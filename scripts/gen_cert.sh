#!/bin/bash

NAME=$(basename "${0}")
BASE_DIR=$(dirname "${0}")
HOST=''
EMAIL=''
EXIST_COUNT=0

usage()
{
    echo "Usage:
    ${NAME} [-d|--directory <cert_dir>] [-o|-check] [-host <host>] [-email <email>]

    The default directory for cert files will be the parent directory of
    this script when not specified via command line argument.

    Hostname and email address for a generated or checked cert may be
    given via command line or in 'HOST' and/or 'EMAIL' variables defined
    in an '.ssl_env' file in the output directory.  Command line args
    take priority.  Additionally, script will fall back to using the
    output of the $(which hostname) command as the cert host value, but
    an email address must be provided to generate the cert.

    The '-check' option may be used to check whether any existing cert
    are valid for expected host and/or email address values. No cert is
    generated and no files written when this is specified.  The script
    will exit with a valid return code either if all provided values
    (e.g., host) match the existing cert or there is no existing cert
    file.

    The '-o' value can specify that any existing cert files may be
    overwritten.  Otherwise, the script exits with error.  Note that
    regardless, an individual warning message is printed for each
    existing script file.

    "
}

check_cert_files_exist()
{
    if [[ -e ${CERT_FILE} ]]; then
        EXIST_COUNT=$((EXIST_COUNT+1))
        echo "WARN: cert output file ${CERT_FILE} already exists"
    fi

    if [[ -e ${KEY_FILE} ]]; then
        EXIST_COUNT=$((EXIST_COUNT+1))
        echo "WARN: key output file ${KEY_FILE} already exists"
    fi

    if [[ ${EXIST_COUNT} -gt 0 ]] && [[ -z "${OVERWRITE:-}" ]]; then
        echo "ERROR: exiting due to output files that already exist; use '-o' if wanting to overwrite files"
        exit 1
    fi
}

parse_cert_subject()
{
    local _SUB="$(openssl x509 -noout -subject -in "${CERT_FILE}")"

    echo "${_SUB}" | sed "s|.*/${1}=\([^/]*\).*|\1|" 2>/dev/null
}

check_existing_cert_valid()
{
    local _IS_BAD=0

    if [[ ! -f "${CERT_FILE}" ]]; then
        echo "No cert file '${CERT_FILE}' exists; exiting successfully after no invalid cert was found."
        exit 0
    fi

    # We will always have a 'host' value, even if just the value from the hostname command
    local _CERT_HOST="$(parse_cert_subject CN)"
    if [[ "${_CERT_HOST}" != "${HOST}" ]]; then
        echo "ERROR: invalid cert host '${_CERT_HOST}' (expected '${HOST}')"
        _IS_BAD=$((_IS_BAD+1))
    fi

    # However, we may not always get an EMAIL value, so only check if necessary
    if [[ -n "${EMAIL}" ]]; then
        local _CERT_EMAIL="$(parse_cert_subject emailAddress)"

        if [[ "${_CERT_EMAIL}" != "${EMAIL}" ]]; then
            echo "ERROR: invalid cert email '${_CERT_EMAIL}' (expected '${EMAIL}')"
            _IS_BAD=$((_IS_BAD+2))
        fi
    fi

    # Also make sure cert hasn't expired
    openssl x509 -noout -checkend 0 -in "${CERT_FILE}" 2>/dev/null
    if [[ ${?} -ne 0 ]]; then
        echo "ERROR: cert appears to have expired"
        _IS_BAD=$((_IS_BAD+4))
    fi

    [[ ${_IS_BAD} -eq 0 ]] && echo "SUCCESS: cert appears valid"

    exit ${_IS_BAD}
}

generate_cert()
{
    # Check whether either file exists, and whether we need to bail because of that
    check_cert_files_exist

    # Finally, generate and write the certificate files
    local _SUBJ="/C=US/ST=Alabama/L=Tuscaloosa/O=OWP/OU=APD/CN=${HOST}/emailAddress=${EMAIL}"
    openssl req -newkey rsa:2048 -nodes -keyout "${KEY_FILE}" -x509 -days 36500 -out "${CERT_FILE}" -subj "${_SUBJ}"
}

while [[ ${#} -gt 0 ]]; do
    case "$1" in
        -h|-help|--help)
            usage
            exit
            ;;
        -check)
            [[ -n "${DO_CHECK:-}" ]] && usage && exit 1
            [[ -n "${OVERWRITE:-}" ]] && usage && exit 1
            DO_CHECK='true'
            ;;
        -d|--directory)
            [[ -n "${OUTPUT_DIR:-}" ]] && usage && exit 1
            OUTPUT_DIR="${2}"
            shift
            ;;
        -o)
            [[ -n "${OVERWRITE:-}" ]] && usage && exit 1
            [[ -n "${DO_CHECK:-}" ]] && usage && exit 1
            OVERWRITE='true'
            ;;
        -host)
            # Store command line values in separate var so not lost when sourcing a config file
            [[ -n "${HOST_CLI:-}" ]] && usage && exit 1
            HOST_CLI="${2}"
            shift
            ;;
        -email)
            # Store command line values in separate var so not lost when sourcing a config file
            [[ -n "${EMAIL_CLI:-}" ]] && usage && exit 1
            EMAIL_CLI="${2}"
            shift
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

# Read in the .ssl_env, if it exists (also, set the output dir to the default of the script's base dir when necessary)
CONFIG_FILE="${OUTPUT_DIR:=${BASE_DIR}}/.ssl_env"
[[ -f "${CONFIG_FILE}" ]] && source "${CONFIG_FILE}"

# Set the generated file names
KEY_FILE="${OUTPUT_DIR}/privkey.pem"
CERT_FILE="${OUTPUT_DIR}/certificate.pem"

# Overwrite/set values provided via CLI (stored separately so they don't get overwritten when sourcing external config)
[[ -n "${HOST_CLI:-}" ]] && HOST="${HOST_CLI:-}"
[[ -n "${EMAIL_CLI:-}" ]] && EMAIL="${EMAIL_CLI:-}"

# Sanity check required values are provided or we get defaults
[[ -z "${HOST:-}" ]] && HOST=$(hostname)

# Although don't bother with email if we are only checking
if [[ -n "${DO_CHECK:-}" ]]; then
    check_existing_cert_valid
    exit
fi

[[ -z "${EMAIL:-}" ]] && usage && exit 1

generate_cert
