#!/usr/bin/env sh

NAME="`basename ${0}`"

usage()
{
    local _O="Usage:
    ${NAME} -h|-help|--help
    ${NAME} [-d|--base_dir <dir_path>] build|clean
    ${NAME} [-d|--base_dir <dir_path>] -venv <virtual_env_dir> upgrade
"
    echo "${_O}" 2>&1
}

get_egg_info_dir()
{
    if [ -z "${EGG_DIR:-}" ]; then
        _EGG_DIR_BASE=`ls "${BASE_DIR}" | grep -e '.*\.egg-info$'`
        if [ -n "${_EGG_DIR_BASE:-}" ]; then
            EGG_DIR="${BASE_DIR:?}/${_EGG_DIR_BASE}"
        fi
    fi
}

build()
{
    python setup.py sdist bdist_wheel
}

clean_all()
{
    python setup.py clean --all 2>/dev/null
    [ -d ${BASE_DIR:?}/build ] && echo "Removing ${BASE_DIR}/build" && rm -r ${BASE_DIR}/build
    [ -d ${BASE_DIR:?}/dist ] && echo "Removing ${BASE_DIR}/dist" && rm -r ${BASE_DIR}/dist

    get_egg_info_dir
    #echo "EGG dir is ${EGG_DIR:-<not set>}"
    [ -n "${EGG_DIR:-}" ] && [ -d ${EGG_DIR:?} ] && echo "Removing ${EGG_DIR}" && rm -r "${EGG_DIR}"
}

build_and_upgrade()
{
    clean_all
    build
    pip install --upgrade --force-reinstall --find-links=${BASE_DIR}/dist ${PACKAGE_NAME:-nwmaas-communication}
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        -d|--base_dir)
            [ -n "${BASE_DIR:-}" ] && usge && exit 1
            BASE_DIR="${2}"
            shift
            ;;
        -venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            VENV_DIR="`cd ${2} && pwd`"
            shift
            ;;
        build|clean|upgrade)
            [ -n "${ACTION:-}" ] && usge && exit 1
            ACTION="${1}"
            ;;
        *)
            usage
            exit 1
            ;;
   esac
   shift
done

[ -z "${BASE_DIR:-}" ] && BASE_DIR="$(cd "$(dirname "${0}")"; pwd)"
MANUALLY_ACTIVATED=0

[ ! -d "${BASE_DIR:?}" ] && echo "Error: base dir ${BASE_DIR} does not exist" 1>&2 && usage && exit 1
if [ "${ACTION}" == "upgrade" ]; then
    [ -z "${VENV_DIR:-}" ] && echo "Error: no virtual env directory given for upgrading package" && exit 1
    [ ! -d "${VENV_DIR:-}" ] && echo "Error: given virtual env directory path is not an existing directory" && exit 1
    [ ! -e "${VENV_DIR}/bin/activate" ] && echo "Error: given virtual env directory does not appear to be valid venv" && exit 1
    #
    if [ -z "${VIRTUAL_ENV}" ]; then
        MANUALLY_ACTIVATED=1
        ${VENV_DIR}/bin/activate
    elif [ "${VIRTUAL_ENV:-x}" == "${VENV_DIR:-}" ]; then
        MANUALLY_ACTIVATED=0
    else
        echo "Error: given virtual env directory '${VENV_DIR}' does not match already sourced venv '${VIRTUAL_ENV}'"
        exit 1
    fi
fi

CURRENT_DIR=`pwd`

cd "${BASE_DIR:?}"
if [ "${ACTION}" == "build" ]; then
    build
elif [ "${ACTION}" == "clean" ]; then
    clean_all
elif [ "${ACTION}" == "upgrade" ]; then
    build_and_upgrade
    [ ${MANUALLY_ACTIVATED} -ne 0 ] && deactivate
else
    cd "${CURRENT_DIR:?}"
    echo "Error: unknown action '${ACTION}'"
    exit 1
fi
cd "${CURRENT_DIR:?}"

