.PHONY: install ingest api frontend test evaluate docker

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -r backend/requirements-dev.txt
	cd frontend && npm install

ingest:
	PYTHONPATH=backend python backend/scripts/ingest.py --rebuild

api:
	PYTHONPATH=backend uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	PYTHONPATH=backend pytest backend/tests -q

evaluate:
	PYTHONPATH=backend python backend/scripts/evaluate.py

docker:
	docker compose up --build
