# ARCAUS: GitHub → Cloudflare deployment (backend & infrastructure)

Prepared by Claude (backend/infrastructure only). `site/` is the frozen frontend supplied by the user and is not modified.

## Repository layout
| Path | What it is | Cloudflare Worker |
|---|---|---|
| `/wrangler.toml` + `site/` | Static frontend (frozen) | **`arcaus`**: static assets from `./site` |
| `backend/worker/` | Evidence API + Ask ARCAUS (`/api/v1/*`) | **`arcaus-api`**: separate Worker; never overwrites `arcaus` |
| `backend/ember/`, `backend/data/`, `backend/tests/` | Python build, 51 scientific checks, tests | not deployed |

Both read the same verified evidence (content SHA `7829520c83d7…`). The API Worker bundles `backend/data/build/evidence_bundle.json` at deploy time; there is no database.

## Controlled deploys (no automatic production)
Use two Workers Builds connections to the same repo. In both, set **Production branch = `production`**. Pushes to `main` then build preview versions only; production changes only when `main` is merged into `production` after approval.

| Setting | `arcaus` (site) | `arcaus-api` (backend) |
|---|---|---|
| Git repository | `Thurtzz/arcaus` | `Thurtzz/arcaus` |
| Root directory | `/` | `backend/worker` |
| Build command | *(empty)* | `npm ci` |
| Deploy command | `npx wrangler deploy` | `npx wrangler deploy` |
| Non-production branch deploy command | `npx wrangler versions upload` | `npx wrangler versions upload` |
| Production branch | `production` | `production` |
| Builds for non-production branches | Enabled | Enabled |

## Gemini key (backend Worker only)
Dashboard → Workers & Pages → **arcaus-api** → Settings → Variables and Secrets → Add → Type **Secret** → Name `GEMINI_API_KEY`. Never put it in `site/config.js`, GitHub, screenshots or chat.

## Connect the site to the API
After `arcaus-api` is live, set its public URL in `site/config.js`:
`window.ARCAUS_API_BASE = 'https://arcaus-api.<subdomain>.workers.dev/api/v1';`
This is a public URL, not a secret. Until it is set, the site runs on the verified static bundle.

## Rate limiting (recommended for public Ask ARCAUS)
Security → WAF → Rate limiting rules: if the URI path contains `/api/v1/ask`, limit to 10 requests per minute per IP and block for 10 minutes.

## Verification after deploy
```
curl -s https://arcaus-api.<sub>.workers.dev/api/v1/health                       # status ok, 51 passed / 0 failed
curl -sI -H "Origin: https://arcaus.<sub>.workers.dev" https://arcaus-api.<sub>.workers.dev/api/v1/meta   # Access-Control-Allow-Origin
curl -s -G https://arcaus-api.<sub>.workers.dev/api/v1/ask --data-urlencode "q=How did BASS-II and Saffire-V flames respond when ventilation was reduced or stopped?"
```
A real Gemini answer has `"generated_by":"gemini+citation_check"`, `"grounding":"verified_citations"` and citations that include CMP-05.

## Rollback
Dashboard → the Worker → **Deployments** → choose the previous version → **Rollback**, or run `npx wrangler rollback` in that Worker's directory.
