build: egg-info
	python setup.py sdist

egg-info: accustom.egg-info

accustom.egg-info:
	python setup.py egg_info

clean: clean_build clean_egg

clean_egg:
	rm -fdr accustom.egg-info

clean_build:
	rm -fdr dist

.PHONY: build egg-info clean clean_egg clean_build