FROM alpine:3.15

RUN apk update && apk upgrade && apk add docker bash && mkdir -p /dmod

COPY ./scripts /dmod/scripts

ENV OUT_OF_GIT_REPO='true'

ENTRYPOINT ["/dmod/scripts/init_object_store_dataset_volumes.sh"]
