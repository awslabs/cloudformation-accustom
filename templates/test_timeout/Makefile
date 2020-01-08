package: test_timeout.deploy.ready.yaml

%.deploy.ready.yaml: %.deploy.yaml %.code.zip
ifndef BUCKET_TO_DEPLOY
	$(error BUCKET_TO_DEPLOY is undefined)
endif
	aws cloudformation package --template-file $< --s3-bucket ${BUCKET_TO_DEPLOY} --output-template-file $@

%.code.zip: %.code.py accustom.egg-info clean_code
	mkdir -p code_tmp
	pip install -r accustom.egg-info/requires.txt -t code_tmp
	cp -a ../../accustom code_tmp/
	cp $< code_tmp/
	cd code_tmp; zip $@ * -r
	mv code_tmp/$@ .

accustom.egg-info:
	cd ../..; make egg-info
	rm accustom.egg-info
	ln -s ../../accustom.egg-info .

clean: clean_code
	rm -f *.code.zip *.deploy.ready.yaml

clean_code:
	rm -fdr code_tmp

.PHONY: package clean clean_code accustom.egg-info
