"""Deterministic BM25 retrieval shared by the Python and Cloudflare Worker services.

The index (token frequencies, document lengths, precomputed IDF) is built here and
shipped in the evidence bundle. Query scoring uses only + - * / on stored values,
in a fixed order, so the JavaScript port in worker/src/search.js returns identical
scores and rankings. Tokenizer rules (stopwords, synonyms, stemming) are also
shipped in the bundle and must stay in step with search.js.
"""
from __future__ import annotations

import math
import re

K1 = 1.2
B = 0.75

STOPWORDS = sorted({
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "did", "do", "does", "for", "from", "how", "in", "into", "is",
    "it", "its", "of", "on", "or", "than", "that", "the", "their", "them", "then", "there", "these", "this", "to", "was",
    "were", "what", "when", "where", "which", "while", "who", "why", "will", "with", "would", "about", "across", "between",
    "under", "over", "more", "most", "less", "per", "not", "no", "any", "all", "each", "has", "have", "had",
})

SYNONYMS = {
    "acrylic": "pmma", "plexiglas": "pmma", "plexiglass": "pmma", "polymethylmethacrylate": "pmma",
    "o2": "oxygen", "ventilation": "airflow", "flow": "airflow", "air": "airflow", "fan": "airflow",
    "extinguish": "extinction", "extinguished": "extinction", "extinguishes": "extinction", "extinguishment": "extinction",
    "quench": "quenching", "quenched": "quenching", "quenches": "quenching", "blowoff": "blowoff", "blow": "blowoff",
    "microgravity": "microgravity", "zero": "microgravity", "fabric": "fabric", "cloth": "fabric", "sibal": "fabric",
    "cotton": "fabric", "spread": "spread", "spreading": "spread", "propagation": "spread", "propagate": "spread",
    "thick": "thickness", "thicker": "thickness", "thin": "thickness", "rib": "ribs", "ribbed": "ribs", "structured": "ribs",
    "fire": "flame", "fires": "flame", "flames": "flame", "burning": "burn", "burned": "burn", "burns": "burn",
    "ignite": "ignition", "ignited": "ignition", "ignites": "ignition",
}


def stem(tok: str) -> str:
    if len(tok) > 5 and tok.endswith("ing"):
        return tok[:-3]
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss") and not tok.endswith("us"):
        return tok[:-1]
    return tok


_SPLIT = re.compile(r"[^a-z0-9.]+")
_STOP = set(STOPWORDS)


def tokenize(text: str) -> list[str]:
    out = []
    for raw in _SPLIT.split(str(text).lower()):
        tok = raw.strip(".")
        if not tok or tok in _STOP:
            continue
        tok = SYNONYMS.get(tok, tok)
        tok = stem(tok)
        if tok and tok not in _STOP:
            out.append(tok)
    return out


def config() -> dict:
    return {"k1": K1, "b": B, "stopwords": STOPWORDS, "synonyms": SYNONYMS,
            "stemming": "strip 'ing' if len>5; 'ies'->'y' if len>4; trailing 's' if len>3 and not 'ss'/'us'",
            "split_pattern": "[^a-z0-9.]+", "strip_chars": "."}


def _doc_text(kind: str, rec: dict, studies: dict) -> str:
    if kind == "finding":
        st = studies.get(rec["study_id"], {})
        parts = [rec["title"], rec["title"], rec["research_question"], rec["statement"], rec.get("material", ""),
                 rec.get("geometry", ""), " ".join(rec.get("topics", [])).replace("_", " "), st.get("name", ""), rec["study_id"]]
        parts += [str(v) for v in (rec.get("conditions") or {}).values()]
        return " ".join(parts)
    if kind == "study":
        return " ".join([rec["name"], rec["name"], rec["id"], rec["summary"], " ".join(rec["materials"]), " ".join(rec["variables"]), rec["platform"]])
    if kind == "comparison":
        return " ".join([rec["title"], rec["title"], rec["question"], rec["agreement"], rec["differences"], rec["topic"].replace("_", " ")])
    raise ValueError(kind)


def build_index(findings: list[dict], studies: list[dict], comparisons: list[dict]) -> dict:
    smap = {s["id"]: s for s in studies}
    docs = []
    for kind, recs in (("finding", findings), ("study", studies), ("comparison", comparisons)):
        for rec in recs:
            toks = tokenize(_doc_text(kind, rec, smap))
            tf = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            docs.append({
                "id": rec["id"], "type": kind, "title": rec.get("title") or rec.get("name"),
                "study_id": rec.get("study_id") if kind == "finding" else (rec["id"] if kind == "study" else None),
                "evidence_type": rec.get("evidence_type"),
                "length": len(toks), "tf": dict(sorted(tf.items())),
            })
    n = len(docs)
    df = {}
    for d in docs:
        for t in d["tf"]:
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in sorted(df.items())}
    avgdl = sum(d["length"] for d in docs) / n
    return {"config": config(), "n_docs": n, "avgdl": avgdl, "idf": idf, "docs": docs}


def round4(x: float) -> float:
    return math.floor(x * 10000 + 0.5) / 10000


def score_doc(doc: dict, terms: list[str], index: dict) -> tuple[float, list[str]]:
    k1, b, avgdl = index["config"]["k1"], index["config"]["b"], index["avgdl"]
    s = 0.0
    matched = []
    for t in terms:
        tf = doc["tf"].get(t)
        if not tf:
            continue
        matched.append(t)
        s = s + index["idf"][t] * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc["length"] / avgdl))
    return s, matched


def query_terms(q: str) -> list[str]:
    return sorted(set(tokenize(q)))
