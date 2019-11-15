FROM python:3.7-alpine

WORKDIR /code

RUN pip install --no-cache-dir websockets jsonschema

COPY entrypoint.sh entrypoint.sh
COPY request_handler/ request_handler/
COPY requirements.txt requirements.txt
COPY schemas/ schemas/
COPY ssl/ ssl/
COPY tests/tests.py ./tests.py

CMD entrypoint.sh
