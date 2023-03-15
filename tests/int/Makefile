# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

execute: redact.executed timeout.executed
deploy: redact.deployed timeout.deployed
package: redact.deploy.ready.yaml timeout.deploy.ready.yaml

redact.executed: redact.execute.yaml redact.deployed
	aws cloudformation deploy --template-file $< --stack-name $(subst .,-,$@) --disable-rollback
	echo $(subst .,-,$@) > $@

timeout.executed: timeout.execute.yaml timeout.deployed
	-aws cloudformation deploy --template-file $< --stack-name $(subst .,-,$@) --disable-rollback
	echo $(subst .,-,$@) > $@

%.deployed: %.deploy.ready.yaml
	aws cloudformation deploy --template-file $< --stack-name $(subst .,-,$@) --capabilities CAPABILITY_IAM
	echo $(subst .,-,$@) > $@

%.deploy.ready.yaml: %.deploy.yaml %.zip
ifndef BUCKET_TO_DEPLOY
	$(error BUCKET_TO_DEPLOY is undefined)
endif
	aws cloudformation package --template-file $< --s3-bucket ${BUCKET_TO_DEPLOY} --output-template-file $@

%.zip: %.py
	mkdir -p code_tmp
	python3 -m pip install -r ../../requirements.txt -t code_tmp --platform manylinux2014_x86_64 --python-version 3.8 \
		--implementation cp --only-binary=:all: --compile
	cp -a ../../accustom code_tmp/
	cp $< code_tmp/
	cd code_tmp; zip $@ * -r
	mv code_tmp/$@ .
	rm -fdr code_tmp

clean: undeploy
	rm -f *.deploy.ready.yaml
	rm -f *.zip

undeploy: unexecute
	ls *.deployed | tr . - | xargs -n1 aws cloudformation delete-stack --stack-name
	ls *.deployed | tr . - | xargs -n1 aws cloudformation wait stack-delete-complete --stack-name
	rm -f *.deployed

unexecute:
	ls *.executed | tr . - | xargs -n1 aws cloudformation delete-stack --stack-name
	ls *.executed | tr . - | xargs -n1 aws cloudformation wait stack-delete-complete --stack-name
	rm -f *.executed

.PHONY: package deploy execute clean unexecute undeploy
