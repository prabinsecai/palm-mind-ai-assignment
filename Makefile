install:
	python -m pip install -e '.[test]'

run:
	uvicorn app.main:app --reload

test:
	pytest -q

compose:
	docker compose up --build

compose-down:
	docker compose down
