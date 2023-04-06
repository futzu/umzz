PY3 = python3
PIP3 = pip3
PYPY3 = pypy3

default: install

fmt:
	black setup.py
	black */*.py

commit: fmt
	git pull
	git commit $1
	git push	

clean:
	rm -f dist/*
	rm -rf build/*

pypy3: clean
	$(PYPY3) setup.py sdist bdist_wheel
	$(PYPY3) setup.py install	

install: clean pkg
	$(PY3)  setup.py install

pkg: clean
	$(PY3) setup.py sdist bdist_wheel

upload: clean pkg	
	twine upload dist/*

