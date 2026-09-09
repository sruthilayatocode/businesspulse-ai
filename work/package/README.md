# BusinessPulse AI Tesla MVP

BusinessPulse AI turns news into an explainable Tesla business-risk briefing. The initial MVP uses a synthetic Tesla exposure profile; it does not claim access to Tesla private supplier, ERP, inventory, or sales data.

## What works now

- Tesla dashboard with critical/high risk prioritization and estimated exposure
- Gemini-powered article classification into supply-chain, market, competitor, or regulatory events
- Entity-to-exposure mapping and transparent priority scoring
- Daily-style executive briefing API
- Tesla demo events that work without any API key
- Exasol production DDL in `sql/exasol_schema.sql`

## Run locally

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
2. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Start the app:

   ```powershell
   uvicorn app:app --reload
   ```

4. Open `http://127.0.0.1:8000`, then choose **Load Tesla demo events**.

## Gemini configuration

Set `GEMINI_API_KEY` only in `.env`. `POST /api/events/analyze` sends an article to Gemini and expects a JSON analysis with a category, entities, score inputs, summary, and recommended action. If the key is absent, the seeded demo uses deterministic local analysis so the dashboard remains usable.

## Exasol deployment

Run `sql/exasol_schema.sql` in Exasol. The current runtime uses SQLite to make the prototype start without database credentials. The next implementation step is replacing the `db()` adapter in `app.py` with `pyexasol.connect()` and setting `DATABASE_BACKEND=exasol`; the provided schema is the matching production data model.

## MVP demo scenario

Load the simulated Taiwan chip disruption. The service classifies it as a supply-chain event, connects it to the demo Taiwan chip supplier, applies inventory and dependency exposure, scores the risk, estimates exposure, and recommends a response.
