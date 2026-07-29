.DEFAULT_GOAL := check

compile:
	@python3 -m compileall -q skill/scripts tests

test:
	@python3 -m unittest discover -s tests -p 'test*.gpt.py' -v

check: compile test

.PHONY: compile test check
