#!/bin/bash

set -e

# A virtual environment path may be supplied using this environmental shell variable
if [[ -n "${VENV_DIR:-}" ]]; then
    # Initialize if virtual environment directory either doesn't exists, or exists but is empty ...
    if [[ ! -d "${VENV_DIR}" ]] || [[ $(find "${VENV_DIR}" -maxdepth 0 -empty 2>/dev/null | wc -l) -eq 1 ]]; then
        python -m venv "${VENV_DIR}"
    fi
    source "${VENV_DIR}/bin/activate"
    pip install --update -r /usr/maas_portal/requirements.txt
fi

set +e

# Execute the migration scripts on the designated database
python manage.py migrate

# Collect all static Django resources into one place where nginx can access them
python manage.py collectstatic --no-input

# Run the commands passed in from elsewhere
exec "$@"
