"""Writes golden responses from the Python service; worker/test/parity.test.mjs replays them
against the Cloudflare Worker service and requires identical status and body."""
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

GOLDEN = Path(__file__).parent / "golden" / "parity_cases.json"

CASES = [
    "/", "/api/v1", "/api/v1/", "/api/v1/health", "/api/v1/meta", "/api/v1/consistency", "/api/v1/consistency?status=fail",
    "/api/v1/studies", "/api/v1/studies?independence=separate_investigation", "/api/v1/studies/BASS-II", "/api/v1/studies/SOFIE-GEL",
    "/api/v1/sources", "/api/v1/sources?access=abstract_only", "/api/v1/sources/SRC-EIGENBROD-2021",
    "/api/v1/findings", "/api/v1/findings?topic=ventilation_change", "/api/v1/findings?evidence_type=hypothesis",
    "/api/v1/findings?study=SAFFIRE-IV-V&topic=geometry", "/api/v1/findings?independence=same_experiment&lineage=BASS",
    "/api/v1/findings?test_id=T18", "/api/v1/findings/F-B2-01", "/api/v1/findings/F-S5-05", "/api/v1/findings/F-GEL-01",
    "/api/v1/comparisons", "/api/v1/comparisons?topic=oxygen", "/api/v1/comparisons/CMP-01", "/api/v1/comparisons/CMP-05",
    "/api/v1/gaps", "/api/v1/gaps?status=open&priority=high", "/api/v1/gaps?study=SAFFIRE-IV-V",
    "/api/v1/search?q=oxygen+quenching+fabric", "/api/v1/search?q=How%20does%20airflow%20affect%20flame%20spread%3F&limit=20",
    "/api/v1/search?q=ribbed+acrylic+backdraft&type=finding", "/api/v1/search?q=flame+spread&evidence_type=hypothesis",
    "/api/v1/search?q=flame&study=BASS-II&type=finding&limit=50", "/api/v1/search?q=smoke+detector", "/api/v1/search?q=13.5+oxygen",
    "/api/v1/search?q=Plexiglas+flames+extinguished", "/api/v1/search?q=comparison+ventilation&type=comparison",
    "/api/v1/rank/investigations?q=ventilation+shutdown+extinction", "/api/v1/rank/investigations?q=droplet+inert+gas&limit=3",
    "/api/v1/rank/investigations?q=thick+pmma+thickness+spread+rate", "/api/v1/rank/investigations?q=quenching+blowoff+mechanism",
    "/api/v1/bass2/summary", "/api/v1/bass2/tests", "/api/v1/bass2/tests?flow_configuration=unresolved",
    "/api/v1/bass2/tests?fuel_family=SIBAL%20fabric&flag=o2_final_implausible", "/api/v1/bass2/tests?pi=Olson&flow_configuration=Stagnation",
    "/api/v1/bass2/tests/M8", "/api/v1/bass2/tests/T18", "/api/v1/bass2/tests/O20",
    "/api/v1/bass2/pmma/steps", "/api/v1/bass2/pmma/steps?test_id=M3", "/api/v1/bass2/pmma/steps?tracked=false",
    "/api/v1/bass2/pmma/steps?thickness_mm=4&width_cm=2.2", "/api/v1/bass2/pmma/tests", "/api/v1/bass2/pmma/tests?sides_burning=1",
    "/api/v1/bass2/fabric/outcomes", "/api/v1/bass2/fabric/outcomes?sample_reused=false&width_cm=2.2",
    "/api/v1/bass2/fabric/outcomes?outcome_class=no%20ignition",
    # errors
    "/api/v1/findings?colour=red", "/api/v1/findings?evidence_type=guess", "/api/v1/findings?topic=oxygen&topic=geometry",
    "/api/v1/search", "/api/v1/search?q=", "/api/v1/search?q=the+of", "/api/v1/search?q=oxygen&limit=51",
    "/api/v1/search?q=oxygen&limit=-1", "/api/v1/search?q=oxygen&type=video", "/api/v1/bass2/pmma/steps?thickness_mm=1e3",
    "/api/v1/bass2/pmma/steps?sides_burning=3", "/api/v1/bass2/fabric/outcomes?sample_reused=1", "/api/v1/findings/F-B2-01?verbose=true",
    "/api/v1/findings/NOPE", "/api/v1/studies/apollo", "/api/v1/bass2/tests/X1", "/api/v1/nothing/here", "/elsewhere",
]


def test_write_golden(service):
    out = []
    for url in CASES:
        parts = urlsplit(url)
        status, body = service.handle("GET", parts.path, parse_qsl(parts.query, keep_blank_values=True))
        out.append({"url": url, "method": "GET", "status": status, "body": body})
    out.append({"url": "/api/v1/findings", "method": "DELETE", "status": 405,
                "body": service.handle("DELETE", "/api/v1/findings", [])[1]})
    GOLDEN.write_text(json.dumps(out, indent=1, allow_nan=False))
    assert len(out) == len(CASES) + 1
    assert sum(1 for c in out if c["status"] == 200) >= 55


def test_fastapi_matches_service(client, service):
    for url in CASES:
        parts = urlsplit(url)
        expect = service.handle("GET", parts.path, parse_qsl(parts.query, keep_blank_values=True))
        r = client.get(url)
        assert r.status_code == expect[0], url
        assert r.json() == json.loads(json.dumps(expect[1])), url
