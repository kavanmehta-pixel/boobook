.PHONY: install test demo validate-ais dashboard coverage rf-demo clean

install:
	pip install -e ".[dev]"

test:
	PYTHONPATH=src python -m pytest tests/ -v

demo:
	PYTHONPATH=src python -m ninox.cli demo --out artifacts/demo

validate-ais:
	PYTHONPATH=src python -m ninox.cli validate-ais data/sample/sample_ais_events.csv --out data/processed/sample

dashboard:
	PYTHONPATH=src python -m ninox.cli dashboard --processed data/processed/sample --out artifacts/Ninox_Investor_Dashboard.html

coverage:
	PYTHONPATH=src python -m ninox.cli coverage

rf-demo:
	PYTHONPATH=src python -m ninox.cli rf-demo --out artifacts

clean:
	rm -rf data/processed artifacts/demo __pycache__ src/ninox/__pycache__ .pytest_cache
