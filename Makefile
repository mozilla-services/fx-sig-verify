
DEV_IMAGE_NAME=fxsv/dev
BUILD_IMAGE_NAME=fxsv/build
INSTANCE_NAME=fxsv_latest

# custom build
fxsv.zip: Dockerfile.build-environment.built

.PHONY: upload
upload: fxsv.zip
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	aws lambda update-function-code \
	    --function-name hwine_ffsv_dev \
	    --zip-file fileb://$(PWD)/fxsv.zip \

publish: upload
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	aws lambda publish-version \
	    --function-name hwine_ffsv_dev \
	    --code-sha-256 "$$(openssl sha1 -binary -sha256 fxsv.zip | base64 | tee /dev/tty)" \
	    --description "$$(date -u +%Y%m%dT%H%M%S)" \

.PHONY: invoke
invoke:
	@rm -f invoke_output.json
	@echo "Using AWS credentials for $$AWS_DEFAULT_PROFILE in $$AWS_REGION"
	aws lambda invoke \
		--function-name hwine_ffsv_dev \
		--payload "$$(cat tests/data/S3_event_template.json)" \
		invoke_output.json ; \
	    if test -s invoke_output.json; then \
		jq . invoke_output.json ; \
	    fi

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

# vim: noet ts=8
