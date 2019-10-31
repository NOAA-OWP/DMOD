FROM python:3.7-alpine

WORKDIR /code

RUN pip install --no-cache-dir websockets jsonschema

COPY schemas /code/schemas/
COPY ssl/certificate.pem /code/ssl/
COPY tests.py /code/
CMD python tests.py
