.PHONY: check test ci

check:
	python -m compileall -q src
	python -m ruff check src tests

test:
	python -m pytest -q

ci: check test
