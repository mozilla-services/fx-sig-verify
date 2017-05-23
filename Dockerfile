FROM amazonlinux:latest

WORKDIR /usr/src/app

# get the tools we need
RUN yum install -y python27-devel python27-pip gcc openssl-devel zip findutils
RUN pip install --upgrade pip setuptools

# get the main source
COPY . .

# Dev requirements
#COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# Runtime requirements in the src tree, now that it's there
#COPY requirements.txt ./
RUN pip install -r requirements.txt -t src/lib

# Cause everything to be compiled
RUN pip install -t /tmp/ffsv .

# zip up the result
RUN cd /tmp/ffsv && zip -9r ../ffsv.zip .

