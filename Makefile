all:
	pip uninstall forward
	python setup.py sdist
	pip install -r requirements.txt dist/forward-0.1.0.tar.gz

test:
	python setup.py test
