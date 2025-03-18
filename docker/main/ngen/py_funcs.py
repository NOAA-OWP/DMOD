#!/usr/bin/env python3

import argparse
import json
import logging
import os
import shutil
import tarfile
import concurrent.futures
import subprocess

from datetime import datetime
from enum import Enum
from pathlib import Path
from subprocess import Popen
from typing import Dict, List, Literal, Optional, Set, Tuple


MINIO_ALIAS_NAME = "minio"


def get_dmod_date_str_pattern() -> str:
    return '%Y-%m-%d,%H:%M:%S'


class ArchiveStrategy(Enum):
    """ Settings for whether something that may/can archive files should, should not, or should decide for itself. """
    FORCE = "force"
    DISALLOW = "disallow"
    DYNAMIC = "dynamic"


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


def _parse_for_make_data_local(parent_subparsers_container):
    # A parser for the 'tar_and_copy' param itself, underneath the parent 'command' subparsers container
    desc = "If a primary worker, copy/extract to make dataset data locally available on physical node"
    helper_cmd_parser = parent_subparsers_container.add_parser('make_data_local', description=desc)
    helper_cmd_parser.add_argument('worker_index', type=int, help='The index of this particular worker.')
    helper_cmd_parser.add_argument('primary_workers', type=lambda s: {int(i) for i in s.split(',')},
                                   help='Comma-delimited string of primary worker indices.')


def _parse_for_move_job_output(parent_subparsers_container):
    # A parser for the 'tar_and_copy' param itself, underneath the parent 'command' subparsers container
    desc = "Move output data files produced by a job to another location, typically to put them into a DMOD dataset."
    helper_cmd_parser = parent_subparsers_container.add_parser('move_job_output', description=desc)
    helper_cmd_parser.add_argument('--job_id', '--job-id', dest='job_id', help='Optionally specify job id.')
    helper_cmd_parser.add_argument("--archiving", dest="archiving", default=ArchiveStrategy.DYNAMIC,
                                   type=ArchiveStrategy, help="Set whether job output should be archived before moving")
    helper_cmd_parser.add_argument('output_directory', type=Path,
                                   help='Source directory containing output files to be moved.')

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
    _parse_for_make_data_local(parent_subparsers_container=subparsers)

    return parser.parse_args()


def _get_serial_dataset_dict(serialized_ds_file: Path) -> dict:
    with serialized_ds_file.open() as s_file:
        return json.loads(s_file.read())


def _make_dataset_dir_local(local_data_dir: Path, do_optimized_object_store_copy: bool):
    """
    Make the data in corresponding remotely-backed dataset directory local by placing in a local directory.

    Make a local, optimized copy of data from a dataset, where the data is also locally accessible/mounted but actually
    stored elsewhere, making it less optimal for use by the worker.

    Function examines the serialized dataset file of the source directory and, if already present (indicating this dest
    directory has been set up before), the analogous serialized dataset file in the destination directory. First, if
    there is `dest_dir` version of this file, and if it has the same ``last_updated`` value, the function considers the
    `dest_dir` contents to already be in sync with the `src_dir` simply returns.  Second, it examines whether archiving
    was used for the entire dataset, and then either extracts or copies data to the local volume as appropriate.

    Note that the function does alter the name of the serialized dataset file on the `dest_dir` side, primarily as an
    indication that this is meant as a local copy of data, but not a full-fledge DMOD dataset.  It also allows for a
    final deliberate step of renaming (or copying with a different name) this file, which ensures the checked
    ``last_updated`` value on the `dest_dir` side will have not been updated before a successful sync of the actual data
    was completed.

    Parameters
    ----------
    local_data_dir
        Storage directory, locally available on this worker's host node, in which to copy/extract data.
    do_optimized_object_store_copy
        Whether to do an optimized copy for object store dataset data using the MinIO client (via a subprocess call).
    """
    # TODO: (later) eventually source several details of this this from other part of the code

    dataset_vol_dir = get_cluster_volumes_root_directory().joinpath(local_data_dir.parent.name).joinpath(local_data_dir.name)

    local_serial_file = local_data_dir.joinpath(".ds_serial_state.json")
    dataset_serial_file = dataset_vol_dir.joinpath(f"{dataset_vol_dir.name}_serialized.json")

    # Both should exist
    if not dataset_vol_dir.is_dir():
        raise RuntimeError(f"Can't make data local from dataset mount path '{dataset_vol_dir!s}': not a directory")
    elif not local_data_dir.is_dir():
        raise RuntimeError(f"Can't make data from '{dataset_vol_dir!s}' local: '{local_data_dir!s}' is not a directory")
    # Also, dataset dir should not be empty
    elif len([f for f in dataset_vol_dir.glob("*")]) == 0:
        raise RuntimeError(f"Can't make data local from '{dataset_vol_dir!s}' local because it is empty")

    serial_ds_dict = _get_serial_dataset_dict(dataset_serial_file)

    # If dest_dir is not brand new and has something in it, check to make sure it isn't already as it needs to be
    if local_serial_file.exists():
        prev_ds_dict = _get_serial_dataset_dict(local_serial_file)
        current_last_updated = datetime.strptime(serial_ds_dict["last_updated"], get_dmod_date_str_pattern())
        prev_last_updated = datetime.strptime(prev_ds_dict["last_updated"], get_dmod_date_str_pattern())
        if prev_last_updated == current_last_updated:
            logging.info(f"'{local_data_dir!s}' already shows most recent 'last_updated'; skipping redundant copy")
            return

    # Determine if need to extract
    if serial_ds_dict.get("data_archiving", False):
        # Identify and extract archive
        src_archive_file = [f for f in dataset_vol_dir.glob(f"{dataset_vol_dir.name}_archived*")][0]
        archive_file = local_data_dir.joinpath(src_archive_file.name)
        shutil.copy2(src_archive_file, archive_file)
        shutil.unpack_archive(archive_file, local_data_dir)
        archive_file.unlink(missing_ok=True)
        # Also manually copy serialized state file (do last)
        shutil.copy2(dataset_serial_file, local_serial_file)
    # Need to optimize by using minio client directly here when dealing with OBJECT_STORE dataset, or will take 10x time
    # TODO: (later) this is a bit of a hack, though a necessary one; find a way to integrate more elegantly
    elif do_optimized_object_store_copy and serial_ds_dict["type"] == "OBJECT_STORE":
        alias_src_path = f"{MINIO_ALIAS_NAME}/{local_data_dir.name}/"
        logging.info(f"Copying data from '{alias_src_path}' to '{local_data_dir}'")
        subprocess.run(["mc", "--config-dir", "/dmod/.mc", "cp", "-r", alias_src_path, f"{local_data_dir}/."],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        logging.info(f"Local copying from '{alias_src_path}' complete")
    else:
        # Otherwise copy contents
        shutil.copy2(dataset_vol_dir, local_data_dir)
        # Rename the copied serialized state file in the copy as needed
        # But do this last to confirm directory contents are never more up-to-date with last_updated than expected
        local_data_dir.joinpath(dataset_serial_file.name).rename(local_serial_file)


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
        logging.info(f"Archiving output files to output dataset directory '{dest_dir!s}'")
        tar_and_copy(source=source_dir, dest=dest_dir, archive_name=archive_name)
    else:
        logging.info("Moving output file(s) to output dataset directory '{dest_dir!s}'")
        for p in source_dir.glob("*"):
            shutil.move(p, dest_dir)


def _parse_docker_secret(secret_name: str) -> str:
    return Path("/run/secrets", secret_name).read_text().strip()


def _parse_object_store_secrets() -> Tuple[str, str]:
    return _parse_docker_secret('object_store_exec_user_name'), _parse_docker_secret('object_store_exec_user_passwd')


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

    scp_subs = dict()

    for host in (h for h in mpi_host_names if h != local_hostname):
        scp_subs[host] = Popen(f"scp -q -r {host}:${output_write_dir!s}/ ${output_write_dir!s}/.")

    for host, process in scp_subs.items():
        _, error_in_bytes = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"{get_date_str()} gather_output failed for '{host}' (code={process.returncode}): \n"
                               f"{error_in_bytes.decode()}")


def get_data_exec_root_directory() -> Path:
    """
    Get the root directory path to use for reading and writing dataset data during job execution.

    Returns
    -------
    Path
        The root directory path to use for reading and writing dataset data during job execution.
    """
    return Path("/dmod/datasets")


def get_cluster_volumes_root_directory() -> Path:
    """
    Get the root directory for cluster volumes (i.e., backed by dataset directly, synced cluster-wide) on this worker.

    Returns
    -------
    Path
        The root directory for cluster volumes on this worker.
    """
    return Path("/dmod/cluster_volumes")


def get_expected_data_category_subdirs() -> Set[str]:
    """
    Get names of expected subdirectories for dataset categories underneath directories like local or cluster volumes.

    Returns
    -------
    Set[str]
        Names of expected subdirectories for dataset categories underneath directories like local or cluster volumes.
    """
    return {"config", "forcing", "hydrofabric", "observation", "output"}


def get_local_volumes_root_directory() -> Path:
    """
    Get the root directory for local volumes (i.e., local to physical node, share by all node's workers) on this worker.

    Returns
    -------
    Path
        The root directory for local volumes on this worker.
    """
    return Path("/dmod/local_volumes")


def link_to_data_exec_root(exceptions: Optional[List[Path]] = None):
    """
    Create symlinks into the data exec root for any dataset subdirectories in, e.g., cluster or local data mounts.

    Function iterates through data mount roots for data (e.g., local volumes, cluster volumes) according to priority of
    their use (i.e., local volume data should be used before an analogous cluster volume copy).  If nothing for that
    dataset category and name exists under the data exec root (from ::function:`get_data_exec_root_directory`), then
    a symlink is created.

    Exceptions to the regular prioritization can be provided.  By default (or whenever ``execptions`` is ``None``),
    all ``output`` category/directory datasets will have their symlinks backed by cluster volumes over local volumes. To
    avoid any such exceptions and strictly follow the general priority rules, an empty list can be explicitly passed.

    Parameters
    ----------
    exceptions
        An optional list of exceptions to the general setup rules to create a symlink in the data exec root before
        anything else.

    """
    if exceptions is None:
        exceptions = [d for d in get_cluster_volumes_root_directory().joinpath('output').glob('*') if d.is_dir()]

    for d in exceptions:
        data_exec_analog = get_data_exec_root_directory().joinpath(d.parent.name).joinpath(d.name)
        if data_exec_analog.exists():
            if data_exec_analog.is_symlink():
                logging.warning(f"Overwriting previous symlink at '{data_exec_analog!s}' pointing to '{data_exec_analog.readlink()!s}")
            else:
                logging.warning(f"Overwriting previous contents at '{data_exec_analog}' with new symlink")
        else:
            logging.info(f"Creating dataset symlink with source '{d!s}'")
        os.symlink(d, data_exec_analog)
        logging.info(f"Symlink created at dest '{data_exec_analog!s}'")

    # Note that order here is important; prioritize local data if it is there
    data_symlink_sources = [get_local_volumes_root_directory(), get_cluster_volumes_root_directory()]
    for dir in data_symlink_sources:
        # At this level, order isn't as important
        for category_subdir in get_expected_data_category_subdirs():
            for dataset_dir in [d for d in dir.joinpath(category_subdir).glob('*') if d.is_dir()]:
                data_exec_analog = get_data_exec_root_directory().joinpath(category_subdir).joinpath(dataset_dir.name)
                if not data_exec_analog.exists():
                    logging.info(f"Creating dataset symlink with source '{dataset_dir!s}'")
                    os.symlink(dataset_dir, data_exec_analog)
                    logging.info(f"Symlink created at dest '{data_exec_analog!s}'")


def make_data_local(worker_index: int, primary_workers: Set[int], **kwargs):
    """
    Make data local for each local volume mount that exists, but only if this worker is a primary.

    Copy or extract data from mounted volumes/directories directly backed by DMOD datasets (i.e., "cluster volumes") to
    corresponding directories local to the physical node (i.e. "local volumes"), for any such local directories found to
    exist.  An important distinction is that a local volume is local to the physical node and not the worker itself, and
    thus is shared by all workers on that node.  As such, return immediately without performing any actions if this
    worker is not considered a "primary" worker, so that only one worker per node manipulates data.

    Function (for a primary worker) iterates through the local volume subdirectory paths to see if any local volumes
    were set up when the worker was created.  For any that are found, the function ensures data from the corresponding,
    dataset-backed cluster volume directory is replicated in the local volume directory.

    Parameters
    ----------
    worker_index
        This worker's index.
    primary_workers
        Indices of designated primary workers
    kwargs
        Other ignored keyword args.

    See Also
    --------
    _make_dataset_dir_local
    """

    # Every work does need to do this, though
    link_to_data_exec_root()

    if worker_index not in primary_workers:
        return

    cluster_vol_dir = get_cluster_volumes_root_directory()
    local_vol_dir = get_local_volumes_root_directory()
    expected_subdirs = get_expected_data_category_subdirs()

    if not cluster_vol_dir.exists():
        raise RuntimeError(f"Can't make data local: cluster volume root '{cluster_vol_dir!s}' does not exist")
    if not cluster_vol_dir.is_dir():
        raise RuntimeError(f"Can't make data local: cluster volume root '{cluster_vol_dir!s}' is not a directory")
    if not local_vol_dir.exists():
        raise RuntimeError(f"Can't make data local: local volume root '{local_vol_dir!s}' does not exist")
    if not local_vol_dir.is_dir():
        raise RuntimeError(f"Can't make data local: local volume root '{local_vol_dir!s}' is not a directory")

    try:
        obj_store_access_key, obj_store_secret_key = _parse_object_store_secrets()
        logging.info(f"Executing test run of minio client to see if alias '{MINIO_ALIAS_NAME}' already exists")
        mc_ls_result = subprocess.run(["mc", "--config-dir", "/dmod/.mc", "alias", "ls", MINIO_ALIAS_NAME])
        logging.debug(f"Return code from alias check was {mc_ls_result.returncode!s}")
        if mc_ls_result.returncode != 0:
            logging.info(f"Creating new minio alias '{MINIO_ALIAS_NAME}'")
            # TODO: (later) need to set value for obj_store_url better than just hardcoding it
            obj_store_url = "http://minio-proxy:9000"
            subprocess.run(["mc", "--config-dir", "/dmod/.mc", "alias", "set", MINIO_ALIAS_NAME, obj_store_url,
                            obj_store_access_key, obj_store_secret_key])
            logging.info(f"Now rechecking minio client test for '{MINIO_ALIAS_NAME}' alias")
            mc_ls_result_2 = subprocess.run(["mc", "--config-dir", "/dmod/.mc", "alias", "ls", MINIO_ALIAS_NAME])
            if mc_ls_result_2.returncode != 0:
                raise RuntimeError(f"Could not successfully create minio alias '{MINIO_ALIAS_NAME}'")
        do_optimized_object_store_copy = True
    except RuntimeError as e:
        raise e
    except Exception as e:
        logging.warning(f"Unable to parse secrets for optimized MinIO local data copying: {e!s}")
        do_optimized_object_store_copy = False

    # Use some multi-threading here since this is IO heavy
    logging.info(f"Performing local data copying using multiple threads")
    futures = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for type_dir in (td for td in local_vol_dir.glob("*") if td.is_dir()):
            if not cluster_vol_dir.joinpath(type_dir.name).is_dir():
                raise RuntimeError(f"Directory '{type_dir!s}' does not have analog in '{cluster_vol_dir!s}'")
            if type_dir.name not in expected_subdirs:
                logging.warning(f"Found unexpected (but matching) local volume data type subdirectory {type_dir.name}")
            for local_ds_dir in (d for d in type_dir.glob("*") if d.is_dir()):
                futures.add(pool.submit(_make_dataset_dir_local, local_ds_dir, do_optimized_object_store_copy))
        for future in futures:
            future.result()
    logging.info(f"Local data copying complete")


def get_date_str() -> str:
    """
    Get the current date and time as a string with format ``%Y-%m-%d,%H:%M:%S``

    Returns
    -------
    The current date and time as a string.
    """
    return datetime.now().strftime(get_dmod_date_str_pattern())


def move_job_output(output_directory: Path, move_action: str, archiving: ArchiveStrategy = ArchiveStrategy.DYNAMIC,
                    job_id: Optional[str] = None, **kwargs):
    """
    Move output data files from a job from their initial directory to somewhere, depending on the CLI-given move action.

    If `do_archiving` is either ``True`` or ``False`` (by default, it is ``None``), have that control whether output
    files should be archived before moving. If it is ``None``, re-set its value to whether the output directory contains
    more than 100 individual files.

    Parameters
    ----------
    output_directory
        Source directory containing output files to be moved.
    move_action
        The type of move action to be performed.
    archiving
        Strategy controlling whether job output should be archived before moving.
    job_id
        Optional job id, used as part of archive name when applicable.
    kwargs
        Other keyword args from the CLI specific to the particular move action to be performed.

    """
    if not output_directory.is_dir():
        raise ValueError(
            f"{get_date_str()} Can't move job output from non-directory path {output_directory!s} to output dataset")

    # If this was not set, dynamically determine what it should be
    if archiving == ArchiveStrategy.DYNAMIC:
        # For now, just do this if the output data contains more than 100 individual files
        out_dir_files = [f for f in output_directory.glob("**/*")]
        out_dir_file_count = len(out_dir_files)
        logging.debug(f"Dir {output_directory!s} contains {out_dir_file_count!s} files")
        max_displayed = 25
        displayed = "\n    ".join((str(f) for f in (out_dir_files[:25] if len(out_dir_files) > 25 else out_dir_files)))
        logging.debug(f"List of files in {output_directory!s} (max first {max_displayed!s}): \n    {displayed}")
        do_archiving = out_dir_file_count > 100
    else:
        logging.debug(f"Archiving parameter was set to {archiving.name}")
        do_archiving = archiving == ArchiveStrategy.FORCE

    assert do_archiving is not None

    # Sub-commands will know if they should do archiving based on whether they actually receive and archive name to use
    if do_archiving:
        archive_name = f"job-{job_id}-output.tar" if job_id else "job-output.tar"
        logging.debug(f"Archiving files with archive name {archive_name}")
    else:
        logging.debug("Set to not archive files before moving")
        archive_name = None

    if move_action == "to_directory":
        dest_dir = kwargs["dest_dir"]
        logging.info(f"Moving output from '{output_directory!s}' to '{dest_dir!s}'")
        _move_to_directory(source_dir=output_directory, dest_dir=dest_dir, archive_name=archive_name)
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


def tar_and_copy(source: Path, dest: Path, archive_name: str, do_dry_run: bool = False, do_compress: bool = False, **kwargs):
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
    kwargs
        Other unused keyword args.

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
    logging.info(f"Creating archive file '{archive_create_path!s}'")
    with tarfile.open(archive_create_path, tar_mode_args) as tar:
        for p in source.glob("*"):
            logging.debug(f"Adding '{p!s}' to archive")
            tar.add(p, arcname=p.name)

    if archive_create_path != final_archive_path:
        logging.info(f"Moving archive to final location at '{final_archive_path!s}'")
        shutil.move(archive_create_path, final_archive_path)
    else:
        logging.info(f"Archive creation complete and at final location")


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
    elif args.command == 'make_data_local':
        make_data_local(**(vars(args)))
    else:
        raise RuntimeError(f"Command arg '{args.command}' doesn't match a command supported by module's main function")


if __name__ == '__main__':
    main()
