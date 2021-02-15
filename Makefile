# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

build:
	python setup.py sdist

clean: clean_build

clean_build:
	rm -fdr dist

.PHONY: build clean clean_build