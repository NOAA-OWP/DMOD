ARG REQUIRE="gcc g++ musl-dev gdal-dev libffi-dev openssl-dev rust cargo git proj proj-dev proj-util openblas openblas-dev lapack lapack-dev geos-dev"
################################################################################################################
################################################################################################################
##### Create foundational level build stage with initial structure
FROM python:3.8-alpine3.15 as foundation
ARG REQUIRE

RUN apk update && apk upgrade && apk add --no-cache ${REQUIRE}
# Along with setup and wheel to build, install all project pip dependencies for package building later
RUN mkdir /DIST && mkdir /dmod && pip install --upgrade pip
RUN for d in numpy pandas crypt scikit-learn; do for b in DIST; do mkdir -p /${b}/${d}; done; done

################################################################################################################
################################################################################################################
##### Create individual, semi-independent stages for building some of the longer-to-build packages to isolate
##### them in the cache.  This has the additional benefit of parallelizing these build steps.
FROM foundation as build_numpy_dep
RUN pip install --upgrade pip
ARG NUMPY_VERSION=">=1.18.0"
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary numpy${NUMPY_VERSION}

############################################################
FROM foundation as build_cryptograph_dep
RUN pip install --upgrade pip
ARG CRYPTOGRAPHY_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary cryptography${CRYPTOGRAPHY_VERSION}

############################################################
FROM foundation as build_shapely_dep
RUN pip install --upgrade pip
ARG SHAPELY_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary shapely${SHAPELY_VERSION}

############################################################
# This one also requires numpy
FROM build_numpy_dep as build_pandas_dep
RUN pip install --upgrade pip
ARG PANDAS_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary pandas${PANDAS_VERSION}

############################################################
# This one requires numpy as well
FROM build_numpy_dep as build_sklearn_dep
RUN pip install --upgrade pip
ARG SKLEARN_VERSION=""
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary scikit-learn${SKLEARN_VERSION}

################################################################################################################

################################################################################################################
################################################################################################################
##### Create base intermediate build stage that has all required dependencies for lib and service packages prepared
###### in its /DIST/ directory.
FROM foundation as basis
ARG REQUIRE

# Copy what we built so far in those other (hopefully cached) stages
COPY --from=build_pandas_dep /DIST/ /DIST/
COPY --from=build_pandas_dep /CACHE/ /CACHE/

COPY --from=build_cryptograph_dep /DIST/ /DIST/
COPY --from=build_cryptograph_dep /CACHE/ /CACHE/

COPY --from=build_shapely_dep /DIST/ /DIST/
COPY --from=build_shapely_dep /CACHE/ /CACHE/

COPY --from=build_sklearn_dep /DIST/ /DIST/
COPY --from=build_sklearn_dep /CACHE/ /CACHE/

#RUN mv /DIST/pandas/* /DIST/. && mv /DIST/crypt/* /DIST/. && mv /DIST/sklearn/* /DIST/. \
#    && apk update && apk upgrade && apk add --no-cache ${REQUIRE} \

RUN apk update && apk upgrade && apk add --no-cache ${REQUIRE} \
    && if [ ! -d /CACHE ]; then mkdir /CACHE; fi \
    && pip install --upgrade pip \
    && pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary setuptools wheel geopandas

# Copy project requirements file, which should have everything needed to build any package within project
COPY ./requirements.txt /dmod/requirements.txt
# Along with setup and wheel to build, install any remaining (see above) project pip dependencies for package building later
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary -r /dmod/requirements.txt


################################################################################################################