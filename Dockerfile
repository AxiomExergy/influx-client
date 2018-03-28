#################
# Build arguments
#
ARG PYTHON_IMAGE=python:3.5

############
# Unit tests
#
FROM $PYTHON_IMAGE AS common

RUN mkdir -p /usr/src/app

WORKDIR /usr/src/app

COPY setup.py .

# Installing deps
RUN pip install --compile .

# Install test dependencies
RUN pip install --compile .[test]

# Copy in app and tests
COPY influx/ ./influx/
COPY test/ ./test/
# COPY fixtures/ ./fixtures/

# Check code style and run static analysis along with tests
RUN flake8 . && \
    nosetests -v -a !services_required test/

