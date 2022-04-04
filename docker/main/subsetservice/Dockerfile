# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-sources as sources

# Need to use base, rather than -alpine, image variant, due to C++ lib
# dependencies related to pandas when using the monitordata package.
#FROM python:3.8

FROM python:3.8-alpine3.15

ARG comms_package_name
ARG modeldata_package_name
ARG subsetservice_package_name

WORKDIR /code

# Needed until subsetservice package dependencies like hypy, etc. are publish, as opposed to pulled via git
#ARG REQUIRE="git gcc gfortran musl-dev python3-dev libpng-dev"
#RUN apk update && apk upgrade && apk add --no-cache ${REQUIRE}
#RUN apt-get update && apt-get upgrade && apt-get -y install ${REQUIRE}
#RUN ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1

#RUN echo "http://dl-8.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories
RUN apk --no-cache --update-cache add git gcc gfortran python3 python3-dev py-pip build-base wget geos-dev gdal-dev freetype-dev libpng-dev openblas-dev
RUN ln -s /usr/include/locale.h /usr/include/xlocale.h

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

COPY ./entrypoint.sh entrypoint.sh
# Install custom and generally available packages, starting with any custom from external source image
# Do these first packages separately first to work around some current issues (2/1/2022)
# TODO: fix root cause for problem this works around
RUN pip install websockets MarkupSafe yarl wrapt \
    && pip install --no-index --find-links=/DIST ${subsetservice_package_name} \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

ENTRYPOINT ["/code/entrypoint.sh"]
