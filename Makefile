.DEFAULT_GOAL := check

compile:
	@python3 -m compileall -q skill/scripts tests

test:
	@set -e; for test_file in tests/test*.py; do \
	  python3 "$$test_file"; \
	done

assets:
	@python3 assets/build.py

assets-check:
	@python3 assets/build.py --check

check: compile test assets-check

.PHONY: compile test assets assets-check check
