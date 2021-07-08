# To customize for your aws account & bucket, export the following shell
# variables:
#	S3_BUCKET   <-- bucket to use
#	LAMBDA	    <-- function name
#
# All other AWS information is supplied the normal way.

PYTHON_VERSION := 3.6
VENV_NAME=venv
NOW := $(shell date -u +%Y-%m-%dT%H:%M:%S)

# dev account defaults
AWS_ACCOUNT_ID=361527076523
ECR_REPO_NAME=fx-sig-verify

# dev account defaults
AWS_REGION_DEV := us-west-2
AWS_PROFILE_DEV := cloudservices-aws-dev
AWS_ACCOUNT_ID_DEV := 927034868273
ECR_REPO_NAME_DEV := fx-sig-verify-dev

# Defaults for docker-debug
PRODUCTION_DEFAULT = 0	# set to 1 for skips
VERBOSE_DEFAULT = 2	# 2 is max, 0 is quiet
# show the details of the build (which build-kit hides by default)
# DOCKER_BUILD_OPTIONS := --progress plain

.PHONY: help
help:
	@echo "help		this list"
	@echo "docker-shell-prod    obtain shell in production docker container"
	@echo "docker-shell-debug   obtain shell in debug docker container"
	@echo ""
	@echo "upload		upload prod container to AWS"
	@echo "publish		publish prod container on AWS"
	@echo "invoke		execute test cases against AWS"
	@echo "invoke-docker    execute test cases against AWS from a"
	@echo "                 local docker instance with RIE installed"
	@echo "docker-debug	start local debug container"
	@echo "docker-build-all	build all containers"
	@echo "docker-build-prod    build production container"
	@echo "docker-build-debug   build debug container from prod"
	@echo "tests		execute local tests locally via tox"
	@echo "docker-debug-tests   execute local tests in docker"
	@echo "populate_s3	upload test data to S3"
	@echo ""
	@echo "clean            remove built files"
	@echo ""
	@echo "generate-docs    Generate docs locally"



.PHONY: clean
clean:
	rm -f Dockerfile*built
	rm -f fxsv.zip

.PHONY: upload upload-dev
upload: docker-build-prod
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	docker tag fxsigverify $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPO_NAME)
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPO_NAME)

upload-dev:
	$(MAKE) AWS_PROFILE=$(AWS_PROFILE_DEV) AWS_ACCOUNT_ID=$(AWS_ACCOUNT_ID_DEV) ECR_REPO_NAME=$(ECR_REPO_NAME_DEV) AWS_REGION=$(AWS_REGION_DEV) upload

.PHONY: publish publish-dev
publish: upload
	@echo "Go use the console - aws cli is currently f'd up wrt lambda containers"
	@false
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	which aws2
	aws2 lambda update-function-code \
	    --region $${AWS_REGION} \
	    --function-name hwine_fxsv_container \
	    --image-uri 927034868273.dkr.ecr.us-west-2.amazonaws.com/fx-sig-verify-dev:latest \
	    --dry-run \

publish-dev:
	$(MAKE) AWS_ACCOUNT_ID=$(AWS_ACCOUNT_ID_DEV) ECR_REPO_NAME=$(ECR_REPO_NAME_DEV) publish

# The following targets exercise the actual lambda code, and having that
# code interact with real AWS services. So valid credentials must be
# applied.
#
# The "-docker" versions do so to the code deployed in a container with
# the lambda Remote Interface Emulater installed
#
# The ones without that suffix invoke the lambda on AWS
.PHONY: invoke invoke-no-error invoke-error invoke-docker invoke-no-error-docker invoke-error-docker
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
		                  -e 's/1970-01-01T00:00:00/$(NOW)/g' \
				  tests/data/S3_event_template-no-error.json)" \
		invoke_output-no-error.json ; \
	    if test -s invoke_output-no-error.json; then \
		jq . invoke_output-no-error.json ; \
	    fi

invoke-no-error-docker:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@test -n "$$LAMBDA" || ( echo "You must define LAMBDA" ; false )
	@rm -f invoke_output-no-error.json
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	@echo "Should not return error (but some 'fail')"
	curl http://localhost:9000/2015-03-31/functions/function/invocations \
		--data "$$(sed -e 's/hwine-ffsv-dev/$(S3_BUCKET)/g' \
		                  -e 's/1970-01-01T00:00:00/$(NOW)/g' \
				  tests/data/S3_event_template-no-error.json)" \
		> invoke_output-no-error.json ; \
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
		                  -e 's/1970-01-01T00:00:00/$(NOW)/g' \
				  tests/data/S3_event_template-error.json)" \
		invoke_output-error.json ; \
	    if test -s invoke_output-error.json; then \
		jq . invoke_output-error.json ; \
	    fi

invoke-error-docker:
	@test -n "$$S3_BUCKET" || ( echo "You must define S3_BUCKET" ; false )
	@test -n "$$LAMBDA" || ( echo "You must define LAMBDA" ; false )
	@rm -f invoke_output-error.json
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	@echo "Should return error"
	curl http://localhost:9000/2015-03-31/functions/function/invocations \
		--data "$$(sed -e 's/hwine-ffsv-dev/$(S3_BUCKET)/g' \
		                  -e 's/1970-01-01T00:00:00/$(NOW)/g' \
				  tests/data/S3_event_template-error.json)" \
		> invoke_output-error.json ; \
	    if test -s invoke_output-error.json; then \
		jq . invoke_output-error.json ; \
	    fi

invoke: invoke-no-error invoke-error
invoke-docker: invoke-no-error-docker invoke-error-docker

PHONY: docker-build-prod
docker-build-prod:
	docker build $(DOCKER_BUILD_OPTIONS) -t fxsigverify -f Dockerfile.buster .

PHONY: docker-build-debug
docker-build-debug: docker-build-prod
	env PRODUCTION=$(or $(PRODUCTION),$(PRODUCTION_DEFAULT)) \
	docker build $(DOCKER_BUILD_OPTIONS) -t fxsv-debug -f Dockerfile.buster.debug .

PHONY: docker-build-all
docker-build-all: docker-build-prod docker-build-debug

# We don't make docker-debug depend on docker-build-debug, as we may
# want several runs as we change code
PHONY: docker-debug
docker-debug:
	bash -xc ' \
	declare -p $${!AWS*} ; \
	env VERBOSE=2 PRODUCTION=0 \
	docker run --rm -it \
	    -e AWS_ACCESS_KEY_ID \
	    -e AWS_REGION \
	    -e AWS_DEFAULT_REGION \
	    -e AWS_SECRET_ACCESS_KEY \
	    -e AWS_SECURITY_TOKEN \
	    -e AWS_SESSION_TOKEN \
	    -e AWS_VAULT \
	    -e PRODUCTION \
	    -e SNSARN \
	    -e VERBOSE \
	    -p 9000:8080 \
	    fxsv-debug \
	'

PHONY: docker-shell-prod
docker-shell-prod:
	@echo "N.B. no environment variables set"
	docker run --rm -it --entrypoint bash fxsigverify

PHONY: docker-shell-debug
docker-shell-debug:
	@echo "N.B. no environment variables set"
	docker run --rm -it --entrypoint bash fxsv-debug

PHONY: docker-debug-tests
docker-debug-tests:
	docker run --rm --entrypoint pytest fxsv-debug:latest tests

# idea from
# https://stackoverflow.com/questions/23032580/reinstall-virtualenv-with-tox-when-requirements-txt-or-setup-py-changes#23039826
.PHONY: tests
tests: .tox/venv.touch
	tox $(REBUILD_FLAG)

.tox/venv.touch: setup.py requirements.txt
	$(eval REBUILD_FLAG := --recreate)
	mkdir -p $$(dirname $@)
	touch $@


$(VENV_NAME):
	python$(PYTHON_VERSION) -m venv  $@
	. $(VENV_NAME)/bin/activate && pip install --upgrade pip
	. $(VENV_NAME)/bin/activate && echo req*.txt | xargs -n1 pip install -r
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
	aws s3 cp tests/data/2020-05-32bit.exe "s3://$(S3_BUCKET)/2020-05-32bit.exe"
	aws s3 cp tests/data/FxStub-87.0b2.exe "s3://$(S3_BUCKET)/FxStub-87.0b2.exe"
	aws s3 cp tests/data/2021-05-signable-file.exe "s3://$(S3_BUCKET)/2021-05-signable-file.exe"


.PHONY: generate-docs
generate-docs:
	tox -e docs

# vim: noet ts=8
