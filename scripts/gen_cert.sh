#!/bin/bash

NAME=$(basename "${0}")
BASE_DIR=$(dirname "${0}")
HOST=''
EMAIL=''

usage()
{
    echo "Usage:
    ${NAME} [-d|--directory <output_dir>] [-o] [-host <host>] -email <email>

    Defaults to host value from $(which hostname) command if not specified.
    Files are written to same directory as script."
}

while [[ ${#} -gt 0 ]]; do
    case "$1" in
        -h|-help|--help)
            usage
            exit
            ;;
        -d|--directory)
            [[ -n "${OUTPUT_DIR:-}" ]] && usage && exit 1
            OUTPUT_DIR="${2}"
            shift
            ;;
        -o)
            [[ -n "${OVERWRITE:-}" ]] && usage && exit 1
            OVERWRITE='true'
            ;;
        -host)
            [[ -n "${HOST:-}" ]] && usage && exit 1
            HOST="${2}"
            shift
            ;;
        -email)
            [[ -n "${EMAIL:-}" ]] && usage && exit 1
            EMAIL="${2}"
            shift
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

KEY_FILE="${OUTPUT_DIR:=${BASE_DIR}}/privkey.pem"
CERT_FILE="${OUTPUT_DIR}/certificate.pem"

EXIST_COUNT=0
if [[ -e ${KEY_FILE} ]]; then
    EXIST_COUNT=$((EXIST_COUNT+1))
    echo "WARN: key output file ${KEY_FILE} already exists"
fi

if [[ -e ${KEY_FILE} ]]; then
    EXIST_COUNT=$((EXIST_COUNT+1))
    echo "WARN: key output file ${KEY_FILE} already exists"
fi

if [[ ${EXIST_COUNT} -gt 0 ]] && [[ -z "${OVERWRITE:-}" ]]; then
    echo "ERROR: exiting due to output files that already exist; use '-o' if wanting to overwrite files"
    exit 1
fi

[[ -z "${HOST:-}" ]] && HOST=$(hostname)
[[ -z "${EMAIL:-}" ]] && usage && exit 1

SUBJ="/C=US/ST=Alabama/L=Tuscaloosa/O=OWP/OU=APD/CN=${HOST}/emailAddress=${EMAIL}"
openssl req -newkey rsa:2048 -nodes -keyout "${KEY_FILE}" -x509 -days 36500 -out "${CERT_FILE}" -subj "${SUBJ}"
