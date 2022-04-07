import argparse
from . import name as package_name
from .dmod_client import YamlClientConfig, DmodClient
from dmod.communication.client import get_or_create_eventloop
from dmod.core.meta_data import DataCategory
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

    dataset_categories = [str(e.name).lower() for e in DataCategory]

    # Nested parser for the 'create' action, with required argument for dataset name
    parser_create = action_subparsers.add_parser('create')
    parser_create.add_argument('name', help='Specify the name of the dataset to create.')
    parser_create.add_argument('--paths', dest='upload_paths', nargs='?', help='Specify files/directories to upload.')
    parser_create.add_argument('category', choices=dataset_categories, help='Specify dataset category.')

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
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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

    parser.prog = package_name
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


def execute_dataset_command(parsed_args, client: DmodClient):
    async_loop = get_or_create_eventloop()
    if parsed_args.action == 'create':
        category = DataCategory.get_for_name(parsed_args.category)
        upload_paths, bad_paths = _process_uploads(parsed_args.upload_paths)
        if len(bad_paths):
            raise RuntimeError('Aborted before dataset {} created; invalid upload paths: {}'.format(parsed_args.name,
                                                                                                    bad_paths))

        # Proceed with create, and raising error on failure
        if not async_loop.run_until_complete(client.create_dataset(parsed_args.name, category)):
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

    blah = ''


if __name__ == '__main__':
    main()