.PHONY: test

simpletron: simpletron.c
	cc simpletron.c -o simpletron

test: simpletron
	python3 run_tests.py
