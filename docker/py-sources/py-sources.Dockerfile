ARG REQUIRE="gcc g++ musl-dev gdal-dev libffi-dev openssl-dev rust cargo git proj proj-dev proj-util openblas openblas-dev lapack lapack-dev"
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
# Needed for sourced functions used by build scripts in later stages
RUN mkdir -p /dmod/scripts/shared
COPY ./scripts/dist_package.sh /dmod/scripts
COPY ./scripts/shared /dmod/scripts/shared
# Copy python sources
COPY ./python /dmod/python
# Move to source dir
WORKDIR ./dmod

################################################################################################################

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building wheel distributions for lib packages
FROM basis as lib_packages
ARG comms_package_name
ARG access_package_name
ARG externalrequests_package_name
ARG scheduler_package_name
# Set this so script below will not run logic that only applies to when in a full Git repo directory tree
ENV OUT_OF_GIT_REPO=true
RUN for p in `ls python/lib`; do \
        [ -e python/lib/${p}/setup.py ] && ./scripts/dist_package.sh --sys python/lib/${p} && mv python/lib/${p}/dist/*.whl /DIST/.; \
    done
################################################################################################################

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building wheel distributions for service packages
FROM basis as service_packages
ARG request_service_package_name
ARG scheduler_service_package_dist_name
# Set these expressly in the environment, since probably not sourced from env (not sure if still needed)
ENV PYTHON_PACKAGE_DIST_NAME_REQUEST_SERVICE=${request_service_package_name}
ENV PYTHON_PACKAGE_DIST_NAME_SCHEDULER_SERVICE=${scheduler_service_package_dist_name}
# Set this so script below will not run logic that only applies to when in a full Git repo directory tree
ENV OUT_OF_GIT_REPO=true
# Build service dist packages
RUN for p in `ls python/services`; do \
        [ -e python/services/${p}/setup.py ] && ./scripts/dist_package.sh --sys python/services/${p} && mv python/services/${p}/dist/*.whl /DIST/. ; \
    done
################################################################################################################

################################################################################################################
################################################################################################################
#### Create final Docker build stage for desired image
FROM python:3.8-alpine3.15
WORKDIR /dmod
RUN apk update && apk upgrade && apk add --no-cache git
# Copy complete python source packages to location
COPY --from=basis /dmod /dmod
# And for every built dist/wheel package copy wheel file into analogous location for this stage
COPY --from=lib_packages /DIST/* /DIST/
COPY --from=lib_packages /CACHE/* /CACHE/
COPY --from=service_packages /DIST/* /DIST/
COPY --from=service_packages /CACHE/* /CACHE/
################################################################################################################
