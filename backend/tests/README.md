# Test layout

- `unit/`: isolated business rules and adapters with fake HTTP/providers.
- `integration/`: FastAPI, service composition and temporary SQLite databases.
- `regression/`: deterministic fixtures for previously reproduced route/timetable failures.
- `e2e/`: opt-in Playwright application workflows. Live cases never write to Notion.
- `data/`: shared non-sensitive fixtures; `factories.py`: shared domain builders.

Run `pytest` from the repository root, or `docker compose exec -T backend pytest`.
Run individual groups with `pytest backend/tests/unit` (inside Docker: `pytest tests/unit`).

Browser fixture workflows: `AUTOTRIP_E2E=1 pytest backend/tests/e2e`.
Live browser workflows additionally require `AUTOTRIP_LIVE_UI=1` and the actual local application.
Set `AUTOTRIP_UI_URL` when the application uses a different URL; tests otherwise use
`http://host.docker.internal:5174`. Live tests are not part of the default offline suite.

Temporary investigation scripts, provider dumps and old manual Notion scripts are
preserved under ignored `.local/`; they are not tests and must not be committed.
