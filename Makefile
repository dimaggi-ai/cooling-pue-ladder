test:
	python3 -m unittest discover -s tests -v

validate:
	python3 -c "import sys; from cooling.cli import main; sys.exit(main(['validate']))"

figures:
	python3 run.py

.PHONY: test validate figures
