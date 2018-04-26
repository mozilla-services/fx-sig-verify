# To customize for your aws account & bucket, export the following shell
# variables:
#	S3_BUCKET   <-- bucket to use
#	LAMBDA	    <-- function name
#
# All other AWS information is supplied the normal way.

DEV_IMAGE_NAME	:= fxsv/dev
BUILD_IMAGE_NAME:= fxsv/build
INSTANCE_NAME	:= fxsv_latest
VENV_NAME	:= venv

DOCKER_BUILD_OPTIONS  :=

.DEFAULT_GOAL	:= fxsv.zip

help:
	@echo "Targets:"
	@echo "    fxsv.zip (default) build zip file in docker container"
	@echo "    commit   update any files derived from another, prior to committing"
	@echo "    upload   upload and install zip file as latest lambda version"
	@echo "    invoke   invoke lambda with content already on S3"
	@echo "    populate_s3  upload test files to S3"
	@echo "    help     show this text"

# custom build
fxsv.zip: Dockerfile.build-environment.built
	docker cp $(INSTANCE_NAME):/tmp/fxsv.zip .
	# docker's host (VM) likely to have wrong time (on macOS). Update it
	touch fxsv.zip

.PHONY: commit
commit:
	rm -f Docker*built fxsv.zip
	$(MAKE) DOCKER_BUILD_OPTIONS=--no-cache fxsv.zip

upload: fxsv.zip
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	aws lambda update-function-code \
	    --region $${AWS_REGION} \
	    --function-name hwine_ffsv_dev \
	    --zip-file fileb://$(PWD)/fxsv.zip \

.PHONY: upload
publish: upload
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	aws lambda publish-version \
	    --region $${AWS_REGION} \
	    --function-name hwine_ffsv_dev \
	    --code-sha-256 "$$(openssl sha1 -binary -sha256 fxsv.zip | base64 | tee /dev/tty)" \
	    --description "$$(date -u +%Y%m%dT%H%M%S)" \

.PHONY: invoke invoke-no-error invoke-error invoke-mar
invoke-mar:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@test -n "$$LAMBDA" || ( echo "You must define LAMBDA" ; false )
	@rm -f invoke_output-mar-no-error.json
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	@echo "Should not return error (but some 'fail')"
	aws lambda invoke \
		--region $${AWS_REGION} \
		--function-name $(LAMBDA) \
		--payload "$$(sed 's/hwine-ffsv-dev/$(S3_BUCKET)/g' tests/data/S3_event_template-mar-no-error.json)" \
		invoke_output-mar-no-error.json ; \
	    if test -s invoke_output-mar-no-error.json; then \
		jq . invoke_output-mar-no-error.json ; \
	    fi
invoke-no-error:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@test -n "$$LAMBDA" || ( echo "You must define LAMBDA" ; false )
	@rm -f invoke_output-no-error.json
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	@echo "Should not return error (but some 'fail')"
	aws lambda invoke \
		--region $${AWS_REGION} \
		--function-name $(LAMBDA) \
		--payload "$$(sed 's/hwine-ffsv-dev/$(S3_BUCKET)/g' tests/data/S3_event_template-no-error.json)" \
		invoke_output-no-error.json ; \
	    if test -s invoke_output-no-error.json; then \
		jq . invoke_output-no-error.json ; \
	    fi

invoke-error:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@test -n "$$LAMBDA" || ( echo "You must define LAMBDA" ; false )
	@rm -f invoke_output-error.json
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	@echo "Should return error"
	aws lambda invoke \
		--region $${AWS_REGION} \
		--function-name $(LAMBDA) \
		--payload "$$(sed 's/hwine-ffsv-dev/$(S3_BUCKET)/g' tests/data/S3_event_template-error.json)" \
		invoke_output-error.json ; \
	    if test -s invoke_output-error.json; then \
		jq . invoke_output-error.json ; \
	    fi

invoke: invoke-no-error invoke-mar invoke-error

# idea from
# https://stackoverflow.com/questions/23032580/reinstall-virtualenv-with-tox-when-requirements-txt-or-setup-py-changes#23039826
.PHONY: tests
tests: .tox/venv.touch
	tox $(REBUILD_FLAG)

.tox/venv.touch: setup.py requirements.txt
	$(eval REBUILD_FLAG := --recreate)
	mkdir -p $$(dirname $@)
	touch $@

Dockerfile.dev-environment.built: Dockerfile.dev-environment requirements-dev.txt
	docker build $(DOCKER_BUILD_OPTIONS) -t $(DEV_IMAGE_NAME) -f $< .
	docker images $(DEV_IMAGE_NAME) >$@
	test -s $@ || rm $@

Dockerfile.build-environment: Dockerfile.dev-environment.built $(shell find src -name \*.py)
	touch $@

Dockerfile.build-environment.built: Dockerfile.build-environment requirements.txt
	docker build $(DOCKER_BUILD_OPTIONS) -t $(BUILD_IMAGE_NAME) -f $< .
	# get rid of anything old
	docker rm $(INSTANCE_NAME) || true	# okay if fails
	# retrieve the zip file
	docker run --name $(INSTANCE_NAME) $(BUILD_IMAGE_NAME)
	# delete old version, if any
	rm -f fxsv.zip
	docker ps -qa --filter name=$(INSTANCE_NAME) >$@
	test -s $@ || rm $@

$(VENV_NAME):
	virtualenv --python=python2.7 $@
	# if M2Crypto install fails, see notes in tox.ini
	. $(VENV_NAME)/bin/activate && echo req*.txt | xargs -n1 pip install -r
	@echo "Virtualenv created in $(VENV_NAME). You must activate before continuing."
	@false

# Hack -- assume if jquery isn't there, we haven't built, so need to
# install needed packages
dist/docs/_static/jquery.js:
	pip install -r docs/requirements.txt

.PHONY:	docs doc_build
doc_files := $(wildcard docs/.rst) docs/requirements.txt dist/docs/_static/jquery.js
doc_build: $(doc_files)
	sphinx-build -E -b html docs dist/docs
docs: doc_build
	@echo "Serving the docs on <http://localhost:8000/index.html>, ^C to stop"
	-cd dist/docs && python -m SimpleHTTPServer 8000

.PHONY:	populate_s3
populate_s3:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@echo "Populating s3://$(S3_BUCKET) using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	# authenticode test data
	aws s3 cp tests/data/32bit_new.exe "s3://$(S3_BUCKET)/32bit new.exe"
	aws s3 cp tests/data/32bit.exe "s3://$(S3_BUCKET)/32bit.exe"
	aws s3 cp tests/data/32bit_new.exe "s3://$(S3_BUCKET)/32bit_new.exe"
	aws s3 cp tests/data/32bit_new.exe "s3://$(S3_BUCKET)/32bit+new.exe"
	aws s3 cp tests/data/32bit_sha1.exe "s3://$(S3_BUCKET)/32bit_sha1.exe"
	aws s3 cp tests/data/bad_2.exe "s3://$(S3_BUCKET)/bad_2.exe"
	aws s3 cp tests/data/signtool.exe "s3://$(S3_BUCKET)/signtool.exe"
	aws s3 cp tests/data/32bit.exe "s3://$(S3_BUCKET)/nightly/test/Firefox bogus thingy.exe"
	# mar test data
	aws s3 cp tests/data/test-bz2.mar "s3://$(S3_BUCKET)/valid.mar"
	aws s3 cp tests/data/test-xz.mar "s3://$(S3_BUCKET)/nightly/invalid.mar"


	# vim: noet ts=8
