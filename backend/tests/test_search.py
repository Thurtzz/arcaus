"""Research retrieval and relevance ranking."""
from ember import search


def test_tokenizer_normalizes_synonyms_and_stems():
    assert search.tokenize("Acrylic flames quenched in O2") == ["pmma", "flame", "quench", "oxygen"]


def test_ranking_is_deterministic(service):
    a = service.handle("GET", "/api/v1/search", [("q", "oxygen quenching fabric")])
    b = service.handle("GET", "/api/v1/search", [("q", "fabric quenching oxygen")])
    assert a[1]["data"]["results"] == b[1]["data"]["results"]


def test_relevant_findings_rank_first(service):
    cases = {
        "ribbed PMMA surface structure spread": "F-S5-01",
        "fan turned off flames went out ISS": "F-B2-11",
        "smoke particle size detector": "F-SAMER-01",
        "PMMA sphere quenching blowoff transition": "F-GEL-01",
        "Nomex fire barrier ignition": "F-B2-12",
    }
    for q, expected in cases.items():
        _, body = service.handle("GET", "/api/v1/search", [("q", q), ("type", "finding"), ("limit", "3")])
        ids = [r["id"] for r in body["data"]["results"]]
        assert expected in ids, (q, ids)


def test_investigation_ranking(service):
    _, body = service.handle("GET", "/api/v1/rank/investigations", [("q", "droplet combustion extinction inert gas")])
    assert body["data"]["results"][0]["study_id"] == "FLEX"
    _, body = service.handle("GET", "/api/v1/rank/investigations", [("q", "ribbed structured PMMA exploration atmosphere")])
    assert body["data"]["results"][0]["study_id"] == "SAFFIRE-IV-V"


def test_search_filters(service):
    _, body = service.handle("GET", "/api/v1/search", [("q", "flame spread"), ("evidence_type", "hypothesis")])
    assert body["data"]["results"] and all(r["evidence_type"] == "hypothesis" for r in body["data"]["results"])
    _, body = service.handle("GET", "/api/v1/search", [("q", "flame spread"), ("study", "BASS-II"), ("type", "finding")])
    assert all(r["study_id"] == "BASS-II" for r in body["data"]["results"])
