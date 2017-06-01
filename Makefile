
DEV_IMAGE_NAME=ffsv/dev
BUILD_IMAGE_NAME=ffsv/build
INSTANCE_NAME=ffsv_latest

# custom build
ffsv.zip: Dockerfile.build-environment.built

ffsv.zip.old: Dockerfile
	docker build -t $(BUILD_IMAGE_NAME) .
	# get rid of anything old
	docker rm $(INSTANCE_NAME) || true	# okay if fails
	# retrieve the zip file
	docker run --name $(INSTANCE_NAME) $(BUILD_IMAGE_NAME)
	docker cp $(INSTANCE_NAME):/tmp/ffsv.zip .

upload: ffsv.zip
	aws lambda update-function-code --function-name hwine_ffsv_dev --zip-file fileb://$(PWD)/ffsv.zip

Dockerfile.dev-environment.built: Dockerfile.dev-environment
	docker build -t $(USER):prestaged -f $< .
	docker images $(USER):prestaged >$@
	test -s $@ || rm $@

Dockerfile.build-environment: Dockerfile.dev-environment.built

Dockerfile.build-environment.built: Dockerfile.build-environment
	docker build -t $(BUILD_IMAGE_NAME) -f $< .
	# get rid of anything old
	docker rm $(INSTANCE_NAME) || true	# okay if fails
	# retrieve the zip file
	docker run --name $(INSTANCE_NAME) $(BUILD_IMAGE_NAME)
	docker cp $(INSTANCE_NAME):/tmp/ffsv.zip .
	docker ps -qa --filter name=$(INSTANCE_NAME) >$@
	test -s $@ || rm $@

.PHONY: Dockerfile.build-environment upload

# vim: noet ts=8

