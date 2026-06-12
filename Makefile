.PHONY: install test demo validate-ais dashboard coverage rf-demo clean

install:
	pip install -e ".[dev]"

test:
	PYTHONPATH=src python -m pytest tests/ -v

demo:
	PYTHONPATH=src python -m boobook.cli demo --out artifacts/demo

validate-ais:
	PYTHONPATH=src python -m boobook.cli validate-ais data/sample/sample_ais_events.csv --out data/processed/sample

dashboard:
	PYTHONPATH=src python -m boobook.cli dashboard --processed data/processed/sample --out artifacts/Boobook_Investor_Dashboard.html

coverage:
	PYTHONPATH=src python -m boobook.cli coverage

rf-demo:
	PYTHONPATH=src python -m boobook.cli rf-demo --out artifacts

clean:
	rm -rf data/processed artifacts/demo __pycache__ src/boobook/__pycache__ .pytest_cache
