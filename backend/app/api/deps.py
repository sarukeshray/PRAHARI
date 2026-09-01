"""Authentication and the seven-role access model.

Every scoped endpoint resolves a caller through ``current_user`` and then asks
``Scope`` what that caller may see. The filters are derived from the ``users``
row on the server — never from anything the client sends — so a caller cannot
widen their own view by editing a request.

Two sign-in paths:

* **Firebase.** A Bearer ID token is verified with the Admin SDK, and the
  verified email is matched to a ``users`` row that carries the role and scope.
* **Demo.** When Firebase is not configured, an ``X-Demo-User`` header naming a
  user id is accepted. This is a convenience for local work and is not
  authentication: it trusts the client completely. It refuses to run when
  ``ENV=production``, so it cannot reach a deployment by accident.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db import get_db
from app.models import Agency, User, Work
from app.models.enums import Role

logger = logging.getLogger(__name__)

_firebase_app = None


def _init_firebase():
    """Load the Admin SDK once, on first use."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    import firebase_admin
    from firebase_admin import credentials

    cred = credentials.Certificate(str(settings.credentials_file))
    _firebase_app = firebase_admin.initialize_app(
        cred, {"storageBucket": settings.firebase_storage_bucket} if settings.firebase_storage_bucket else None
    )
    return _firebase_app


def auth_mode() -> str:
    return "firebase" if settings.firebase_ready else "demo"


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str
    display_name: str
    role: Role
    scope_state: str | None = None
    scope_district_id: str | None = None
    scope_mp_id: str | None = None
    scope_agency_id: str | None = None
    scope_user_agency_id: str | None = None

    @classmethod
    def from_row(cls, row: User) -> CurrentUser:
        return cls(
            user_id=row.user_id,
            email=row.email,
            display_name=row.display_name,
            role=row.role,
            scope_state=row.scope_state,
            scope_district_id=row.scope_district_id,
            scope_mp_id=row.scope_mp_id,
            scope_agency_id=row.scope_agency_id,
            scope_user_agency_id=row.scope_user_agency_id,
        )


def current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
) -> CurrentUser:
    if settings.firebase_ready:
        return _user_from_firebase(db, authorization)
    return _user_from_demo_header(db, x_demo_user)


def _user_from_firebase(db: Session, authorization: str | None) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")

    from firebase_admin import auth as fb_auth

    _init_firebase()
    token = authorization.split(" ", 1)[1]
    try:
        claims = fb_auth.verify_id_token(token)
    except Exception as exc:  # noqa: BLE001 - any verification failure is a 401
        logger.info("token rejected: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in has expired.") from exc

    email = (claims.get("email") or "").lower()
    row = db.scalar(select(User).where(User.email == email))
    if row is None:
        # Authenticated by Firebase, but no role on record. Deliberately not a
        # 403: from the caller's side there is simply no account here.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No PRAHARI account for this sign-in.")

    if row.firebase_uid is None:
        row.firebase_uid = claims.get("uid")
        db.commit()

    return CurrentUser.from_row(row)


def _user_from_demo_header(db: Session, x_demo_user: str | None) -> CurrentUser:
    if settings.is_production:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Firebase is not configured and the demo sign-in is disabled in production.",
        )
    if not x_demo_user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Firebase is not configured. Send an X-Demo-User header naming a demo account.",
        )
    row = db.get(User, x_demo_user)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"No demo account {x_demo_user!r}.")
    return CurrentUser.from_row(row)


# ---------------------------------------------------------------------------
# Scoping
# ---------------------------------------------------------------------------


class Scope:
    """Turns a caller's role into the filter its queries must carry.

    One place, so a new endpoint cannot forget. The rule for each role:

    ============================  ==========================================
    District Authority            works in their district
    State Nodal Authority         works in their state
    Ministry                      everything
    Member of Parliament          works they recommended
    Implementing Agency           works assigned to them
    User Agency                   works handed over to them
    Public                        aggregates only, never a work row
    ============================  ==========================================
    """

    def __init__(self, user: CurrentUser) -> None:
        self.user = user

    @property
    def is_public(self) -> bool:
        return self.user.role is Role.PUBLIC

    def works(self, stmt: Select) -> Select:
        """Narrow a works query to what this caller may see."""
        role = self.user.role

        if role is Role.MINISTRY:
            return stmt

        if role is Role.PUBLIC:
            # Never reachable in practice - the public endpoints do not query
            # works at all - but a filter that matches nothing is the right
            # answer if one ever does.
            return stmt.where(Work.work_id.is_(None))

        if role is Role.DISTRICT_AUTHORITY:
            return stmt.where(Work.district_id == self.user.scope_district_id)

        if role is Role.STATE_NODAL:
            from app.models import District

            return stmt.where(
                Work.district_id.in_(
                    select(District.district_id).where(District.state == self.user.scope_state)
                )
            )

        if role is Role.MP:
            return stmt.where(Work.mp_id == self.user.scope_mp_id)

        if role is Role.IMPLEMENTING_AGENCY:
            return stmt.where(Work.agency_id == self.user.scope_agency_id)

        if role is Role.USER_AGENCY:
            from app.models import AssetHandover

            return stmt.where(
                Work.work_id.in_(
                    select(AssetHandover.work_id).where(
                        AssetHandover.user_agency_id == self.user.scope_user_agency_id
                    )
                )
            )

        # An unrecognised role sees nothing. Failing closed is the only safe
        # default when the question is "what may this person read?".
        return stmt.where(Work.work_id.is_(None))

    def may_see_work(self, db: Session, work_id: str) -> bool:
        stmt = self.works(select(Work.work_id).where(Work.work_id == work_id))
        return db.scalar(stmt) is not None

    def require_work(self, db: Session, work_id: str) -> Work:
        """Fetch a work or refuse.

        A work outside the caller's scope returns 404, not 403. A 403 would
        confirm the record exists, which is itself information the caller is not
        entitled to.
        """
        work = db.get(Work, work_id)
        if work is None or not self.may_see_work(db, work_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such work.")
        return work


def scope(user: CurrentUser = Depends(current_user)) -> Scope:
    return Scope(user)


def require_roles(*roles: Role):
    """Restrict an endpoint to particular roles."""

    def dependency(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action is available to {', '.join(r.value for r in roles)}.",
            )
        return user

    return dependency
