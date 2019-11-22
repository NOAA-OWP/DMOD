#!/bin/bash

NAME=$(basename "${0}")
BASE_DIR=$(dirname "${0}")
HOST=''
EMAIL=''
KEY_FILE="${BASE_DIR}/privkey.pem"
CERT_FILE="${BASE_DIR}/certificate.pem"

usage()
{
    echo "Usage:
    ${NAME} [-host <host>] -email <email>

    Defaults to host value from $(which hostname) command if not specified.
    Files are written to same directory as script."
}

while [[ ${#} -gt 0 ]]; do
    case "$1" in
        -h|-help|--help)
            usage
            exit
            ;;
        -host)
            [[ -n "${HOST}" ]] && usage && exit 1
            HOST="${2}"
            shift
            ;;
        -email)
            [[ -n "${EMAIL}" ]] && usage && exit 1
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

[[ -z "${HOST}" ]] && HOST=$(hostname)
[[ -z "${EMAIL}" ]] && usage && exit 1

SUBJ="/C=US/ST=Alabama/L=Tuscaloosa/O=OWP/OU=APD/CN=${HOST}/emailAddress=${EMAIL}"
openssl req -newkey rsa:2048 -nodes -keyout "${KEY_FILE}" -x509 -days 36500 -out "${CERT_FILE}" -subj "${SUBJ}"
