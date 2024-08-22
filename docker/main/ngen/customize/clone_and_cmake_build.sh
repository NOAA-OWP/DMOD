#!/usr/bin/env bash

REPO_URL="${1:?No repo URL provided}"

if [ -e "./repo_dir" ]; then
    rm --preserve-root -rf "./repo_dir"
fi

# Clone the repo, but only the primary branch
git clone --single-branch ${REPO_URL} repo_dir
cd repo_dir || exit 1

# Generate a CMake build system and build
cmake -B ./cmake_build -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE:-Release} -DCMAKE_INSTALL_PREFIX:PATH=/dmod -S .
cmake --build ./cmake_build

# Move libraries within the /dmod/ directory so they'll be copied into later image build stage
mkdir -p /dmod/lib64
mkdir -p /dmod/shared_libs
cp -a ./cmake_build/*.so* /dmod/lib64/.
cp -a ./cmake_build/*.so* /dmod/shared_libs/.
