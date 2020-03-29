# To customize for your aws account & bucket, export the following shell
# variables:
#	S3_BUCKET   <-- bucket to use
#	LAMBDA	    <-- function name
#
# All other AWS information is supplied the normal way.

DEV_IMAGE_NAME=fxsv/dev
BUILD_IMAGE_NAME=fxsv/build
INSTANCE_NAME=fxsv_latest
VENV_NAME=venv

# custom build
fxsv.zip: Dockerfile.build-environment.built


.PHONY: help
help:
	@echo "fxsv.zip	DEFAULT target - build lambda package"
	@echo "help		this list"
	@echo "docker-shell	obtain shell in docker container"
	@echo "docker-test	run all tests in docker container"
	@echo ""
	@echo "upload		upload lambda function to AWS"
	@echo "publish		publish lambda function on AWS"
	@echo "invoke		execute test cases on AWS"
	@echo "tests		execute tests locally via tox"
	@echo "docker-test      execute tests in docker image"
	@echo "populate_s3	upload test data to S3"
	@echo ""
	@echo "clean            remove built files"



.PHONY: clean
clean:
	rm -f Dockerfile*built
	rm -f fxsv.zip

.PHONY: upload
upload: fxsv.zip
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	aws lambda update-function-code \
	    --region $${AWS_REGION} \
	    --function-name hwine_ffsv_dev \
	    --zip-file fileb://$(PWD)/fxsv.zip \

.PHONY: publish
publish: upload
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	aws lambda publish-version \
	    --region $${AWS_REGION} \
	    --function-name hwine_ffsv_dev \
	    --code-sha-256 "$$(openssl sha1 -binary -sha256 fxsv.zip | base64 | tee /dev/tty)" \
	    --description "$$(date -u +%Y%m%dT%H%M%S)" \

.PHONY: invoke invoke-no-error invoke-error
invoke-no-error:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@test -n "$$LAMBDA" || ( echo "You must define LAMBDA" ; false )
	@rm -f invoke_output-no-error.json
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	@echo "Should not return error (but some 'fail')"
	aws lambda invoke \
		--region $${AWS_REGION} \
		--function-name $(LAMBDA) \
		--payload "$$(sed -e 's/hwine-ffsv-dev/$(S3_BUCKET)/g' \
		                  -e 's/1970-01-01T00:00:00/$$(date +%Y-%m-%dT%H:%M:%S)/g' \
				  tests/data/S3_event_template-no-error.json)" \
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
		--payload "$$(sed -e 's/hwine-ffsv-dev/$(S3_BUCKET)/g' \
		                  -e 's/1970-01-01T00:00:00/$$(date +%Y-%m-%dT%H:%M:%S)/g' \
				  tests/data/S3_event_template-error.json)" \
		invoke_output-error.json ; \
	    if test -s invoke_output-error.json; then \
		jq . invoke_output-error.json ; \
	    fi

invoke: invoke-no-error invoke-error

PHONY: docker-shell
docker-shell: Dockerfile.build-environment.built
	@echo Working directory mounted at /root/src
	docker run --rm -it --volume $PWD:/root/src fxsv/build:latest bash

PHONY: docker-test
docker-test: Dockerfile.build-environment.built
	docker run --rm -it --volume $PWD:/root fxsv/build:latest pytest tests

# idea from
# https://stackoverflow.com/questions/23032580/reinstall-virtualenv-with-tox-when-requirements-txt-or-setup-py-changes#23039826
.PHONY: tests
tests: .tox/venv.touch
	tox $(REBUILD_FLAG)

.tox/venv.touch: setup.py requirements.txt
	$(eval REBUILD_FLAG := --recreate)
	mkdir -p $$(dirname $@)
	touch $@

Dockerfile.dev-environment.built: Dockerfile.dev-environment
	docker build -t $(DEV_IMAGE_NAME) -f $< .
	docker images $(DEV_IMAGE_NAME) >$@
	test -s $@ || rm $@

Dockerfile.build-environment: Dockerfile.dev-environment.built $(shell find src -name \*.py)
	touch $@

Dockerfile.build-environment.built: Dockerfile.build-environment
	docker build -t $(BUILD_IMAGE_NAME) -f $< .
	# get rid of anything old
	docker rm $(INSTANCE_NAME) || true	# okay if fails
	# retrieve the zip file
	docker run --name $(INSTANCE_NAME) $(BUILD_IMAGE_NAME)
	# delete old version, if any
	rm -f fxsv.zip
	docker cp $(INSTANCE_NAME):/tmp/fxsv.zip .
	# docker's host (VM) likely to have wrong time (on macOS). Update it
	touch fxsv.zip
	docker ps -qa --filter name=$(INSTANCE_NAME) >$@
	test -s $@ || rm $@

$(VENV_NAME):
	virtualenv --python=python2.7 $@
	source $(VENV_NAME)/bin/activate && echo req*.txt | xargs -n1 pip install -r
	@echo "Virtualenv created in $(VENV_NAME). You must activate before continuing."
	@false

.PHONY:	populate_s3
populate_s3:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@echo "Populating s3://$(S3_BUCKET) using current credentials & region"
	aws s3 cp tests/data/32bit_new.exe "s3://$(S3_BUCKET)/32bit new.exe"
	aws s3 cp tests/data/32bit.exe "s3://$(S3_BUCKET)/32bit.exe"
	aws s3 cp tests/data/32bit_new.exe "s3://$(S3_BUCKET)/32bit_new.exe"
	aws s3 cp tests/data/32bit_new.exe "s3://$(S3_BUCKET)/32bit+new.exe"
	aws s3 cp tests/data/32bit_sha1.exe "s3://$(S3_BUCKET)/32bit_sha1.exe"
	aws s3 cp tests/data/bad_2.exe "s3://$(S3_BUCKET)/bad_2.exe"
	aws s3 cp tests/data/signtool.exe "s3://$(S3_BUCKET)/signtool.exe"
	aws s3 cp tests/data/32bit.exe "s3://$(S3_BUCKET)/nightly/test/Firefox bogus thingy.exe"
	aws s3 cp tests/data/2019-06-64bit.exe "s3://$(S3_BUCKET)/2019-06-64bit.exe"

# vim: noet ts=8
