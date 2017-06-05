
DEV_IMAGE_NAME=fxsv/dev
BUILD_IMAGE_NAME=fxsv/build
INSTANCE_NAME=fxsv_latest

# custom build
fxsv.zip: Dockerfile.build-environment.built

upload: fxsv.zip
	aws lambda update-function-code --function-name hwine_fxsv_dev --zip-file fileb://$(PWD)/fxsv.zip

Dockerfile.dev-environment.built: Dockerfile.dev-environment
	docker build -t $(DEV_IMAGE_NAME) -f $< .
	docker images $(DEV_IMAGE_NAME) >$@
	test -s $@ || rm $@

Dockerfile.build-environment: Dockerfile.dev-environment.built

Dockerfile.build-environment.built: Dockerfile.build-environment
	docker build -t $(BUILD_IMAGE_NAME) -f $< .
	# get rid of anything old
	docker rm $(INSTANCE_NAME) || true	# okay if fails
	# retrieve the zip file
	docker run --name $(INSTANCE_NAME) $(BUILD_IMAGE_NAME)
	docker cp $(INSTANCE_NAME):/tmp/fxsv.zip .
	docker ps -qa --filter name=$(INSTANCE_NAME) >$@
	test -s $@ || rm $@

.PHONY: Dockerfile.build-environment upload

# vim: noet ts=8
