import argparse
import datetime
import json
from dmod.core.execution import AllocationParadigm
from . import name as package_name
from .dmod_client import YamlClientConfig, DmodClient
from dmod.communication.client import get_or_create_eventloop
from dmod.core.meta_data import ContinuousRestriction, DataCategory, DataDomain, DataFormat, DiscreteRestriction
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_CLIENT_CONFIG_BASENAME = '.dmod_client_config.yml'


class DmodCliArgumentError(ValueError):
    """
    Trivial, but distinct, error type for errors involving bad args to the DMOD CLI client.
    """
    pass


def _handle_config_command_args(parent_subparsers_container):
    """
    Handle setup of arg parsing for 'config' command, which allows for various operations related to config.

    Parameters
    ----------
    parent_subparsers_container
        The top-level parent container for subparsers of various commands, including the 'dataset' command, to which
        some numbers of nested subparser containers and parsers will be added.
    """
    # A parser for the 'config' command itself, underneath the parent 'command' subparsers container
    command_parser = parent_subparsers_container.add_parser('config')
    command_parser.add_argument('action', choices=['print', 'validate'], help='Specify action to perform on the config')


def _handle_exec_command_args(parent_subparsers_container):
    """
    Handle setup of arg parsing for 'exec' command, which allows for various workflow executions.

    Parameters
    ----------
    parent_subparsers_container
        The top-level parent container for subparsers of various commands, including the 'exec' command, to which
        some numbers of nested subparser containers and parsers will be added.
    """
    # A parser for the 'exec' command itself, underneath the parent 'command' subparsers container
    command_parser = parent_subparsers_container.add_parser('exec')

    # Subparser under the exec command's parser for handling the different workflows that might be run
    workflow_subparsers = command_parser.add_subparsers(dest='workflow')
    workflow_subparsers.required = True

    # Nested parser for the 'ngen' action
    parser_ngen = workflow_subparsers.add_parser('ngen')

    parser_ngen_cal = workflow_subparsers.add_parser('ngen_cal')
    # parser_ngen_cal.add_argument('--allocation-paradigm',
    #                          dest='allocation_paradigm',
    #                          type=AllocationParadigm.get_from_name,
    #                          choices=[val.name.lower() for val in AllocationParadigm],
    #                          default=AllocationParadigm.get_default_selection(),
    #                          help='Specify job resource allocation paradigm to use.')
    parser_ngen_cal.add_argument('realization_cfg_data_id', help='Identifier of dataset of required realization config')
    # parser_ngen_cal.add_argument('cpu_count', type=int, help='Provide the desired number of processes for the execution')


    parser_ngen.add_argument('--partition-config-data-id', dest='partition_cfg_data_id', default=None,
                             help='Provide data_id for desired partition config dataset.')
    parser_ngen.add_argument('--allocation-paradigm',
                             dest='allocation_paradigm',
                             type=AllocationParadigm.get_from_name,
                             choices=[val.name.lower() for val in AllocationParadigm],
                             default=AllocationParadigm.get_default_selection(),
                             help='Specify job resource allocation paradigm to use.')
    parser_ngen.add_argument('--catchment-ids', dest='cat_ids', nargs='+', help='Specify catchment subset.')
    date_format = DataDomain.get_datetime_str_format()
    printable_date_format = 'YYYY-mm-dd HH:MM:SS'

    def date_parser(date_time_str: str) -> datetime.datetime:
        try:
            return datetime.datetime.strptime(date_time_str, date_format)
        except ValueError:
            raise argparse.ArgumentTypeError("Not a valid date: {}".format(date_time_str))

    parser_ngen.add_argument('start', type=date_parser, help='Model start date and time ({})'.format(printable_date_format))
    parser_ngen.add_argument('end', type=date_parser, help='Model end date and time ({})'.format(printable_date_format))
    parser_ngen.add_argument('hydrofabric_data_id', help='Identifier of dataset of required hydrofabric')
    parser_ngen.add_argument('hydrofabric_uid', help='Unique identifier of required hydrofabric')
    parser_ngen.add_argument('realization_cfg_data_id', help='Identifier of dataset of required realization config')
    parser_ngen.add_argument('bmi_cfg_data_id', help='Identifier of dataset of required BMI init configs')
    parser_ngen.add_argument('cpu_count', type=int, help='Provide the desired number of processes for the execution')


def _handle_dataset_command_args(parent_subparsers_container):
    """
    Handle setup of arg parsing for 'dataset' command, which allows for various operations related to datasets.

    Parameters
    ----------
    parent_subparsers_container
        The top-level parent container for subparsers of various commands, including the 'dataset' command, to which
        some numbers of nested subparser containers and parsers will be added.
    """
    # A parser for the 'dataset' command itself, underneath the parent 'command' subparsers container
    command_parser = parent_subparsers_container.add_parser('dataset')

    # Subparser under the dataset command's parser for handling the different actions that might be done relating to a
    # dataset (e.g., creation or uploading of data)
    action_subparsers = command_parser.add_subparsers(dest='action')
    action_subparsers.required = True

    dataset_categories = [e.name.lower() for e in DataCategory]
    dataset_formats = [e.name for e in DataFormat]

    # Nested parser for the 'create' action, with required argument for dataset name, category, and format
    parser_create = action_subparsers.add_parser('create')
    parser_create.add_argument('name', help='Specify the name of the dataset to create.')
    parser_create.add_argument('--paths', dest='upload_paths', nargs='+', help='Specify files/directories to upload.')
    json_form = '{"variable": "<variable_name>", ("begin": "<value>", "end": "<value>" | "values": [<values>])}'
    restrict_help_str = 'Specify continuous or discrete domain restriction as (simplified) serialized JSON - {}'
    parser_create.add_argument('--restriction', dest='domain_restrictions', nargs='*',
                               help=restrict_help_str.format(json_form))
    parser_create.add_argument('--format', dest='dataset_format', choices=dataset_formats, help='Specify dataset domain format.')
    parser_create.add_argument('--domain-json', dest='domain_file', help='Deserialize the dataset domain from a file.')
    parser_create.add_argument('category', choices=dataset_categories, help='Specify dataset category.')

    # Nested parser for the 'delete' action, with required argument for dataset name
    parser_delete = action_subparsers.add_parser('delete')
    parser_delete.add_argument('name', help='Specify the name of the dataset to delete.')

    # Nested parser for the 'upload' action, with required args for dataset name and files to upload
    parser_upload = action_subparsers.add_parser('upload')
    parser_upload.add_argument('name', help='Specify the name of the desired dataset.')
    parser_upload.add_argument('paths', nargs='+', help='Specify files or directories to upload.')

    # Nested parser for the 'upload' action, with required args for dataset name and files to upload
    parser_download = action_subparsers.add_parser('download')
    parser_download.add_argument('name', help='Specify the name of the desired dataset.')
    parser_download.add_argument('--dest', dest='download_dest', default=None,
                                 help='Specify local destination path to save to.')
    parser_download.add_argument('path', help='Specify a file/item within dataset to download.')

    # Nested parser for the 'upload' action, with required args for dataset name and files to upload
    parser_download_all = action_subparsers.add_parser('download_all')
    parser_download_all.add_argument('name', help='Specify the name of the desired dataset.')
    parser_download_all.add_argument('--directory', dest='download_dir', default=None,
                                     help='Specify local destination directory to save to (defaults to ./<dataset_name>')

    # Nested parser for the 'list' action
    parser_list = action_subparsers.add_parser('list')
    listing_categories_choices = list(dataset_categories)
    listing_categories_choices.append('all')
    parser_list.add_argument('category', choices=listing_categories_choices, nargs='?', default='all',
                             help='Specify the category of dataset to list')


def _handle_jobs_command_args(parent_subparsers_container):
    """
    Handle setup of arg parsing for 'jobs' command, which allows for various query and control actions regarding jobs.

    Parameters
    ----------
    parent_subparsers_container
        The top-level parent container for subparsers of various commands, including the 'jobs' command, to which
        some numbers of nested subparser containers and parsers will be added.
    """
    # A parser for the 'jobs' command itself, underneath the parent 'command' subparsers container
    command_parser = parent_subparsers_container.add_parser('jobs')

    # Subparser under the jobs command's parser for handling the different query or control that might be run
    subcommand_subparsers = command_parser.add_subparsers(dest='subcommand')
    subcommand_subparsers.required = True

    # Nested parser for the 'list' action
    parser_list_jobs = subcommand_subparsers.add_parser('list')
    parser_list_jobs.add_argument('--active', dest='jobs_list_active_only', action='store_true',
                                  help='List only jobs with "active" status')

    # Nested parser for the 'info' action
    parser_job_info = subcommand_subparsers.add_parser('info')
    parser_job_info.add_argument('job_id', help='The id of the job for which to retrieve job state info')

    # Nested parser for the 'release' action
    parser_job_release = subcommand_subparsers.add_parser('release')
    parser_job_release.add_argument('job_id', help='The id of the job for which to release resources')

    # Nested parser for the 'status' action
    parser_job_status = subcommand_subparsers.add_parser('status')
    parser_job_status.add_argument('job_id', help='The id of the job for which to retrieve status')

    # Nested parser for the 'stop' action
    parser_job_stop = subcommand_subparsers.add_parser('stop')
    parser_job_stop.add_argument('job_id', help='The id of the job to stop')


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='dmod.client')
    parser.add_argument('--client-config',
                        help='Set path to client configuration file',
                        dest='client_config',
                        default=None)
    parser.add_argument('--bypass-request-service', '-b', dest='bypass_reqsrv', action='store_true', default=False,
                        help='Attempt to connect directly to the applicable service')
    # Top-level subparsers container, splitting off a variety of handled commands for different behavior
    # e.g., 'dataset' to do things related to datasets, like creation
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    # Nested command parsers handling actions of dataset command
    _handle_dataset_command_args(parent_subparsers_container=subparsers)
    # Nested command parsers handling config actions
    _handle_config_command_args(parent_subparsers_container=subparsers)
    # Nested command parsers handling exec actions
    _handle_exec_command_args(parent_subparsers_container=subparsers)
    # Nested command parsers handling jobs querying and control command actions
    _handle_jobs_command_args(parent_subparsers_container=subparsers)

    #parser.prog = package_name
    return parser.parse_args()


def find_client_config(basenames: Optional[List[str]] = None, dirs: Optional[List[Path]] = None) -> Optional[Path]:
    """
    Search locations for the client config of given basenames, falling back to defaults, and returning path if found.

    Each basename of each directory is iterated through (i.e., all options in 1st dir, all options in 2nd dir, etc.),
    until an existing file is encountered.

    Default if nothing provided for basename is the value of ``DEFAULT_CLIENT_CONFIG_BASENAME``.

    Default if nothing provided for dirs is the current directory and the user's home directory, in that order.

    Parameters
    ----------
    basenames
    dirs

    Returns
    -------
    Optional[Path]
        The path of the found config file, or ``None``.
    """
    if basenames is None or len(basenames) == 0:
        basenames = [DEFAULT_CLIENT_CONFIG_BASENAME]

    if dirs is None or len(dirs) == 0:
        dirs = [Path('.'), Path.home()]

    existing = [d.joinpath(basename) for d in dirs for basename in basenames if d.joinpath(basename).is_file()]
    return existing[0] if len(existing) > 0 else None


def _process_uploads(upload_path_str: Optional[List[str]]) -> Tuple[List[Path], List[Path]]:
    """
    Process the given list of string representations of paths, returning a tuple of lists of processed and bad paths.

    Process the given list of string representations of paths, converting the initial list to a second list of
    ::class:`Path` objects. Then, derive a third list from the second, consisting of any "bad" paths that do not
    exist.  Return a tuple containing the second and third lists.

    If the param is ``None``, it will be treated as an empty list, resulting in a tuple of two empty lists returned.

    Parameters
    ----------
    upload_path_str : Optional[List[str]]
        A list of string forms of paths to process.

    Returns
    -------
    Tuple[List[Path], List[Path]]
        Tuple of two lists of ::class:`Path`, with the first list being all derived from the param, and the second being
        a list of any non-existing ::class:`Path` objects within the first list.
    """
    # Convert the string form of the given paths to Path objects
    upload_paths = [] if upload_path_str is None else [Path(p) for p in upload_path_str]
    # Track bad paths, though, so that we can bail if there are any
    bad_paths = [p for p in upload_paths if not p.exists()]
    return upload_paths, bad_paths


def _process_domain_restriction_args(domain_restriction_strs: List[str]) -> Tuple[List[ContinuousRestriction], List[DiscreteRestriction]]:
    """
    Process serialized JSON strings to restriction objects.

    Strings are expected to be in either the standard serialized format from each type's ``to_dict`` function, or
    for continuous restrictions, in a similar, truncated form that can be converted to the standard format by using
    ::method:`ContinuousRestriction.convert_truncated_serial_form`.

    Parameters
    ----------
    domain_restriction_strs : List[str]
        List of JSON strings, where strings are serialized restriction objects, possibly in a simplified format for
        ::class:`ContinuousRestriction`

    Returns
    -------
    Tuple[List[ContinuousRestriction], List[DiscreteRestriction]]
        A tuple of two lists of restriction objects, with the first being continuous and the second discrete.
    """
    discrete_restrictions = []
    continuous_restrictions = []
    for json_str in domain_restriction_strs:
        json_obj = json.loads(json_str)
        discrete_restrict = DiscreteRestriction.factory_init_from_deserialized_json(json_obj)
        if discrete_restrict is not None:
            discrete_restrictions.append(discrete_restrict)
            continue
        continuous_restrict = ContinuousRestriction.factory_init_from_deserialized_json(json_obj)
        if continuous_restrict is not None:
            continuous_restrictions.append(continuous_restrict)
            continue
        # Try this as well so continuous restrictions can use simpler format
        continuous_restrict = ContinuousRestriction.factory_init_from_deserialized_json(
            ContinuousRestriction.convert_truncated_serial_form(json_obj))
        if continuous_restrict is not None:
            continuous_restrictions.append(continuous_restrict)
            continue
    return continuous_restrictions, discrete_restrictions


def execute_dataset_command(parsed_args, client: DmodClient):
    async_loop = get_or_create_eventloop()
    if parsed_args.action == 'create':
        category = DataCategory.get_for_name(parsed_args.category)
        upload_paths, bad_paths = _process_uploads(parsed_args.upload_paths)
        if len(bad_paths):
            raise RuntimeError('Aborted before dataset {} created; invalid upload paths: {}'.format(parsed_args.name,
                                                                                                    bad_paths))
        # Proceed with create, and raising error on failure

        key_args = dict()

        # If we have a domain file, parse it, and use it as the only key args
        if parsed_args.domain_file is not None:
            domain_file = Path(parsed_args.domain_file)
            domain = DataDomain.factory_init_from_deserialized_json(json.load(domain_file.open()))
            if domain is None:
                raise RuntimeError("Could not deserialize data domain from file {}".format(domain_file))
            key_args['domain'] = domain
        else:
            # Otherwise, start by processing any serialized restrictions provided on the command line
            c_restricts, d_restricts = _process_domain_restriction_args(parsed_args.domain_restrictions)
            # With restrictions processed, proceed to generating keyword args for the client's create function
            data_format = DataFormat.get_for_name(parsed_args.dataset_format)
            if data_format is None:
                msg = 'Failed to create dataset {} due to unparseable data format'
                raise RuntimeError(msg.format(parsed_args.name, parsed_args.dataset_format))
            else:
                key_args['data_format'] = data_format
            # Finally, assemble the key args we will use
            if d_restricts:
                key_args['discrete_restrictions'] = d_restricts
            if c_restricts:
                key_args['continuous_restrictions'] = c_restricts

        if not async_loop.run_until_complete(client.create_dataset(parsed_args.name, category, **key_args)):
            raise RuntimeError('Failed to create dataset {}'.format(parsed_args.name))
        # Display message if create succeeded and there was nothing to upload
        elif len(upload_paths) == 0:
            print('Dataset {} of category {} created successfully'.format(parsed_args.name, category))
        # Handle uploads if there are some after create succeeded, but if those failed ...
        if not async_loop.run_until_complete(client.upload_to_dataset(parsed_args.name, upload_paths)):
            raise RuntimeError('Dataset {} created, but upload of data failed from paths {}'.format(parsed_args.name,
                                                                                                    upload_paths))
        # Lastly (i.e., if uploading did work)
        else:
            print('Dataset {} of category {} created successfully, and uploaded {}'.format(parsed_args.name, category,
                                                                                           upload_paths))
    elif parsed_args.action == 'list':
        category = None if parsed_args.category == 'all' else DataCategory.get_for_name(parsed_args.category)
        dataset_names = async_loop.run_until_complete(client.list_datasets(category))
        if len(dataset_names) == 0:
            print('No existing datasets were found.')
        else:
            for d in dataset_names:
                print(d)

    elif parsed_args.action == 'delete':
        if not async_loop.run_until_complete(client.delete_dataset(parsed_args.name)):
            raise RuntimeError('Failed to delete dataset {}'.format(parsed_args.name))

    elif parsed_args.action == 'upload':
        upload_paths, bad_paths = _process_uploads(parsed_args.paths)
        if len(bad_paths):
            raise RuntimeError("Can't upload to {} - invalid upload paths: {}".format(parsed_args.name, bad_paths))
        elif not async_loop.run_until_complete(client.upload_to_dataset(parsed_args.name, upload_paths)):
            raise RuntimeError('Upload of data to {} failed from paths {}'.format(parsed_args.name, upload_paths))
        else:
            print('Upload succeeded.')

    elif parsed_args.action == 'download':
        if parsed_args.download_dest is None:
            dest = Path('./{}'.format(Path(parsed_args.path).name))
        else:
            dest = Path(parsed_args.download_dest)
        if not dest.parent.is_dir():
            raise RuntimeError("Cannot download file to {}:  parent directory doesn't exist.".format(dest))
        if dest.exists():
            raise RuntimeError("Cannot download file to {}:  file already exists".format(dest))
        if not async_loop.run_until_complete(client.download_from_dataset(dataset_name=parsed_args.name,
                                                                          item_name=parsed_args.path, dest=dest)):
            msg = 'Download of {} data to {} failed from locations {}'
            raise RuntimeError(msg.format(parsed_args.name, dest, parsed_args.path))
        else:
            print('Downloaded {} to local file {}.'.format(parsed_args.path, dest))

    elif parsed_args.action == 'download_all':
        dest_dir = Path(parsed_args.download_dir) if parsed_args.download_dir is not None else Path(parsed_args.name)
        if dest_dir.exists():
            if dest_dir.is_dir():
                dest_dir_orig = dest_dir.name
                old_backup = dest_dir.rename(dest_dir.parent.joinpath('.{}_old'.format(dest_dir_orig)))
                dest_dir = dest_dir.parent.joinpath(dest_dir_orig)
                dest_dir.mkdir()
                print("Backing up existing {} to {}".format(dest_dir, old_backup))
            else:
                RuntimeError("Can't download files to directory named '{}':  this is an existing file".format(dest_dir))
        if not async_loop.run_until_complete(client.download_dataset(dataset_name=parsed_args.name, dest_dir=dest_dir)):
            msg = 'Download of dataset {} to directory {} failed.'
            raise RuntimeError(msg.format(parsed_args.name, dest_dir))
        else:
            print('Downloaded {} contents to local directory {}.'.format(parsed_args.name, dest_dir))
    else:
        raise RuntimeError("Bad dataset command action '{}'".format(parsed_args.action))


def execute_config_command(parsed_args, client: DmodClient):
    if parsed_args.action == 'print':
        client.print_config()
    elif parsed_args.action == 'validate':
        client.validate_config()
    else:
        raise RuntimeError("Bad client command action '{}'".format(parsed_args.action))


def execute_jobs_command(args, client: DmodClient):
    async_loop = get_or_create_eventloop()
    try:
        if args.subcommand == 'info':
            result = async_loop.run_until_complete(client.request_job_info(**(vars(args))))
        elif args.subcommand == 'list':
            result = async_loop.run_until_complete(client.request_jobs_list(**(vars(args))))
        elif args.subcommand == 'release':
            result = async_loop.run_until_complete(client.request_job_release(**(vars(args))))
        elif args.subcommand == 'status':
            result = async_loop.run_until_complete(client.request_job_status(**(vars(args))))
        elif args.subcommand == 'stop':
            result = async_loop.run_until_complete(client.request_job_stop(**(vars(args))))
        else:
            raise DmodCliArgumentError()
        print(result)
    except DmodCliArgumentError as e:
        print("ERROR: Unsupported jobs subcommand {}".format(args.subcommand))
        exit(1)
    except Exception as e:
        print("ERROR: Encountered {} - {}".format(e.__class__.__name__, str(e)))
        exit(1)


def execute_workflow_command(args, client: DmodClient):
    async_loop = get_or_create_eventloop()
    # TODO: aaraney
    if args.workflow == 'ngen':
        result = async_loop.run_until_complete(client.submit_ngen_request(**(vars(args))))
        print(result)
    elif args.workflow == "ngen_cal":
        result = async_loop.run_until_complete(client.submit_ngen_cal_request(realization_cfg_data_id=args.realization_cfg_data_id))
        print(result)
    else:
        print("ERROR: Unsupported execution workflow {}".format(args.workflow))
        exit(1)


def main():
    args = _handle_args()
    client_config_path = find_client_config() if args.client_config is None else Path(args.client_config)
    if client_config_path is None:
        print("ERROR: Could not find any suitable DMOD CLI client configuration file")
        exit(1)

    try:
        client = DmodClient(client_config=YamlClientConfig(client_config_path), bypass_request_service=args.bypass_reqsrv)

        if args.command == 'config':
            execute_config_command(args, client)
        elif args.command == 'dataset':
            execute_dataset_command(args, client)
        elif args.command == 'exec':
            execute_workflow_command(args, client)
        elif args.command == 'jobs':
            execute_jobs_command(args, client)
        else:
            raise ValueError("Unsupported command {}".format(args.command))

    except Exception as error:
        print("ERROR: {}".format(error))
        exit(1)


if __name__ == '__main__':
    main()
