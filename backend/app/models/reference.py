"""Reference data: members, districts, agencies, rate benchmarks, and users."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import AgencyType, House, Role, Terrain, UserAgencyType


def enum_col(py_enum, **kw):
    """VARCHAR + CHECK rather than a native DB enum, so SQLite and Postgres agree."""
    return Enum(py_enum, native_enum=False, validate_strings=True, length=32, **kw)


class MP(Base):
    __tablename__ = "mps"

    mp_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    house: Mapped[House] = mapped_column(enum_col(House))
    constituency: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(80), index=True)
    tenure_start: Mapped[date] = mapped_column(Date)
    tenure_end: Mapped[date] = mapped_column(Date)
    annual_entitlement: Mapped[int] = mapped_column(Integer, default=50_000_000)

    works: Mapped[list["Work"]] = relationship(back_populates="mp")  # noqa: F821


class District(Base):
    __tablename__ = "districts"

    district_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(80), index=True)
    terrain_category: Mapped[Terrain] = mapped_column(enum_col(Terrain), index=True)
    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)

    agencies: Mapped[list["Agency"]] = relationship(back_populates="district")


class Agency(Base):
    """An implementing agency — the body that executes a work."""

    __tablename__ = "agencies"

    agency_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    agency_type: Mapped[AgencyType] = mapped_column(enum_col(AgencyType))
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.district_id"), index=True)
    registered_date: Mapped[date] = mapped_column(Date)

    district: Mapped[District] = relationship(back_populates="agencies")


class UserAgency(Base):
    """The body an asset is handed over to, which then owns its upkeep.

    Distinct from Agency: an implementing agency builds the asset, a user agency
    receives and operates it. A school, panchayat or health centre is a user
    agency; the PWD division that built its classroom block is not.
    """

    __tablename__ = "user_agencies"

    user_agency_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    user_agency_type: Mapped[UserAgencyType] = mapped_column(enum_col(UserAgencyType))
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.district_id"), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    district: Mapped[District] = relationship()


class SORBenchmark(Base):
    """State Schedule of Rates.

    Rates are stored per year. Cost screening compares a work against the rate
    for the year it was recommended, which is what keeps the comparison
    inflation-neutral without any external deflator — a uniform price rise moves
    the cost and the benchmark together, leaving the ratio unchanged.
    """

    __tablename__ = "sor_benchmarks"
    __table_args__ = (
        UniqueConstraint(
            "state", "work_type", "year", "terrain_category", name="uq_sor_state_type_year_terrain"
        ),
    )

    sor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    work_type: Mapped[str] = mapped_column(String(48), index=True)
    unit: Mapped[str] = mapped_column(String(24))
    unit_rate: Mapped[float] = mapped_column(Float)
    year: Mapped[int] = mapped_column(Integer, index=True)

    # Added beyond the original spec's column list. The spec keyed rates on
    # (state, work_type, year) with a single `terrain_multiplier`, which cannot
    # express five different terrain factors for one row. Keying on terrain too
    # makes the lookup unambiguous and leaves `terrain_multiplier` meaning
    # exactly one thing: the factor already applied to reach this row's rate.
    terrain_category: Mapped[Terrain] = mapped_column(enum_col(Terrain), index=True)
    terrain_multiplier: Mapped[float] = mapped_column(Float, default=1.0)


class CostIndex(Base):
    """Optional construction cost index, for the real-terms view on Trends only.

    The engine does not use this. Flagging relies on the same-year SoR ratio
    above; this table exists so cost movement can be shown in constant rupees if
    an index series is loaded, and the screen degrades gracefully when it is not.
    """

    __tablename__ = "cost_index"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(80), default="CPWD")


class User(Base):
    """An authenticated user and the slice of data their role may see.

    Exactly one scope column is populated for the scoped roles; MINISTRY and
    PUBLIC carry none. The API derives every query filter from these columns
    rather than trusting anything the client sends.
    """

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(enum_col(Role), index=True)

    scope_state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scope_district_id: Mapped[str | None] = mapped_column(
        ForeignKey("districts.district_id"), nullable=True
    )
    scope_mp_id: Mapped[str | None] = mapped_column(ForeignKey("mps.mp_id"), nullable=True)
    scope_agency_id: Mapped[str | None] = mapped_column(
        ForeignKey("agencies.agency_id"), nullable=True
    )
    scope_user_agency_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_agencies.user_agency_id"), nullable=True
    )
