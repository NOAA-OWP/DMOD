#!/usr/bin/env bash

# A basic script that serves as a git-secrets secrets provider for the project, just echoing secret patterns

# Redis config file
echo "requirepass\s+[\"'A-Za-z0-9][^$][^\s]*\s*$"
# For setting any variable or named parameter ending in a substring like 'password' (i.e., any of the substrings that
# become 'password' when converted to lowercase).
# In particular, for when initializing a Redis Python client object.
echo "[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*=\s*('[^']+'|\"[^\"$]+\")"
