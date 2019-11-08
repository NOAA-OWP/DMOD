#!/usr/bin/env bash

NAME=$(basename "${0}")

LINTER_CMD='flake8'
AUTOPEP_CMD='autopep8'

DEFAULT_MAX_LINE_LENGTH=120

usage()
{
    local _O="Usage:
    ${NAME} -h|--help
    ${NAME} [options...] <action>
Options:
    --path <path>
        Path to file or directory of interest for action

    --diff
        For 'fix' action, show a diff rather than actually making changes

    --extra-aggressive | -aa
        For 'fix' action, be extra aggressive in changes

    --max-line-length <number>
        Set the max line length (default for this script is ${DEFAULT_MAX_LINE_LENGTH})
Actions:
    fix     Make automatic style corrections
    check   Execute the linter (currently ${LINTER_CMD})
"

    echo "${_O}" 2>&1
}

run_linter()
{
    ${LINTER_CMD} \
        --max-line-length=${MAX_LINE_LENGTH:-${DEFAULT_MAX_LINE_LENGTH}} \
        --count \
        "${CHECK_PATH:-}"
}

run_autofix()
{
    ${AUTOPEP_CMD} \
        -r \
        ${FIX_CHANGE_METHOD:---in-place}  \
        ${AGGRESSIVENESS--a} \
        --max-line-length ${MAX_LINE_LENGTH:-${DEFAULT_MAX_LINE_LENGTH}} \
        "${LIST_FIXES:-}" \
        "${CHECK_PATH:-.}"
}

while [[ ${#} -gt 0 ]]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --direct)
            [[ -n "${IS_DIRECT:-}" ]] && usage && exit 1
            IS_DIRECT='true'
            ;;
        --path)
            [[ -n "${CHECK_PATH:-}" ]] && usage && exit 1
            [[ -n "${IS_DIRECT:-}" ]] && usage && exit 1
            CHECK_PATH="${2}"
            [[ ! -e "${CHECK_PATH}" ]] && echo "Error: check path ${CHECK_PATH} does not exist" && usage && exit 1
            shift
            ;;
        --max-line-length)
            [[ -n "${MAX_LINE_LENGTH:-}" ]] && usage && exit 1
            [[ -n "${IS_DIRECT:-}" ]] && usage && exit 1
            MAX_LINE_LENGTH="${2}"
            re='^[0-9]+$'
            if ! [[ $MAX_LINE_LENGTH =~ $re ]]; then
                usage
                exit 1
            fi
            shift
            ;;
        --diff)
            [[ -n "${FIX_CHANGE_METHOD:-}" ]] && usage && exit 1
            [[ -n "${IS_DIRECT:-}" ]] && usage && exit 1
            FIX_CHANGE_METHOD="--diff"
            ;;
        --extra-aggressive|-aa)
            # This echos if val is set non-null or val not declared
            if  [[ -n "${AGGRESSIVENESS-blah}" ]]; then
                [[ -n "${AGGRESSIVENESS:-}" ]] && usage && exit 1
            fi
            [[ -n "${IS_DIRECT:-}" ]] && usage && exit 1
            AGGRESSIVENESS="-aa"
            ;;
        fix|autopep8)
            ! command -v  ${AUTOPEP_CMD} > /dev/null && echo "Error: cannot find command ${AUTOPEP_CMD} in environment path" && exit 1
            if [[ "${IS_DIRECT:-}" == 'true' ]]; then
                shift
                ${AUTOPEP_CMD} "${@}"
                exit $?
            else
                [[ -n "${ACTION:-}" ]] && usage && exit 1
                ACTION="run_autofix"
            fi
            ;;
        check|linter|flake8)
            ! command -v ${LINTER_CMD} > /dev/null && echo "Error: cannot find command ${LINTER_CMD} in environment path" && exit 1
            if [[ "${IS_DIRECT:-}" == 'true' ]]; then
                shift
                ${LINTER_CMD} "${@}"
                exit $?
            else
                [[ -n "${ACTION:-}" ]] && usage && exit 1
                ACTION="run_linter"
            fi
            ;;
        *)
            usage
            exit 1
    esac
    shift
done

[[ -z "${ACTION:-}" ]] && usage && exit

${ACTION}
