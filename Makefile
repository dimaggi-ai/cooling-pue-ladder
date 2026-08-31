test:
	python3 -m unittest discover -s tests -v

figures:
	python3 run.py

.PHONY: test figures
