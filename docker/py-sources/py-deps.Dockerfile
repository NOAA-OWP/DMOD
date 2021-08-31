################################################################################################################
################################################################################################################
##### Create foundational level build stage with initial structure
FROM python:3.8-alpine as foundation
ARG REQUIRE="gcc g++ musl-dev gdal-dev libffi-dev openssl-dev rust cargo git"
RUN apk update && apk upgrade && apk add --no-cache ${REQUIRE}
# Along with setup and wheel to build, install all project pip dependencies for package building later
RUN mkdir /DIST && mkdir /nwm_service && pip install --upgrade pip

################################################################################################################
################################################################################################################
##### Create individual, semi-independent stages for building some of the longer-to-build packages to isolate
##### them in the cache.  This has the additional benefit of parallelizing these build steps.
FROM foundation as build_pandas_dep
RUN pip install --upgrade pip
ARG PANDAS_VERSION=""
RUN pip wheel --no-cache-dir --wheel-dir /DIST --prefer-binary pandas${PANDAS_VERSION}

############################################################
FROM foundation as build_numpy_dep
RUN pip install --upgrade pip
ARG NUMPY_VERSION=">=1.20.1"
RUN pip wheel --no-cache-dir --wheel-dir /DIST --prefer-binary numpy${NUMPY_VERSION}

############################################################
#FROM foundation as build_geopandas_dep
#RUN pip install --upgrade pip
#ARG GEOPANDAS_VERSION=""
#RUN pip wheel --no-cache-dir --wheel-dir /DIST --prefer-binary geopandas${GEOPANDAS_VERSION}

############################################################
FROM foundation as build_cryptograph_dep
RUN pip install --upgrade pip
ARG CRYPTOGRAPHY_VERSION=""
RUN pip wheel --no-cache-dir --wheel-dir /DIST --prefer-binary cryptography${CRYPTOGRAPHY_VERSION}

################################################################################################################

################################################################################################################
################################################################################################################
##### Create final stage for image that has all required dependencies for lib and service packages prepared in
##### its /DIST/ directory.
FROM foundation

# Copy what we built so far in those other (hopefully cached) stages
COPY --from=build_pandas_dep /DIST/* /DIST/
COPY --from=build_numpy_dep /DIST/* /DIST/
#COPY --from=build_geopandas_dep /DIST/* /DIST/
COPY --from=build_cryptograph_dep /DIST/* /DIST/

# Copy main project requirements file, which should have everything (else, see previous line) needed to build any
# package within project
COPY ./requirements.txt /nwm_service/requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /DIST --prefer-binary -r /nwm_service/requirements.txt