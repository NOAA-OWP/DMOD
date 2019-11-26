#!/usr/bin/env sh

NAME="`basename ${0}`"

usage()
{
    local _O="Usage:
    ${NAME} -h|-help|--help
    ${NAME} [-d|--base_dir <dir_path>] build|clean
"
    echo "${_O}" 2>&1
}

get_egg_info_dir()
{
    if [ -z "${EGG_DIR:-}" ]; then
        EGG_DIR="${BASE_DIR:?}/$(ls ${BASE_DIR:?} | grep -e '.*\.egg-info$')"
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

    [ -d ${EGG_DIR:?} ] && echo "Removing ${EGG_DIR}" && rm -r "${EGG_DIR}"
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
        build|clean)
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
[ ! -d "${BASE_DIR:?}" ] && echo "Error: base dir ${BASE_DIR} does not exist" 1>&2 && usage && exit

if [ "${ACTION}" == "build" ]; then
    build
elif [ "${ACTION}" == "clean" ]; then
    clean_all
else
    echo "Error: unknown action '${ACTION}'"
    exit 1
fi
