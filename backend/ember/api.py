"""FastAPI app for local development, testing and OpenAPI docs.

    uvicorn ember.api:app --reload --port 8787

All logic lives in ember/service.py; each route passes the raw query string to
the service so validation is identical to the Cloudflare Worker.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .service import get_service

app = FastAPI(
    title="EMBER / ORBIT evidence service",
    version="1.0.0",
    description="Evidence-grounded API over verified NASA BASS-II data and curated microgravity fire-safety findings. "
                "Every finding carries an evidence type, study independence and source locator. Deterministic retrieval; no generative AI.",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "HEAD", "OPTIONS"], allow_headers=["*"])


def _respond(request: Request) -> JSONResponse:
    status, body = get_service().handle(request.method, request.url.path, list(request.query_params.multi_items()))
    return JSONResponse(body, status_code=status, headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/v1", tags=["service"])
def root(request: Request):
    return _respond(request)


@app.get("/api/v1/health", tags=["service"])
def health(request: Request):
    return _respond(request)


@app.get("/api/v1/meta", tags=["service"])
def meta(request: Request):
    return _respond(request)


@app.get("/api/v1/consistency", tags=["service"])
def consistency(request: Request, status: Optional[str] = Query(None, description="pass or fail")):
    return _respond(request)


@app.get("/api/v1/studies", tags=["evidence"])
def studies(request: Request, lineage: Optional[str] = None, independence: Optional[str] = None):
    return _respond(request)


@app.get("/api/v1/studies/{study_id}", tags=["evidence"])
def study(request: Request, study_id: str):
    return _respond(request)


@app.get("/api/v1/sources", tags=["evidence"])
def sources(request: Request, access: Optional[str] = None):
    return _respond(request)


@app.get("/api/v1/sources/{source_id}", tags=["evidence"])
def source(request: Request, source_id: str):
    return _respond(request)


@app.get("/api/v1/findings", tags=["evidence"])
def findings(request: Request, study: Optional[str] = None, topic: Optional[str] = None, evidence_type: Optional[str] = None,
             independence: Optional[str] = None, lineage: Optional[str] = None, test_id: Optional[str] = None):
    return _respond(request)


@app.get("/api/v1/findings/{finding_id}", tags=["evidence"])
def finding(request: Request, finding_id: str):
    return _respond(request)


@app.get("/api/v1/comparisons", tags=["evidence"])
def comparisons(request: Request, topic: Optional[str] = None):
    return _respond(request)


@app.get("/api/v1/comparisons/{comparison_id}", tags=["evidence"])
def comparison(request: Request, comparison_id: str):
    return _respond(request)


@app.get("/api/v1/gaps", tags=["evidence"])
def gaps(request: Request, status: Optional[str] = None, priority: Optional[str] = None, study: Optional[str] = None):
    return _respond(request)


@app.get("/api/v1/search", tags=["retrieval"])
def search(request: Request, q: str = Query(..., min_length=1, max_length=200), type: Optional[str] = None,
           limit: Optional[int] = None, evidence_type: Optional[str] = None, study: Optional[str] = None):
    return _respond(request)


@app.get("/api/v1/rank/investigations", tags=["retrieval"])
def rank(request: Request, q: str = Query(..., min_length=1, max_length=200), limit: Optional[int] = None):
    return _respond(request)


@app.get("/api/v1/bass2/summary", tags=["bass2"])
def bass2_summary(request: Request):
    return _respond(request)


@app.get("/api/v1/bass2/tests", tags=["bass2"])
def bass2_tests(request: Request, pi: Optional[str] = None, fuel_family: Optional[str] = None,
                flow_configuration: Optional[str] = None, flag: Optional[str] = None):
    return _respond(request)


@app.get("/api/v1/bass2/tests/{test_id}", tags=["bass2"])
def bass2_test(request: Request, test_id: str):
    return _respond(request)


@app.get("/api/v1/bass2/pmma/steps", tags=["bass2"])
def pmma_steps(request: Request, test_id: Optional[str] = None, thickness_mm: Optional[float] = None, width_cm: Optional[float] = None,
               sides_burning: Optional[int] = None, tracked: Optional[bool] = None):
    return _respond(request)


@app.get("/api/v1/bass2/pmma/tests", tags=["bass2"])
def pmma_tests(request: Request, thickness_mm: Optional[float] = None, width_cm: Optional[float] = None, sides_burning: Optional[int] = None):
    return _respond(request)


@app.get("/api/v1/bass2/fabric/outcomes", tags=["bass2"])
def fabric_outcomes(request: Request, outcome_class: Optional[str] = None, sample_reused: Optional[bool] = None,
                    width_cm: Optional[float] = None):
    return _respond(request)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return _respond(request)


@app.exception_handler(405)
async def not_allowed(request: Request, exc):
    return _respond(request)


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, exc):
    # Route all parameter validation through the shared service so errors match the Worker.
    return _respond(request)
