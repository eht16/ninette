# -*- coding: utf-8 -*-
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

GPG_KEY_ID ?= "579347E6C71A77FA"

release:
	# cleanup
	rm -rf dist build *.egg-info
	# build package
	python -m build
	# show upload hint
	@echo "Call 'make upload-test' or make upload' to publish on PyPI and the 'make tag' to create a GIT tag"

upload-check:
	twine check dist/*

upload: upload-check
	twine upload --sign --identity ${GPG_KEY_ID} --repository pypi dist/*

upload-test: upload-check
	twine upload --sign --identity ${GPG_KEY_ID} --repository pypi-test dist/*

tag:
	# ensure $VERSION is set
	test ${VERSION} || (echo "VERSION must be set, e.g.: 'make VERSION=1.2.3'" && exit 1)
	# tag
	git push
	git tag -s ${VERSION} -m "Tag release ${VERSION}"
	git push origin ${VERSION}

tox:
	tox

.SILENT:tag release
