#!/usr/bin/env bash

INFO="Download 'git-secrets' and optionally install it and Git hooks using it
in this project, or just perform a specified subtask of said install."

# Note that this is "hooks/" and the "shared/" dir requires going up one more level
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/../shared"

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

EXECUTABLE_BASENAME="git-secrets"
MANFILE_BASENAME="git-secrets.1"
REMOTE_REPO_URL="https://github.com/awslabs/git-secrets.git"
SECRETS_PROVIDER_SCRIPT="$(dirname "${0}")/secrets_provider.sh"

USAGE_HEADER="${NAME:?}

${INFO:?}

USAGE:
    ${NAME:?} [opts] <repo_dir> [<install_dir>]
    ${NAME:?} [--clear|-c] --apply-provider
    ${NAME:?} --install-hooks
    ${NAME:?} -h|-help|--help
    ${NAME:?} --info"

usage()
{
    local _O="
${USAGE_HEADER:?}

OPTIONS:
    --clear|-c, --profile|-p <profile_config_file>, --remove-repo|-rm,
    --skip-hooks|-sh, --skip-path|-sp

See --info for more complete description.
"

    echo "${_O}" 2>&1
}

info()
{
    local _INFO_OUT="NAME:
    ${USAGE_HEADER:?}

When called with repo and (optional) install directories as args, script
downloads 'git-secrets' tool by locally cloning tool's Git repo to the
specified directory (unless a repo clone already exists there). Further,
if the optional arg for 'install_dir' is present, the script:

    - installs 'git-secrets' within 'install_dir' (and in PATH)
    - installs these hooks utilizing 'git-secrets' in .git/hooks/
        - commit-msg
        - pre-commit
        - prepare-commit-msg
    - applies a secrets provider to the repo's Git config for supplying
      the patterns for 'git-secrets' and utilizing hooks to warn about

When passed --apply-provider, only apply the custom secrets provider
script to the project's Git config (optionally clearing any previous).

When passed --install-hooks, only install the above mentioned hooks
to .git/hooks/.

See 'OPTIONS' for ways some of this behavior can be controlled.

ARGUMENTS:
    <repo_dir>
        A path to the directory for local copy of 'git-secrets'
        Git repository

    <install_dir>
        A path to a directory in which to install the relevant
        artifacts from git-secrets (e.g., the executable script),
        with these steps being skipped if this argument is not
        provided

    --apply-provider
        Just add the 'git-secrets' secret provider for project to
        local Git config (see 'git-secrets' for info on providers)

        This must be used on its own or with only the optional
        --clear flag.

    --install-hooks
        Just install the appriopriate hooks in .git/hooks/

OPTIONS:
    --clear|-c
        Optionally used with --apply-provider to indicate any
        existing secrets providers in the Git config should be
        cleared before applying this script's provider value

    --profile|-p <file>
        Set the path to the profile config file to append to in
        order to install 'git-secrets' in the user's PATH

    --remove-repo|-rm
        After installing the executable, remove the cloned repo

    --skip-hooks|-sh
        Skip installing/updating applicable hooks in repo to use
        git-secrets

    --skip-path|-sp
        Skip updating the user's PATH to have the executable

"
    echo "${_INFO_OUT}" | less
}

cleanup_repo()
{
    # Only do this deletion if both the flag is set and we have established at some point it is safe to do so
    if [ ${SAFE_REMOVE_REPO:-1} -eq 0 ] && [ -n "${DO_REMOVE_REPO:-}" ];  then
        rm -rf "${REPO_DIR}"
    fi
}

# Verify an explicity set PROFILE_CONFIG, or choose one otherwise.
# When choosing, func looks in HOME for existing and writeable .bash_profile, then .bashrc.
# If neither are suitable, and .bash_profile doesn't exist it will use .bash_profile (i.e., creating a new file).
# If all that fails, it forces an exit with error.
verify_bash_profile_config()
{
    # If profile config explicitly set, confirm the file exists and can be written to
    if [ -z "${PROFILE_CONFIG:-}" ]; then
        if [ ! -e "${PROFILE_CONFIG}" ] || [ ! -w "${PROFILE_CONFIG}" ]; then
            >&2 echo "Error: provide profile config '${PROFILE_CONFIG}' does not exist or is not writeable"
            exit 1
        fi
    # Otherwise, try to find a suitable profile config
    else
        for p in .bash_profile .bashrc; do
            if [ -e "${HOME}/${p}" ] && [ -w "${HOME}/${p}" ]; then
                PROFILE_CONFIG="${HOME}/${p}"
                break
            fi
        done
        # Default to .bash_profile, as long as one doesn't exist from above, which would imply it was non-writeable
        if [ -z "${PROFILE_CONFIG:-}" ] && [ ! -e "${HOME}/.bash_profile" ] ; then
            PROFILE_CONFIG="${HOME}/.bash_profile"
        else
            >&2 echo "Error: no suitable choice for profile config file was set or could be found"
        fi
    fi
}

# Clone the repo, unless it has already been clone to the set directory; exit with error if something else is there.
conditional_clone_repo()
{
    # Verify if path for repo already exists that it is actually the repo
    if [ -d "${REPO_DIR}" ]; then
        # This establishes it is a git repo
        if [ "$(cd ${REPO_DIR}; if git rev-parse --show-toplevel > /dev/null 2>&1; then echo 'true'; fi )" = 'true' ]; then
            # This confirms the expected files are present
            if [ -e "${REPO_DIR}/${EXECUTABLE_BASENAME}" ] && [ -e "${REPO_DIR}/${MANFILE_BASENAME}" ]; then
                >&2 echo "Warning: the Git repo for 'git-secrets' has already been cloned to ${REPO_DIR}"
                >&2 echo "Proceeding, assuming you've made sure the appropriate revision is checked out"
            else
                >&2 echo "Error: ${REPO_DIR} exists and is Git repo, but does not have expected files for git-secrets"
                exit 1
            fi
        else
            >&2 echo "Error: ${REPO_DIR} but is not a Git repository"
            exit 1
        fi
    # If path does not exist, clone repo to given path
    else
        git clone "${REMOTE_REPO_URL}" "${REPO_DIR}"
        # Also, only if the path didn't already exist are we safe to deleted it
        SAFE_REMOVE_REPO=0
    fi
}

install_hook()
{
    # 1 : hook
    # 2 : command option
    if [ ! -e "${PROJECT_ROOT:?}/.git/hooks/${1}" ]; then
        echo "#!/usr/bin/env bash" > "${PROJECT_ROOT:?}/.git/hooks/${1}"
        echo "git secrets --${2} -- \"\$@\"" >> "${PROJECT_ROOT:?}/.git/hooks/${1}"
    else
        >&2 echo "WARN: there is already an existing ${PROJECT_ROOT:?}/.git/hooks/${1} hook for the project."
        >&2 echo ""
        >&2 echo "To incorporate the usage of git-secrets into this hook, manaully add the following line to the file:"
        >&2 echo "    git secrets --${2} -- \"\$@\""
        return 1
    fi
}

install_all_hooks()
{
    # Make sure if this is changed that the info message gets updated
    install_hook "commit-msg" "commit_msg_hook"
    install_hook "pre-commit" "pre_commit_hook"
    install_hook "prepare-commit-msg" "prepare_commit_msg_hook"
}

# Add secrets provider (to the local git config)
apply_secrets_provider()
{
    if [ $(git config --get-all secrets.providers | wc -l) -gt 0 ] && [ "${DO_CLEAR_PROVIDERS:-}" = "true" ]; then
        >&2 echo "Clearing previously set git-secrets secrets providers:"
        >&2 git config --get-all secrets.providers | sed 's/^/    /'
        git config --unset-all secrets.providers
    fi

    git secrets --add-provider -- "${SECRETS_PROVIDER_SCRIPT}"
}

if [ ${#} -eq 0 ]; then
    usage
    exit
fi

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --info)
            info
            exit
            ;;
        --install-hooks)
            # When this runs, then only this runs
            [ -n "${PROFILE_CONFIG:-}" ] && usage && exit 1
            [ -n "${DO_REMOVE_REPO:-}" ] && usage && exit 1
            [ -n "${DO_SKIP_HOOKS:-}" ] && usage && exit 1
            [ -n "${DO_SKIP_PATH:-}" ] && usage && exit 1
            [ -n "${REPO_DIR:-}" ] && usage && exit 1
            [ -n "${INSTALL_DIR:-}" ] && usage && exit 1
            [ -n "${DO_CLEAR_PROVIDERS:-}" ] && usage && exit 1
            # Also, this has to be the last arg
            [ ${#} -gt 1 ] && usage && exit 1
            install_all_hooks
            exit $?
            ;;
        --apply-provider)
            # When this runs, then only this runs
            [ -n "${PROFILE_CONFIG:-}" ] && usage && exit 1
            [ -n "${DO_REMOVE_REPO:-}" ] && usage && exit 1
            [ -n "${DO_SKIP_HOOKS:-}" ] && usage && exit 1
            [ -n "${DO_SKIP_PATH:-}" ] && usage && exit 1
            [ -n "${REPO_DIR:-}" ] && usage && exit 1
            [ -n "${INSTALL_DIR:-}" ] && usage && exit 1
            # Also, this has to be the last arg
            [ ${#} -gt 1 ] && usage && exit 1
            apply_secrets_provider
            exit $?
            ;;
        --clear|-c)
            [ -n "${DO_CLEAR_PROVIDERS:-}" ] && usage && exit 1
            DO_CLEAR_PROVIDERS='true'
            ;;
        --profile|-p)
            [ -n "${PROFILE_CONFIG:-}" ] && usage && exit 1
            PROFILE_CONFIG="${2}"
            shift
            ;;
        --remove-repo|-rm)
            [ -n "${DO_REMOVE_REPO:-}" ] && usage && exit 1
            DO_REMOVE_REPO='true'
            ;;
        --skip-hooks|-sh)
            [ -n "${DO_SKIP_HOOKS:-}" ] && usage && exit 1
            DO_SKIP_HOOKS='true'
            ;;
        --skip-path|-sp)
            [ -n "${DO_SKIP_PATH:-}" ] && usage && exit 1
            DO_SKIP_PATH='true'
            ;;
        *)
            [ -n "${DO_CLEAR_PROVIDERS:-}" ] && usage && exit 1
            if [ -z "${REPO_DIR:-}" ]; then
                REPO_DIR="${1}"
            elif [ -z "${INSTALL_DIR:-}" ]; then
                INSTALL_DIR="${1}"
            else
                usage
                exit 1
            fi
            ;;
    esac
    shift
done

# Trap to make sure we "clean up" script activity before exiting
trap cleanup_repo 0 1 2 3 6 15

# Make sure a repo directory was set
if [ -z "${REPO_DIR:-}" ]; then
    usage
    exit 1
fi
# Also, make sure repo directory either doesn't exist or is a directory
if [ -e "${REPO_DIR}" ] && [ ! -d "${REPO_DIR}" ]; then
    >&2 echo "Error: non-directory file exists at provided path for repository directory"
    exit 1
fi
# Convert to an absolute path
REPO_DIR="$(cd "${REPO_DIR}"; pwd)"

# Also, go ahead and do something similar right here for INSTALL_DIR, if that was set
if [ -n "${INSTALL_DIR:-}" ] && [ -e "${INSTALL_DIR}" ] && [ ! -d "${INSTALL_DIR}" ]; then
    >&2 echo "Error: non-directory file exists at provided path for installation directory"
    exit 1
fi

# TODO: consider support for other shells
verify_bash_profile_config

conditional_clone_repo

if [ -n "${INSTALL_DIR:-}" ]; then
    # Verify install directory exists, or create it
    [ -d "${INSTALL_DIR}" ] || mkdir "${INSTALL_DIR}"
    # Make git-secrets/, git-secrets/bin/, git-secrets/man/, git-secrets/man/man1/ under <install_dir>
    [ -d "${INSTALL_DIR}/git-secrets" ] || mkdir "${INSTALL_DIR}/git-secrets"
    [ -d "${INSTALL_DIR}/git-secrets/bin" ] || mkdir "${INSTALL_DIR}/git-secrets/bin"
    [ -d "${INSTALL_DIR}/git-secrets/man" ] || mkdir "${INSTALL_DIR}/git-secrets/man"
    [ -d "${INSTALL_DIR}/git-secrets/man/man1" ] || mkdir "${INSTALL_DIR}/git-secrets/man/man1"

    # Copy script to bin/ and man file to man/man1
    cp "${REPO_DIR}/${EXECUTABLE_BASENAME}" "${INSTALL_DIR}/git-secrets/bin/${EXECUTABLE_BASENAME}"
    cp "${REPO_DIR}/${MANFILE_BASENAME}" "${INSTALL_DIR}/git-secrets/man/man1/${MANFILE_BASENAME}"

    # Update user path in profile file (unless set not to)
    if [ -z "${DO_SKIP_PATH:-}" ]; then
        echo "export PATH=\"\$PATH:${INSTALL_DIR}/git-secrets/bin\"}" >> "${PROFILE_CONFIG}"
        # Also update the PATH in the current shell
        export PATH="${PATH}:${INSTALL_DIR}/git-secrets/bin"
    fi

    # Install the actual hooks
    if [ -z "${DO_SKIP_HOOKS:-}" ]; then
        install_all_hooks
    fi
fi

apply_secrets_provider
