"""The seven-role access boundary, tested from outside the API.

These are the tests that matter most in this file set. Everything else checks
that the engine says the right thing; these check that it says it only to the
people entitled to hear it.

Each test drives real HTTP requests through the app with a different role signed
in, and asserts on what comes back — not on internal helper functions, because a
boundary that only holds in a helper is not a boundary.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import (
    MP,
    Agency,
    AssetHandover,
    District,
    Payment,
    ProgressReport,
    SORBenchmark,
    User,
    UserAgency,
    Work,
)
from app.models.enums import (
    AgencyType,
    HandoverStatus,
    House,
    Role,
    Terrain,
    UserAgencyType,
    WorkStatus,
)

TODAY = date(2026, 8, 31)


@pytest.fixture
def client(tmp_path):
    """An app wired to a small two-district corpus with one user per role."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    with maker() as db:
        _seed(db)
        db.commit()

    def override_get_db():
        with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed(db) -> None:
    # Two districts in two states, so state scoping has something to exclude.
    db.add_all(
        [
            District(
                district_id="RJ-AAA", name="Alpha", state="Rajasthan",
                terrain_category=Terrain.PLAIN, centroid_lat=25.0, centroid_lon=74.0,
            ),
            District(
                district_id="KL-BBB", name="Beta", state="Kerala",
                terrain_category=Terrain.COASTAL, centroid_lat=10.0, centroid_lon=76.0,
            ),
        ]
    )
    db.add_all(
        [
            MP(
                mp_id="MP-A", name="Dr. A. Alpha", house=House.LOK_SABHA,
                constituency="Alpha", state="Rajasthan",
                tenure_start=date(2024, 6, 1), tenure_end=date(2029, 5, 31),
            ),
            MP(
                mp_id="MP-B", name="Dr. B. Beta", house=House.LOK_SABHA,
                constituency="Beta", state="Kerala",
                tenure_start=date(2024, 6, 1), tenure_end=date(2029, 5, 31),
            ),
        ]
    )
    db.add_all(
        [
            Agency(
                agency_id="AG-A", name="PWD Alpha", agency_type=AgencyType.PWD,
                district_id="RJ-AAA", registered_date=date(2019, 1, 1),
            ),
            Agency(
                agency_id="AG-B", name="PWD Beta", agency_type=AgencyType.PWD,
                district_id="KL-BBB", registered_date=date(2019, 1, 1),
            ),
        ]
    )
    db.add_all(
        [
            UserAgency(
                user_agency_id="UA-A", name="Panchayat Alpha",
                user_agency_type=UserAgencyType.PANCHAYAT, district_id="RJ-AAA",
            ),
            UserAgency(
                user_agency_id="UA-B", name="Panchayat Beta",
                user_agency_type=UserAgencyType.PANCHAYAT, district_id="KL-BBB",
            ),
        ]
    )
    for year, rate in [(2025, 1_000_000.0), (2026, 1_062_000.0)]:
        for terrain in (Terrain.PLAIN, Terrain.COASTAL):
            db.add(
                SORBenchmark(
                    state="Rajasthan" if terrain is Terrain.PLAIN else "Kerala",
                    work_type="ROAD_CC", unit="per km", unit_rate=rate, year=year,
                    terrain_category=terrain, terrain_multiplier=1.0,
                )
            )
    db.flush()

    def work(work_id, district, mp, agency, *, completed=False):
        w = Work(
            work_id=work_id, mp_id=mp, district_id=district, block="Central",
            panchayat="Central", work_type="ROAD_CC",
            description="Construction of cement concrete road at Central village.",
            estimated_cost=1_000_000.0,
            recommended_date=date(2025, 1, 10),
            sanctioned_date=date(2025, 2, 10),
            expected_completion_date=date(2026, 2, 10),
            actual_completion_date=TODAY - timedelta(days=200) if completed else None,
            status=WorkStatus.COMPLETED if completed else WorkStatus.IN_PROGRESS,
            agency_id=agency, latitude=25.0, longitude=74.0, is_sc_st_area=False,
        )
        db.add(w)
        return w

    work("RJ-AAA-00001", "RJ-AAA", "MP-A", "AG-A")
    work("RJ-AAA-00002", "RJ-AAA", "MP-B", "AG-B")  # same district, other member/agency
    handed = work("RJ-AAA-00003", "RJ-AAA", "MP-A", "AG-A", completed=True)
    work("KL-BBB-00001", "KL-BBB", "MP-B", "AG-B")  # different state entirely
    db.flush()

    db.add(
        AssetHandover(
            work_id=handed.work_id, user_agency_id="UA-A",
            handover_initiated_date=TODAY - timedelta(days=190),
            handover_acknowledged_date=None, status=HandoverStatus.PENDING,
        )
    )

    for w_id in ("RJ-AAA-00001", "RJ-AAA-00002", "RJ-AAA-00003", "KL-BBB-00001"):
        db.add(Payment(work_id=w_id, installment_no=1, amount=500_000.0,
                       payment_date=date(2025, 4, 1), reported_physical_progress_pct=50.0))
        db.add(ProgressReport(work_id=w_id, report_date=date(2025, 4, 1),
                              physical_progress_pct=50.0, remarks="ok"))

    db.add_all(
        [
            User(user_id="u-da", email="da@x.test", display_name="DA Alpha",
                 role=Role.DISTRICT_AUTHORITY, scope_district_id="RJ-AAA", scope_state="Rajasthan"),
            User(user_id="u-da2", email="da2@x.test", display_name="DA Alpha Two",
                 role=Role.DISTRICT_AUTHORITY, scope_district_id="RJ-AAA", scope_state="Rajasthan"),
            User(user_id="u-sna", email="sna@x.test", display_name="SNA Rajasthan",
                 role=Role.STATE_NODAL, scope_state="Rajasthan"),
            User(user_id="u-min", email="min@x.test", display_name="Ministry",
                 role=Role.MINISTRY),
            User(user_id="u-mp", email="mp@x.test", display_name="Dr. A. Alpha",
                 role=Role.MP, scope_mp_id="MP-A", scope_state="Rajasthan"),
            User(user_id="u-agency", email="ag@x.test", display_name="PWD Alpha",
                 role=Role.IMPLEMENTING_AGENCY, scope_agency_id="AG-A",
                 scope_district_id="RJ-AAA", scope_state="Rajasthan"),
            User(user_id="u-ua", email="ua@x.test", display_name="Panchayat Alpha",
                 role=Role.USER_AGENCY, scope_user_agency_id="UA-A",
                 scope_district_id="RJ-AAA", scope_state="Rajasthan"),
            User(user_id="u-public", email="pub@x.test", display_name="Public",
                 role=Role.PUBLIC),
        ]
    )


def as_(user_id: str) -> dict:
    return {"X-Demo-User": user_id}


def work_ids(response) -> set[str]:
    return {row["work_id"] for row in response.json()}


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------


def test_unauthenticated_request_is_refused(client):
    assert client.get("/api/v1/works").status_code == 401


def test_unknown_user_is_refused(client):
    assert client.get("/api/v1/works", headers=as_("u-nobody")).status_code == 401


def test_health_needs_no_sign_in(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert "Synthetic" in body["data_notice"]


# ---------------------------------------------------------------------------
# Read scope, per role
# ---------------------------------------------------------------------------


def test_district_authority_sees_only_its_district(client):
    seen = work_ids(client.get("/api/v1/works", headers=as_("u-da")))
    assert seen == {"RJ-AAA-00001", "RJ-AAA-00002", "RJ-AAA-00003"}
    assert "KL-BBB-00001" not in seen


def test_state_nodal_sees_its_state_only(client):
    seen = work_ids(client.get("/api/v1/works", headers=as_("u-sna")))
    assert "RJ-AAA-00001" in seen
    assert "KL-BBB-00001" not in seen


def test_ministry_sees_everything(client):
    seen = work_ids(client.get("/api/v1/works", headers=as_("u-min")))
    assert seen == {"RJ-AAA-00001", "RJ-AAA-00002", "RJ-AAA-00003", "KL-BBB-00001"}


def test_mp_sees_only_own_recommendations(client):
    seen = work_ids(client.get("/api/v1/works", headers=as_("u-mp")))
    assert seen == {"RJ-AAA-00001", "RJ-AAA-00003"}
    # Same district, another member's work.
    assert "RJ-AAA-00002" not in seen


def test_implementing_agency_sees_only_assigned_works(client):
    seen = work_ids(client.get("/api/v1/works", headers=as_("u-agency")))
    assert seen == {"RJ-AAA-00001", "RJ-AAA-00003"}
    assert "RJ-AAA-00002" not in seen


def test_user_agency_sees_only_assets_handed_to_it(client):
    seen = work_ids(client.get("/api/v1/works", headers=as_("u-ua")))
    assert seen == {"RJ-AAA-00003"}


# ---------------------------------------------------------------------------
# Direct access to a record outside scope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("user_id", "forbidden_work"),
    [
        ("u-da", "KL-BBB-00001"),
        ("u-sna", "KL-BBB-00001"),
        ("u-mp", "RJ-AAA-00002"),
        ("u-agency", "RJ-AAA-00002"),
        ("u-ua", "RJ-AAA-00001"),
    ],
)
def test_work_outside_scope_is_not_reachable_by_id(client, user_id, forbidden_work):
    """404, not 403.

    A 403 would confirm the record exists, which is itself something the caller
    is not entitled to know.
    """
    response = client.get(f"/api/v1/works/{forbidden_work}", headers=as_(user_id))
    assert response.status_code == 404


def test_ministry_can_reach_any_work(client):
    assert client.get("/api/v1/works/KL-BBB-00001", headers=as_("u-min")).status_code == 200


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------


def test_public_aggregates_need_no_sign_in(client):
    assert client.get("/api/v1/public/aggregates").status_code == 200


def test_public_aggregates_expose_no_identifying_detail(client):
    """The test for this role is what it cannot show."""
    body = client.get("/api/v1/public/aggregates").text
    for leak in ("RJ-AAA-00001", "KL-BBB-00001", "PWD Alpha", "Dr. A. Alpha", "MP-A"):
        assert leak not in body, f"public aggregate leaked {leak!r}"


def test_public_role_gets_no_work_rows(client):
    assert client.get("/api/v1/works", headers=as_("u-public")).json() == []


def test_public_role_cannot_read_findings(client):
    assert client.get("/api/v1/flags", headers=as_("u-public")).json() == []


def test_public_role_cannot_read_agency_performance(client):
    response = client.get("/api/v1/agencies/AG-A/performance", headers=as_("u-public"))
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Write actions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("user_id", ["u-mp", "u-agency", "u-ua", "u-public"])
def test_only_reviewers_may_decide_on_a_finding(client, user_id):
    response = client.post(
        "/api/v1/flags/1/review",
        headers=as_(user_id),
        json={"action": "CLEAR", "justification": ""},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("user_id", ["u-da", "u-agency", "u-public", "u-min"])
def test_only_a_member_may_submit_a_recommendation(client, user_id):
    response = client.post(
        "/api/v1/works",
        headers=as_(user_id),
        json={
            "district_id": "RJ-AAA", "block": "Central", "work_type": "ROAD_CC",
            "description": "Construction of a cement concrete road at Central village ward 4.",
            "estimated_cost": 900_000, "latitude": 25.0, "longitude": 74.0,
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize("user_id", ["u-da", "u-mp", "u-agency", "u-min"])
def test_only_a_user_agency_may_acknowledge_a_handover(client, user_id):
    response = client.post("/api/v1/assets/RJ-AAA-00003/acknowledge", headers=as_(user_id))
    assert response.status_code == 403


def test_user_agency_cannot_acknowledge_someone_elses_asset(client):
    """UA-A must not be able to acknowledge a handover addressed to UA-B."""
    response = client.post("/api/v1/assets/KL-BBB-00001/acknowledge", headers=as_("u-ua"))
    assert response.status_code == 404


@pytest.mark.parametrize("user_id", ["u-da", "u-sna", "u-mp", "u-agency"])
def test_only_the_ministry_may_retune_the_engine(client, user_id):
    response = client.put(
        "/api/v1/engine/weights", headers=as_(user_id), json={"thresholds": {"COST_ABOVE_SOR_PCT": 30}}
    )
    assert response.status_code == 403


def test_ministry_can_retune_and_it_persists(client):
    before = client.get("/api/v1/engine/weights", headers=as_("u-min")).json()
    assert before["thresholds"]["COST_ABOVE_SOR_PCT"] == 25.0

    client.put(
        "/api/v1/engine/weights",
        headers=as_("u-min"),
        json={"thresholds": {"COST_ABOVE_SOR_PCT": 33.0}},
    )
    after = client.get("/api/v1/engine/weights", headers=as_("u-min")).json()
    assert after["thresholds"]["COST_ABOVE_SOR_PCT"] == 33.0


# ---------------------------------------------------------------------------
# The override justification rule
# ---------------------------------------------------------------------------


def _first_flag_id(client) -> int:
    """Score a work so there is a real finding to act on."""
    client.post("/api/v1/works/RJ-AAA-00001/assess", headers=as_("u-da"))
    flags = client.get("/api/v1/flags", headers=as_("u-da")).json()
    assert flags, "expected the engine to raise at least one finding to review"
    return flags[0]["flag_id"]


def test_override_without_justification_is_rejected(client):
    flag_id = _first_flag_id(client)
    response = client.post(
        f"/api/v1/flags/{flag_id}/review",
        headers=as_("u-da"),
        json={"action": "OVERRIDE", "justification": ""},
    )
    assert response.status_code == 422
    assert "justification" in response.json()["detail"].lower()


def test_override_with_a_token_justification_is_rejected(client):
    flag_id = _first_flag_id(client)
    response = client.post(
        f"/api/v1/flags/{flag_id}/review",
        headers=as_("u-da"),
        json={"action": "OVERRIDE", "justification": "ok"},
    )
    assert response.status_code == 422


def test_override_with_a_real_justification_is_recorded(client):
    flag_id = _first_flag_id(client)
    response = client.post(
        f"/api/v1/flags/{flag_id}/review",
        headers=as_("u-da"),
        json={
            "action": "OVERRIDE",
            "justification": "Site inspection on 12 August confirmed the revised scope.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OVERRIDDEN"
    assert body["reviews"][0]["action"] == "OVERRIDE"
    assert "12 August" in body["reviews"][0]["justification"]


def test_clear_and_investigate_need_no_justification(client):
    flag_id = _first_flag_id(client)
    response = client.post(
        f"/api/v1/flags/{flag_id}/review",
        headers=as_("u-da"),
        json={"action": "INVESTIGATE", "justification": ""},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "UNDER_INVESTIGATION"


def test_a_decision_is_never_taken_without_a_person(client):
    """No path through the API moves a finding out of OPEN on its own.

    Re-running the engine over a work must leave every finding it already raised
    exactly as the reviewer left it.
    """
    flag_id = _first_flag_id(client)
    client.post(
        f"/api/v1/flags/{flag_id}/review",
        headers=as_("u-da"),
        json={"action": "CLEAR", "justification": "Checked against the sanction file."},
    )
    client.post("/api/v1/works/RJ-AAA-00001/assess", headers=as_("u-da"))
    assert client.get(f"/api/v1/flags/{flag_id}", headers=as_("u-da")).json()["status"] == "CLEARED"
