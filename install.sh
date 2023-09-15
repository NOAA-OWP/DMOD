#!/usr/bin/env bash

deactivate;

ACTIVATE_FILE='venv/bin/activate';

if [ -f "$ACTIVATE_FILE" ];
then
    echo
    echo "Virtual Environment found. Attempting to activate it."
    echo
    . venv/bin/activate;
else
    echo
    echo "Virtual Environment not found. Attempting to create it"
    echo
    python -m venv venv
    echo
    echo "Activating Virtual Environment"
    echo
    . venv/bin/activate;
fi

ACTIVATED=$?;

if [ $ACTIVATED != 0 ]; then
    echo
    echo "Could not activate a python virtual environment" >&2;
    echo
    exit $ACTIVATED;
fi

echo
echo "Attempting to install DMOD requirements"
echo
pip install -r requirements.txt

REQUIREMENTS_INSTALLED=$?

if [ $REQUIREMENTS_INSTALLED != 0 ]; then
    echo
    echo "DMOD Requirements could not be installed." >&2
    echo
    exit $REQUIREMENTS_INSTALLED
fi

echo
echo "Attempting to update DMOD packages..."
echo
./scripts/update_package.sh

PACKAGES_UPDATED=$?;

if [ $PACKAGES_UPDATED != 0 ]; then
    echo
    echo "DMOD Packages could not be updated." >&2;
    echo
else
    echo
    echo "DMOD has been installed and is ready to go"
    echo
fi

exit $PACKAGES_UPDATED
