build: egg-info
	python setup.py sdist

egg-info: accustom.egg-info

accustom.egg-info:
	python setup.py egg_info

clean: clean-egg clean-build

clean-egg:
	rm -fdr accustom.egg-info

clean-build:
	rm -fdr dist

.PHONY: build egg-info clean clean-egg clean-build