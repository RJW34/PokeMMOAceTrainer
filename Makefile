.PHONY: install test lint typecheck guard simulate replay batch dashboard check

install:
	python -m pip install -e .[dev,overlay]

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src

guard:
	python -m huntlab.guards.no_live_control .

simulate:
	huntlab simulate --scenario scenarios/magikarp_fishing.yaml --seed 7 --max-steps 100

replay:
	huntlab replay --input fixtures/magikarp_normal_then_shiny.jsonl

batch:
	python scripts/run_batch.py --runs 200

dashboard:
	python scripts/update_dashboard.py --runs 200

check: guard lint typecheck test
