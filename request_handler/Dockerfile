FROM python:3.7-alpine

WORKDIR /code

RUN pip install --no-cache-dir websockets jsonschema

COPY request_handler/ request_handler/
COPY schemas/ schemas/
COPY ssl/ ssl/
COPY tests/tests.py ./tests.py

CMD python -m request_handler
