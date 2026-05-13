.PHONY: test

simpletron: simpletron.c
	cc -Wall -Wextra -Wpedantic -std=c11 -O2 simpletron.c -o simpletron

test: simpletron
	python3 run_tests.py
