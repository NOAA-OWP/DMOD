import git

from pathlib import Path
from typing import Optional


def find_git_root_dir(path: Optional[Path] = None) -> Path:
    """
    Given a path (with ``None`` implying the current directory) assumed to be in a Git repo, find repo's root.

    Parameters
    ----------
    path : Path
        A file path within the project directory structure, or ``None`` to imply use the current directory.

    Returns
    -------
    Path
        The root directory for the Git repo containing the given/current path.

    Raises
    -------
    InvalidGitRepositoryError : If the given path is not within a Git repo.
    NoSuchPathError : If the given path is not valid.
    BadObject : If the given revision of the obtained ::class:`git.Repo` could not be found.
    ValueError : If the rev of the obtained ::class:`git.Repo` couldn't be parsed
    IndexError: If an invalid reflog index is specified.
    """
    if path is None:
        path = Path('.')
    git_repo = git.Repo(path, search_parent_directories=True)
    return Path(git_repo.git.rev_parse("--show-toplevel"))