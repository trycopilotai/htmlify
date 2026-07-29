.DEFAULT_GOAL := check

compile:
	@python3 -m compileall -q skill/scripts tests

test:
	@set -e; for test_file in tests/test*.gpt.py; do \
	  python3 "$$test_file"; \
	done

check: compile test

.PHONY: compile test check
