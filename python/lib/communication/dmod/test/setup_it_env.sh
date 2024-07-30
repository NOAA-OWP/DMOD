#!/usr/bin/env sh

CERT_SCRIPT="${PROJECT_ROOT}/scripts/gen_cert.sh"

check_test_cert()
{
    # TODO: this may be technically incorrect and need to be generalized or configurable somehow
    _CERT_DIR="${PROJECT_ROOT:?}/ssl/local"

    # Check the cert is valid as expected and not expired, regenerating if necessary
    ${CERT_SCRIPT} -d ${_CERT_DIR} -check
    if [ ${?} -ne 0 ]; then
        # Try overwriting the cert, first without config args, hoping there is a config file in the directory
        ${CERT_SCRIPT} -d ${_CERT_DIR} -o
        if [ ${?} -ne 0 ]; then
            ${CERT_SCRIPT} -d ${_CERT_DIR} -o -email "$(whoami)@$(hostname)"
        fi
    # Also, if there was no cert file, write (but don't overwrite) new files
    elif [ ! -e "${_CERT_DIR}/certificate.pem" ]; then
        # Try write the cert, first without any config args, hoping there is a config file in the directory
        ${CERT_SCRIPT} -d ${_CERT_DIR}
        if [ ${?} -ne 0 ]; then
            ${CERT_SCRIPT} -d ${_CERT_DIR} -email "$(whoami)@$(hostname)"
        fi
    fi

}

do_setup()
{
    # Need to make sure cert exists where expected and is valid
    check_test_cert

}

do_teardown()
{
    # Nothing really needed for cert stuff
    echo "No teardown tasks"
}
