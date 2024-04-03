# About
Python package for data management service for DMOD infrastructure.

# Structure
Structure has been modified from original to have inner duplicate directory in order to comply with general Python packaging structure.
This facilitates executing tests in a variety of different scenarios, including running integration tests on a local machine using the included test script and/or running unit tests directly within an IDE.

## Configuration

Provide listed service configuration variables as either environment variables, in a '.env' file, as a `secret` in `/run/secrets`, or as a mixture of the aforementioned options.

Configuration option names are case insensitive.

boolean values are case insensitive.
valid values are:
    `0`, `off`, `f`, `false`, `n`, `no`, `1`, `on`, `t`, `true`, `y`, `yes`

A `.env` file must be utf-8 encoded and follow syntax rules:
- lines beginning with `#` are treated as comments
- blank lines are ignored
- each line represents a key-value pair. values can optionally be quoted.
  for example:
      ```
      PORT=8080
      PORT='8080'
      PORT="8080"
      ```
For more in-depth information, see these resources:
- https://docs.docker.com/compose/environment-variables/env-file/#syntax
- https://github.com/theskumar/python-dotenv?tab=readme-ov-file#file-format

A secret's filename must match the name of a configuration variable (case insensitive).
The value of the secret are the contents of the file.

Configuration Source Priority:
1. environment variables
2. variables loaded from a dotenv (`.env`) file.
3. variables loaded from the secrets directory.
4. default field values

Configuration Variable:

`S3FS_URL_PROTOCOL`: string (default='http')
`S3FS_URL_HOST`: string (optional)
`S3FS_URL_PORT`: integer (default=9000)
`S3FS_VOL_IMAGE_NAME`: string (default='127.0.0.1:5000/s3fs-volume-helper')
`S3FS_VOL_IMAGE_TAG`: string (default='latest')
`S3FS_PLUGIN_ALIAS`: string (default='s3fs')
`S3FS_HELPER_NETWORK`: string (default='host')
`HOST`: string (default='Lynkers-MacBook-Pro-2.local')
	Set the appropriate listening host name or address value (NOTE: must match SSL cert)
`PORT`: integer (default=3012)
	Set the appropriate listening port value
`CERT_PATH`: string (optional)
	Specify path for a particular SSL certificate file to use
`KEY_PATH`: string (optional)
	Specify path for a particular SSL private key file to use
`SSL_DIR`: string (optional)
	Change the base directory when using SSL certificate and key files with default names
`OBJECT_STORE_HOST`: string (default='minio-proxy')
	Set hostname for connection to object store
`OBJECT_STORE_PORT`: integer (default=9000)
	Set port for connection to object store
`OBJECT_STORE_EXEC_USER_NAME`: string (required)
    Object store user access key
`OBJECT_STORE_EXEC_USER_PASSWD`: string (required)
    Object store user secret key
`REDIS_HOST`: string (default='myredis')
	Set the host value for making Redis connections
`REDIS_PORT`: integer (default=6379)
	Set the port value for making Redis connections
`REDIS_PASS`: string (default='noaaOwp')
	Set the password value for making Redis connections
`PYCHARM_DEBUG`: boolean (default=False)
	Activate Pycharm remote debugging support
