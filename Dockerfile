FROM amazonlinux:latest

WORKDIR /usr/src/app

# get the tools we need
RUN yum install -y python27-devel python27-pip gcc openssl-devel zip findutils
RUN pip install --upgrade pip setuptools

# get the main source
COPY . .

# Dev requirements first - "mis install" them, remove, then install for
# real
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# Runtime requirements in the src tree, now that it's there
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -t src/lib

#CMD [ "python", "setup.py" "ldist"]

