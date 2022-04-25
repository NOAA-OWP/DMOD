import argparse
import json
from . import name as package_name
from .dmod_client import YamlClientConfig, DmodClient
from dmod.communication.client import get_or_create_eventloop
from dmod.core.meta_data import ContinuousRestriction, DataCategory, DataDomain, DataFormat, DiscreteRestriction
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_CLIENT_CONFIG_BASENAME = '.dmod_client_config.yml'


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

    command_parser.add_argument('--bypass-request-service', '-b', dest='bypass_reqsrv', action='store_true',
                                default=False, help='Attempt to connect directly to the data-service')

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

    # Nested parser for the 'list' action
    parser_list = action_subparsers.add_parser('list')
    listing_categories_choices = list(dataset_categories)
    listing_categories_choices.append('all')
    parser_list.add_argument('category', choices=listing_categories_choices, nargs='?', default='all',
                             help='Specify the category of dataset to list')


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='dmod.client')
    parser.add_argument('--client-config',
                        help='Set path to client configuration file',
                        dest='client_config',
                        default=None)
    # Top-level subparsers container, splitting off a variety of handled commands for different behavior
    # e.g., 'dataset' to do things related to datasets, like creation
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    # Nested command parsers handling actions of dataset command
    _handle_dataset_command_args(parent_subparsers_container=subparsers)
    # Nested command parsers handling config actions
    _handle_config_command_args(parent_subparsers_container=subparsers)

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


def _process_uploads(upload_path_str: Optional[List[str]]):
    # Get paths to upload, if appropriate, bailing before create if any are bad
    upload_paths = [Path(p) for p in upload_path_str] if upload_path_str is not None else []
    # Track bad paths, though, and bail if there are any
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
                raise RuntimeError("Could nod deserialize data domain from file {}".format(domain_file))
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
    elif parsed_args.action == 'upload':
        upload_paths, bad_paths = _process_uploads(parsed_args.paths)
        if len(bad_paths):
            raise RuntimeError("Can't upload to {} - invalid upload paths: {}".format(parsed_args.name, bad_paths))
        elif not async_loop.run_until_complete(client.upload_to_dataset(parsed_args.name, upload_paths)):
            raise RuntimeError('Upload of data to {} failed from paths {}'.format(parsed_args.name, upload_paths))
        else:
            print('Upload succeeded.')
    else:
        raise RuntimeError("Bad dataset command action '{}'".format(parsed_args.action))


def execute_config_command(parsed_args, client: DmodClient):
    if parsed_args.action == 'print':
        client.print_config()
    elif parsed_args.action == 'validate':
        client.validate_config()
    else:
        raise RuntimeError("Bad client command action '{}'".format(parsed_args.action))


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
        else:
            raise ValueError("Unsupported command {}".format(args.command))

    except Exception as error:
        print("ERROR: {}".format(error))
        exit(1)


if __name__ == '__main__':
    main()
