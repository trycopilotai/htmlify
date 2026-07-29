.DEFAULT_GOAL := check

compile:
	@python3 -m compileall -q skill/scripts tests

test:
	@set -e; for test_file in tests/test*.gpt.py; do \
	  python3 "$$test_file"; \
	done

assets:
	@python3 assets/build.gpt.py

check: compile test

.PHONY: compile test assets check
