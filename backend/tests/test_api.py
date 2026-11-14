"""Cross-study evidence APIs, source traceability, input validation and error handling (FastAPI)."""
import pytest


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["data"]["status"] == "ok"


def test_every_finding_is_traceable(client):
    fids = [f["id"] for f in client.get("/api/v1/findings").json()["data"]]
    assert len(fids) == 31
    for fid in fids:
        d = client.get(f"/api/v1/findings/{fid}").json()["data"]
        assert d["evidence_type"] in ("verified_measurement", "author_conclusion", "hypothesis")
        assert d["independence_from_bass2"] and d["study"]["id"] == d["study_id"]
        for ref in d["source_refs"]:
            assert ref["locator"] and ref["source"]["url"].startswith("https://")


def test_comparison_rows_carry_independence(client):
    d = client.get("/api/v1/comparisons/CMP-05").json()["data"]
    assert d["numeric_merge_allowed"] is False
    assert {r["study_id"] for r in d["rows"]} >= {"BASS-II", "SAFFIRE-IV-V"}
    assert all("independence_from_bass2" in r for r in d["rows"])


def test_replication_flag(client):
    same = client.get("/api/v1/findings/F-L18-01").json()["data"]
    sep = client.get("/api/v1/findings/F-GEL-01").json()["data"]
    assert same["independence_from_bass2"] == "same_experiment" and same["counts_as_replication_of_bass2"] is False
    assert sep["counts_as_replication_of_bass2"] is True


def test_findings_filters(client):
    hyp = client.get("/api/v1/findings", params={"evidence_type": "hypothesis"}).json()
    assert hyp["meta"]["count"] == 4 and all(f["evidence_type"] == "hypothesis" for f in hyp["data"])
    ver = client.get("/api/v1/findings", params={"evidence_type": "verified_measurement"}).json()["data"]
    assert ver and all(f["study_id"] == "BASS-II" for f in ver)
    m8 = client.get("/api/v1/findings", params={"test_id": "M8"}).json()["data"]
    assert {f["id"] for f in m8} == {"F-B2-01", "F-B2-02"}


def test_bass2_data_endpoints(client):
    steps = client.get("/api/v1/bass2/pmma/steps", params={"tracked": "true"}).json()
    assert steps["meta"]["count"] == 39 and steps["meta"]["measurement_level"] == "repeated_step_within_test"
    tests = client.get("/api/v1/bass2/pmma/tests").json()
    assert tests["meta"]["count"] == 18 and tests["meta"]["units"]["spread_rate"] == "mm/s"
    one = client.get("/api/v1/bass2/pmma/tests", params={"thickness_mm": "1", "width_cm": "2.2", "sides_burning": "2"}).json()["data"]
    assert [t["test_id"] for t in one] == ["M16"]
    q = client.get("/api/v1/bass2/fabric/outcomes", params={"outcome_class": "quenched (low flow)"}).json()["data"]
    assert len(q) == 6 and all(r["final_flow_is_upper_bound"] for r in q)
    t = client.get("/api/v1/bass2/tests/M8").json()["data"]
    assert t["flow_configuration"] == "Opposed" and len(t["pmma_spread_steps"]) == 3 and t["fabric_outcome"] is None
    assert client.get("/api/v1/bass2/tests", params={"flow_configuration": "unresolved"}).json()["meta"]["count"] == 5


@pytest.mark.parametrize("url,status,code", [
    ("/api/v1/findings?colour=red", 400, "unknown_parameter"),
    ("/api/v1/findings?evidence_type=guess", 400, "invalid_parameter"),
    ("/api/v1/findings?topic=a&topic=b", 400, "duplicate_parameter"),
    ("/api/v1/search", 400, "missing_parameter"),
    ("/api/v1/search?q=", 400, "invalid_parameter"),
    ("/api/v1/search?q=the%20and", 400, "invalid_parameter"),
    ("/api/v1/search?q=oxygen&limit=0", 400, "invalid_parameter"),
    ("/api/v1/search?q=oxygen&limit=x", 400, "invalid_parameter"),
    ("/api/v1/search?q=" + "a" * 201, 400, "invalid_parameter"),
    ("/api/v1/bass2/pmma/steps?thickness_mm=thick", 400, "invalid_parameter"),
    ("/api/v1/bass2/pmma/steps?tracked=yes", 400, "invalid_parameter"),
    ("/api/v1/findings/F-B2-01?x=1", 400, "unknown_parameter"),
    ("/api/v1/findings/NOPE", 404, "not_found"),
    ("/api/v1/bass2/tests/Z9", 404, "not_found"),
    ("/api/v1/unknown", 404, "not_found"),
])
def test_errors(client, url, status, code):
    r = client.get(url)
    assert r.status_code == status
    assert r.json()["error"]["code"] == code


def test_method_not_allowed(client):
    r = client.post("/api/v1/findings")
    assert r.status_code == 405 and r.json()["error"]["code"] == "method_not_allowed"


def test_openapi_lists_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/search" in paths and "/api/v1/bass2/pmma/tests" in paths
