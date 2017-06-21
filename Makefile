
DEV_IMAGE_NAME=fxsv/dev
BUILD_IMAGE_NAME=fxsv/build
INSTANCE_NAME=fxsv_latest

# custom build
fxsv.zip: Dockerfile.build-environment.built

upload: fxsv.zip
	aws lambda update-function-code --function-name hwine_ffsv_dev --zip-file fileb://$(PWD)/fxsv.zip

invoke:
	aws lambda invoke --function-name hwine_ffsv_dev --payload "$$(cat tests/data/S3_event_template.json)" test_output.json ; jq . test_output.json

Dockerfile.dev-environment.built: Dockerfile.dev-environment
	docker build -t $(DEV_IMAGE_NAME) -f $< .
	docker images $(DEV_IMAGE_NAME) >$@
	test -s $@ || rm $@

Dockerfile.build-environment: Dockerfile.dev-environment.built $(shell find . -name \*.py)
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

.PHONY: upload invoke

# vim: noet ts=8
