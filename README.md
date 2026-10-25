# Gridline

Gridline is a historical forecast review workspace for January 2026 UK day-ahead electricity decisions. It selects Elexon WINDFOR vintages available at a documented GB auction cutoff, aligns them with FUELHH WIND actuals for the following delivery day, and reports forecast error and source coverage.

This is a historical analysis, not a live forecast, price view, demand forecast, or procurement recommendation. It uses only Elexon WINDFOR and FUELHH (fuelType=WIND).

## Run locally

### Docker

~~~sh
docker compose up --build
~~~

Open http://localhost:8000. The API health check is at http://localhost:8000/api/health, with interactive API documentation at http://localhost:8000/api/docs.

### Development mode

Requires Python 3.12+ and Node 20+.

~~~sh
python -m venv .venv
# Activate the virtual environment, then:
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8000
~~~

In a second terminal:

~~~sh
cd frontend
npm ci
npm run dev
~~~

Open http://localhost:5173. Vite proxies /api requests to the FastAPI development server.

## Analysis method

- The analysis covers decision dates January 1–31, 2026. Each decision date D maps to the following local delivery date D+1 (January 2–February 1).
- The UI offers EPEX SPOT GB day-ahead scenarios: its published 60-minute auction time is 09:20 GMT and its 30-minute auction time is 15:30 GMT. The replay uses these as prototype decision cutoffs; they are not verified deadlines for every buyer. Both are next-day delivery scenarios. Nord Pool N2EX is a separate UK hourly day-ahead auction with a documented 09:50 GMT gate closure; it is documented in the UI but not modeled as a scenario. In January, Europe/London is GMT.
- For every hourly delivery interval, select the latest WINDFOR.publishTime at or before the selected decision cutoff. A record exactly at cutoff is eligible; later publications are excluded. There is no post-cutoff filling.
- The “later forecast records excluded” count is scenario-specific: it counts distinct WINDFOR `(startTime, publishTime)` versions, after identical duplicate rows are collapsed, for the 744 expected hourly D+1 delivery starts when publication is after that interval’s decision-date cutoff. It is limited to the archived WINDFOR publication-time query windows listed in `data/raw/manifest.json`, not all Elexon history.
- Elexon documents WINDFOR as an hourly wind forecast in MW; the included WINDFOR records also have hourly start times. FUELHH generation values are half-hour average MW. For hourly comparisons, the two equal-duration FUELHH actuals are averaged; both must be present. No interpolation is used.
- Both scenarios therefore report hourly source-series comparisons: 31 × 24 = 744 expected hourly pairs. The 30-minute EPEX product scenario does not measure 30-minute forecast accuracy because WINDFOR provides no half-hour forecast series. Its cutoff changes forecast selection, while the comparison resolution remains explicitly hourly.
- MAE, RMSE, forecast-minus-actual mean bias, WAPE, error signs, and the signed-error range are calculated from unrounded matched hourly pairs. Missing forecasts and actuals are counted against 744 expected comparisons. Daily and monthly metrics use the same aligned observations.
- The downloaded snapshot includes the complete 31-day decision window and following-day delivery actuals. The dashboard shows the exchange gate, selected vintages, comparison resolution, coverage, signed-error counts, source retrieval time, and a scenario-labeled CSV export.

The [EPEX SPOT trading brochure](https://www.epexspot.com/sites/default/files/2025-02/EPEX%20SPOT%20Trading%20Brochure%202025%20February.pdf) documents the two local GB auction times. Nord Pool documents the separate [N2EX day-ahead gate closure and hourly products](https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-n2ex-day-ahead-auction). Elexon documents the [hourly wind forecast](https://bmrs.elexon.co.uk/wind-generation) and [half-hourly generation by fuel type](https://www.elexon.co.uk/bsc/glossary/half-hourly-generation-by-fuel-type/).

Elexon describes WINDFOR as forecasts for wind farms visible to ESO with operational metering, and FUELHH as generation by fuel type. The exact asset populations are not demonstrated to be identical here. The metrics describe error between the specified source series; they are not definitive total-national forecast error and should not be used alone to decide procurement volumes. The positive bias remains in the source records: the 15:30 EPEX scenario has 653 positive, 91 negative, and zero zero hourly errors (range -2,720 to +7,073 MW; MAE equals bias on 18 decision dates). The 09:20 scenario has 632 positive, 112 negative, and zero zero errors (range -3,550 to +6,870 MW; MAE equals bias on 19 decision dates). These patterns are preserved rather than adjusted.

## Repository map

| Path | Purpose |
| --- | --- |
| app.py | FastAPI app, analysis API routes, and production static frontend mount |
| backend/analysis.py | Source validation, cutoff selection, hourly alignment, coverage, and metrics |
| data/raw/fuelhh/ | Retrieved Elexon FUELHH source chunks, filtered to WIND during analysis |
| data/raw/windfor/ | Retrieved Elexon WINDFOR source chunks, including January 31 decision publications |
| data/raw/manifest.json | Snapshot query windows, record counts, and retrieval metadata |
| frontend/src/App.jsx | React dashboard, charts, accessible data table, CSV export, theme, and navigation |
| frontend/src/csv.js | Shared CSV column mapping and safe escaping for hourly replay exports |
| frontend/src/styles.css | Responsive light/dark product styles and design tokens |
| frontend/vite.config.js | Frontend dev server and /api proxy configuration |
| frontend/test/csv.test.js | CSV mapping, missing-value, and escaping regression checks |
| tests/test_analysis.py | Replay coverage, metric, cutoff, and API checks |
| requirements.txt, requirements-dev.txt | Runtime and test dependencies |
| Dockerfile, docker-compose.yml | Multi-stage Docker build and local app service |
| build.py | Optional single-service helper that builds the frontend before packaging FastAPI |
| pyproject.toml | Python package metadata and runtime dependencies |
| vercel.json | Vercel FastAPI/Vite service roots and public routing |

Install test dependencies with python -m pip install -r requirements-dev.txt, then run the analysis and API checks with python -m pytest -q. Run the frontend export checks from frontend with npm test.

## Vercel Services

`vercel.json` defines two independently built services for one Vercel project:

- `app` uses the repository root and the FastAPI framework. Vercel detects the standard `app.py` entrypoint.
- `frontend` uses `frontend/` and the Vite framework, which builds the static frontend from that service root.

The ordered top-level rewrites route `/api/*` to `app` first and all other paths to `frontend`. Vercel preserves the incoming path, which matches FastAPI's existing `/api/...` routes and the browser's same-origin `/api/analysis` request. Both services receive public traffic on those paths. There are no server-side service-to-service calls, so no service bindings are configured. The Vite proxy in `frontend/vite.config.js` is only for the separate local Vite development server.

The previous `pyproject.toml` build hook that bundled the Vite frontend into the FastAPI service has been removed so Vercel builds the services independently. `build.py` remains available as a single-service build helper but is not used by this multi-service configuration. Docker continues to build and serve the combined local application.

Run `vercel dev -L` from the repository root to test the service routes locally. Vercel Services are in beta. Before deploying, set the linked Vercel project's framework preset to Services in project settings; this setting is outside the repository, and no Vercel project is linked in this workspace. A public deployment URL is not configured here.

See the [Vercel Services documentation](https://vercel.com/docs/services) for project setup and configuration details.

## Data and AI disclosure

The Elexon raw source records are included in data/raw/ so the analysis can be reproduced without an external API dependency. Their request windows and record counts are recorded in manifest.json.

AI tools were used during implementation: OpenAI Codex assisted with research, implementation, and review. The calculations are derived from the included Elexon records; the interface does not use generated sample metrics or chart data.
