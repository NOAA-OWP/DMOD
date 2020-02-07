#!/usr/bin/env bash

# A basic script that serves as a git-secrets secrets provider for the project, just echoing secret patterns

# Redis config file
echo 'requirepass\s+[A-Za-z0-9][^\s]*\s*$'
# In particular, for when initializing a Redis Python client object, but easily could apply to other situations
echo 'password\s*=\s*"[^"]+"'
echo "password\s*=\s*'[^']+'"