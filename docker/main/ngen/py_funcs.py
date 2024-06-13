#!/usr/bin/env python3

import argparse
import logging
import os
import shutil
import tarfile

from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from subprocess import Popen
from typing import Dict, List, Literal, Optional


def _apply_logging(log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]):
    logging.basicConfig(
        level=logging.getLevelName(log_level),
        format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def _parse_for_tar_and_copy(parent_subparsers_container):
    """ Run subparser for CLI command responsible for running `tar_and_copy` helper function. """
    # A parser for the 'tar_and_copy' param itself, underneath the parent 'command' subparsers container
    helper_cmd_parser = parent_subparsers_container.add_parser(
        'tar_and_copy', description="Archive contents of a directory and copy archive to specified destination.")
    helper_cmd_parser.add_argument('--dry-run', dest='do_dry_run', action='store_true',
                                   help='Perform a dry run to check paths, with no archiving/moving/copying.')
    helper_cmd_parser.add_argument('--compress', dest='do_compress', action='store_true',
                                   help='Compress the created archive with gzip compression.')
    helper_cmd_parser.add_argument('archive_name', help='Basename for the created archive file.')
    helper_cmd_parser.add_argument('source', type=Path, help='Directory whose contents should be archived.')
    helper_cmd_parser.add_argument('dest', type=Path, help='Destination directory in which to place the archive file.')


def _parse_for_gather_output(parent_subparsers_container):
    # A parser for the 'tar_and_copy' param itself, underneath the parent 'command' subparsers container
    desc = "Using subprocesses, gather output from remote MPI hosts and collect in analogous directory on this host."
    helper_cmd_parser = parent_subparsers_container.add_parser('gather_output', description=desc)
    # TODO: (later) when we move to all Python, rework this to accept several individually
    helper_cmd_parser.add_argument('mpi_hosts_str', help='Comma delimited MPI hosts string received by worker.')
    helper_cmd_parser.add_argument('output_write_dir', type=Path, help='Directory where output was written on hosts.')


def _subparse_move_to_directory(parent_subparser_container):
    sub_cmd_parser = parent_subparser_container.add_parser('to_directory', description="Move to a specified directory")
    sub_cmd_parser.add_argument("dest_dir", type=Path, help="Destination directory to which to move the output")


def _parse_for_move_job_output(parent_subparsers_container):
    # A parser for the 'tar_and_copy' param itself, underneath the parent 'command' subparsers container
    desc = "Move output data files produced by a job to another location, typically to put them into a DMOD dataset."
    helper_cmd_parser = parent_subparsers_container.add_parser('move_job_output', description=desc)
    helper_cmd_parser.add_argument('--job_id', '--job-id', dest='job_id', help='Optionally specify job id.')
    helper_cmd_parser.add_argument('--archive-files', dest='do_archiving', choices=["true", "false"],
                                   type=lambda s: True if s.lower == "true" else False, default=None,
                                   help='Force archiving before moving job output.')
    helper_cmd_parser.add_argument('output_directory', type=Path,
                                   help='Source directory containing output files to be placed within the dataset.')

    cmd_subparsers = helper_cmd_parser.add_subparsers(dest='move_action', help="Specify the type of move action.")
    cmd_subparsers.required = True
    _subparse_move_to_directory(cmd_subparsers)


def _parse_args() -> argparse.Namespace:
    """
    Set up and run top-level arg parsing for module.

    Returns
    -------
    argparse.Namespace
        The parsed arguments namespace object.
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='py_funcs',
                                     description="Run one of several Docker image entrypoint Python helper functions.")
    parser.add_argument('--log-level', '-L', dest='log_level',
                        default=os.environ.get("DEFAULT_LOG_LEVEL", "INFO").upper(),
                        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], help='Optionally specify log level.')

    subparsers = parser.add_subparsers(dest='command', help='Specify the Python helper function command to run.')
    subparsers.required = True

    _parse_for_tar_and_copy(parent_subparsers_container=subparsers)
    _parse_for_gather_output(parent_subparsers_container=subparsers)
    _parse_for_move_job_output(parent_subparsers_container=subparsers)

    return parser.parse_args()


def _move_to_directory(source_dir: Path, dest_dir: Path, archive_name: Optional[str] = None):
    """
    Move source data files from their initial directory to a different directory, potentially combining into an archive.

    Parameters
    ----------
    source_dir
        The source directory containing output files to be placed within the dataset; note that this has already been
        tested for existence as a directory.
    dest_dir
        The destination directory, to which the output data should be moved; note that this path has not yet been tested
        for existence as a directory.
    archive_name
        When files should be archived as part of moving, the name of the archive; when files should not be archived,
        ``None``.
    """
    if not dest_dir.is_dir():
        raise ValueError(f"{get_date_str()} Can't move job output to non-directory path {dest_dir!s}!")

    if archive_name:
        logging.info("Archiving output files to output dataset")
        tar_and_copy(source=source_dir, dest=dest_dir, archive_name=archive_name)
    else:
        logging.info("Moving output file(s) to output dataset")
        for p in source_dir.glob("*"):
            shutil.move(p, dest_dir)


def gather_output(mpi_host_names: List[str], output_write_dir: Path):
    """
    Using subprocesses, gather output from remote MPI hosts and collect in the analogous directory on this host.

    Parameters
    ----------
    mpi_host_names
        List of MPI host names for the relevant job.
    output_write_dir
        Common job output directory across all hosts, from which data on remotes should be taken and in which data on
        this host should be collected.
    """
    from socket import gethostname
    local_hostname = gethostname()

    scp_subs = OrderedDict()

    for host in (h for h in mpi_host_names if h != local_hostname):
        scp_subs[host] = Popen(f"scp -q -r {host}:${output_write_dir!s}/ ${output_write_dir!s}/.")

    for host, process in scp_subs.items():
        _, error_in_bytes = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"{get_date_str()} gather_output failed for '{host}' (code={process.returncode}): \n"
                               f"{error_in_bytes.decode()}")


def get_date_str() -> str:
    """
    Get the current date and time as a string with format ``%Y-%m-%d,%H:%M:%S``

    Returns
    -------
    The current date and time as a string.
    """
    return datetime.now().strftime('%Y-%m-%d,%H:%M:%S')


def move_job_output(output_directory: Path, move_action: str, do_archiving: Optional[bool] = None,
                    job_id: Optional[str] = None, **kwargs):
    """
    Move output data files from a job from their initial directory to somewhere, depending on the CLI-given move action.

    If `do_archiving` is either ``True`` or ``False`` (by default, it is ``None``), have that control whether output
    files should be archived before moving. If it is ``None``, re-set its value to whether the output directory contains
    more than 100 individual files.

    Parameters
    ----------
    output_directory
    move_action
    do_archiving
    kwargs
        Other keyword args from the CLI specific to the particular move action to be performed.

    """
    if not output_directory.is_dir():
        raise ValueError(
            f"{get_date_str()} Can't move job output from non-directory path {output_directory!s} to output dataset")


    # If this was not set, dynamically determine what it should be
    if do_archiving is None:
        # For now, just do this if the output data contains more than 100 individual files
        out_dir_files = [f for f in output_directory.glob("**/*")]
        out_dir_file_count = len(out_dir_files)
        logging.debug(f"Dir {output_directory!s} contains {out_dir_file_count!s} files")
        max_displayed = 25
        displayed = "\n    ".join((str(f) for f in (out_dir_files[:25] if len(out_dir_files) > 25 else out_dir_files)))
        logging.debug(f"List of files in {output_directory!s} (max first {max_displayed!s}): \n    {displayed}")
        do_archiving = out_dir_file_count > 100
    else:
        logging.debug(f"Archiving parameter was set to {do_archiving!s}")

    assert do_archiving is not None

    # Sub-commands will know if they should do archiving based on whether they actually receive and archive name to use
    if do_archiving:
        archive_name = f"job-{job_id}-output.tar" if job_id else "job-output.tar"
        logging.debug(f"Archiving files with archive name {archive_name}")
    else:
        logging.debug("Set to not archive files before moving")
        archive_name = None

    if move_action == "to_directory":
        _move_to_directory(source_dir=output_directory, dest_dir=kwargs["dest_dir"], archive_name=archive_name)
    else:
        raise RuntimeError(f"{get_date_str()} Invalid CLI move action {move_action}")


def process_mpi_hosts_string(hosts_string: str, hosts_sep: str = ",", host_details_sep: str = ":") -> Dict[str, int]:
    """
    Process the MPI hosts string received by worker entrypoint, splitting into a mapping of host names and processes.

    Parameters
    ----------
    hosts_string
        The raw host string received by the worker when the service container is started.
    hosts_sep
        The delimiter between individual host entries within the string; by default, ``,``.
    host_details_sep
        The delimiter, within a host entry substring, between the host name and the number of processes for that host.

    Returns
    -------
    A dictionary, keyed by host name, mapped to the number of processes for each host.
    """
    results = dict()
    for host_entry in hosts_string.split(sep=hosts_sep):
        split_host_details = host_entry.split(sep=host_details_sep)
        if len(split_host_details) != 2:
            raise ValueError(f"Unexpected format for MPI host string (using '{hosts_sep}' and '{host_details_sep}'): "
                             f"'{hosts_string}'")
        results[split_host_details[0]] = int(split_host_details[1])
    return results


def tar_and_copy(source: Path, dest: Path, archive_name: str, do_dry_run: bool = False, do_compress: bool = False):
    """
    Make a tar archive from the contents of a directory, and place this in a specified destination.

    Parameters
    ----------
    source
        Directory whose contents should be archived.
    dest
        Destination directory in which to place the archive file.
    archive_name
        Basename for the created archive file.
    do_dry_run
        Whether to only perform a dry run to check paths, with no archiving/moving/copying.
    do_compress
        Whether to compress the created archive with gzip compression.

    Raises
    -------
    ValueError
        If the source or dest directory either does not exist or is not a directory; also, if the archive file already
        exists.
    """
    if not source.exists():
        raise ValueError(f"{get_date_str()} tar_and_copy source directory {source!s} does not exist!")
    elif not source.is_dir():
        raise ValueError(f"{get_date_str()} Non-directory file at path for tar_and_copy source directory {source!s}!")

    if not dest.exists():
        raise ValueError(f"{get_date_str()} tar_and_copy destination directory {dest!s} does not exist!")
    elif not dest.is_dir():
        raise ValueError(f"{get_date_str()} Non-directory file at path for tar_and_copy dest directory {dest!s}!")

    # We may change things in the future to write somewhere else, so do things in a little more of a round-about way
    # This is where the archive initially gets created
    archive_create_path = dest.joinpath(archive_name)
    # This is where it must eventually go
    final_archive_path = dest.joinpath(archive_name)

    if archive_create_path.exists():
        raise ValueError(f"{get_date_str()} File exists at tar_and_copy archive path {archive_create_path!s}!")
    if final_archive_path != archive_create_path and final_archive_path.exists():
        raise ValueError(f"{get_date_str()} Archive for tar_and_copy already exists in dest at {final_archive_path!s}!")

    if do_dry_run:
        return

    tar_mode_args = "w:gz" if do_compress else "w"
    with tarfile.open(archive_create_path, tar_mode_args) as tar:
        for p in source.glob("*"):
            tar.add(p, arcname=p.name)

    if archive_create_path != final_archive_path:
        shutil.move(archive_create_path, final_archive_path)


def main():
    args = _parse_args()

    _apply_logging(args.log_level)

    if args.command == 'tar_and_copy':
        tar_and_copy(**(vars(args)))
    elif args.command == 'gather_output':
        mpi_host_to_nproc_map = process_mpi_hosts_string(args.mpi_hosts_str)
        gather_output(mpi_host_names=[h for h in mpi_host_to_nproc_map], output_write_dir=args.output_write_dir)
    elif args.command == 'move_job_output':
        move_job_output(**(vars(args)))
    else:
        raise ValueError("Unsupported command {}".format(args.command))


if __name__ == '__main__':
    main()
