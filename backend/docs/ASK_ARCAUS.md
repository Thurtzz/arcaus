# Ask ARCAUS: Gemini research assistant

`GET /api/v1/ask?q=<question>` (q of at most 300 characters). This is the only endpoint that calls an outside service. It is separate from the deterministic evidence routes, which are unchanged (79/79 golden cases still match).

## How it answers
1. **Retrieval.** BM25 retrieval runs through the existing `/api/v1/search` (up to 2 comparisons plus their findings and the top findings).
2. **Nothing matches.** The endpoint answers "unsupported" and Gemini is **not called**.
3. **Gemini call.** Gemini (default `gemini-3.5-flash`, override with `GEMINI_MODEL`) receives only that evidence pack plus strict rules:
   - cite record ids;
   - keep evidence classes;
   - state the conditions;
   - no merging numbers across experiments;
   - no safe thresholds, risk predictions or Moon/Mars extrapolation;
   - say "unsupported" when the evidence doesn't answer.
4. **Citation check.** The Worker checks every citation. An answer that cites nothing, or cites a record that was not retrieved, is **withheld** (`supported:false`).
5. **Response.** The response returns the answer, citations (statement, evidence class, conditions, limitations, source title, locator and URL), the retrieved ids, the guardrails and the model name.

## Errors
| Status | Code | Meaning |
| --- | --- | --- |
| 503 | `assistant_unavailable` | No `GEMINI_API_KEY` secret. The retrieved evidence ids are still returned. |
| 502 | `upstream_error` | Gemini failed. The key is never echoed. |
| 400 | `missing_parameter` / `invalid_parameter` / `unknown_parameter` / `duplicate_parameter` | Same conventions as the rest of the API. |
| 405 | (other method) | Any method other than GET, HEAD or OPTIONS. |

Responses use `Cache-Control: no-store`.

## Setup (the key never goes in frontend code)
```
cd worker
npx wrangler secret put GEMINI_API_KEY     # paste the key from Google AI Studio when prompted
npx wrangler deploy
```

## Proof of a real Gemini response (run after deploy)
```
curl -s -G "https://<your-worker>.workers.dev/api/v1/ask" \
  --data-urlencode "q=How did BASS-II and Saffire-V flames respond when ventilation was reduced or stopped?"
```
A real response has `"meta":{"generated_by":"gemini+citation_check","grounding":"verified_citations"}`, `"model":"gemini-…"`, a `usage` block from Google, and citations that include CMP-05, BASS-II and Saffire IV–V findings.

## Tests
`worker/test/ask.test.mjs` has 9 tests, with a stand-in for Gemini. They cover:
- retrieval for the ventilation question;
- that only the evidence pack is sent;
- that the key travels in a header and never in a response;
- rejection of fabricated and missing citations;
- unsupported questions;
- no-evidence questions (no model call);
- the missing secret (503);
- an upstream failure (502);
- input validation.
