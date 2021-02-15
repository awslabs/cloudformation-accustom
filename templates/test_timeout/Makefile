# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

package: test_timeout.deploy.ready.yaml

%.deploy.ready.yaml: %.deploy.yaml %.zip
ifndef BUCKET_TO_DEPLOY
	$(error BUCKET_TO_DEPLOY is undefined)
endif
	aws cloudformation package --template-file $< --s3-bucket ${BUCKET_TO_DEPLOY} --output-template-file $@

%.zip: %.py accustom.egg-info clean_code
	mkdir -p code_tmp
	python3 -m pip install -r accustom.egg-info/requires.txt -t code_tmp
	cp -a ../../accustom code_tmp/
	cp $< code_tmp/
	cd code_tmp; zip $@ * -r
	mv code_tmp/$@ .

accustom.egg-info:
	cd ../..; make egg-info
	rm -fdr accustom.egg-info
	ln -s ../../accustom.egg-info .

clean: clean_code clean_egg
	rm -f *.zip *.deploy.ready.yaml

clean_code:
	rm -fdr code_tmp

clean_egg:
	rm -fdr accustom.egg-info

.PHONY: package clean clean_code clean_egg accustom.egg-info
