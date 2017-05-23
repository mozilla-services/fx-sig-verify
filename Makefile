
CONTAINER_NAME=ffsv/latest
INSTANCE_NAME=ffsv_latest

# custom build
ffsv.zip: Dockerfile
	docker build -t $(CONTAINER_NAME) .
	# get rid of anything old
	docker rm $(INSTANCE_NAME) || true	# okay if fails
	# retrieve the zip file
	docker run --name $(INSTANCE_NAME) $(CONTAINER_NAME)
	docker cp $(INSTANCE_NAME):/tmp/ffsv.zip .

upload: ffsv.zip
	aws lambda update-function-code --function-name hwine_ffsv_dev --zip-file fileb://$(PWD)/ffsv.zip

# vim: noet ts=8

