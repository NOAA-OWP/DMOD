FROM python:3.7-alpine

WORKDIR /code

RUN pip install --no-cache-dir websockets jsonschema

COPY src/ src/
WORKDIR /code/src
CMD python handler_entry.py
