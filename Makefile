.PHONY: check test ci

check:
	python -m compileall -q src
	python -m ruff check src/shared/api/middleware.py src/shared/config/settings.py src/shared/runtime/preflight.py tests/test_r0_security_boundary.py

test:
	python -m pytest -q

ci: check test
