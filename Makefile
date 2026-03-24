.PHONY: dev dev-server dev-client test test-server install install-server install-client

install: install-server install-client

install-server:
	cd server && uv pip install -e ".[dev]"

install-client:
	cd client && npm install

dev-server:
	cd server && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-client:
	cd client && npm run dev

test: test-server

test-server:
	cd server && .venv/bin/pytest -v
