import argparse
import sys
import datetime
import json
from dmod.core.execution import AllocationParadigm
from . import name as package_name
from .dmod_client import ClientConfig, DmodClient
from dmod.communication.client import get_or_create_eventloop
from dmod.core.meta_data import ContinuousRestriction, DataCategory, DataDomain, DataFormat, DiscreteRestriction, \
    TimeRange
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type


DEFAULT_CLIENT_CONFIG_BASENAME = '.dmod_client_config.json'


class DmodCliArgumentError(ValueError):
    """
    Trivial, but distinct, error type for errors involving bad args to the DMOD CLI client.
    """
    pass


def _create_ngen_based_exec_parser(subcommand_container: Any, parser_name: str,
                                   default_alloc_paradigm: AllocationParadigm) -> argparse.ArgumentParser:
    """
    Helper function to create a nested parser under the ``exec`` command for different NextGen-related workflows.

    Parameters
    ----------
    subcommand_container
        The ``workflow`` subcommand "special action object" created by ::method:`ArgumentParser.add_subparsers`, which
        is a child of the ``exec`` parser, and to which the new nested parser is to be added.
    parser_name : str
        The name to give to the new parser to be added.
    default_alloc_paradigm : AllocationParadigm
        The default ::class:`AllocationParadigm` value to use when adding the ``--allocation-paradigm`` argument to the
        parser.

    Returns
    -------
    argparse.ArgumentParser
        The newly created and associated subparser.
    """
    new_parser = subcommand_container.add_parser(parser_name)
    new_parser.add_argument('--partition-config-data-id', dest='partition_cfg_data_id', default=None,
                            help='Provide data_id for desired partition config dataset.')
    new_parser.add_argument('--allocation-paradigm',
                            dest='allocation_paradigm',
                            type=AllocationParadigm.get_from_name,
                            choices=[val.name.lower() for val in AllocationParadigm],
                            default=default_alloc_paradigm,
                            help='Specify job resource allocation paradigm to use.')
    new_parser.add_argument('--catchment-ids', dest='catchments', nargs='+', help='Specify catchment subset.')
    new_parser.add_argument('--forcings-data-id', dest='forcings_data_id', help='Specify catchment subset.')

    date_format = DataDomain.get_datetime_str_format()
    print_date_format = 'YYYY-mm-dd HH:MM:SS'

    new_parser.add_argument('time_range', type=TimeRange.parse_from_string,
                            help='Model time range ({} to {})'.format(print_date_format, print_date_format))
    new_parser.add_argument('hydrofabric_data_id', help='Identifier of dataset of required hydrofabric')
    new_parser.add_argument('hydrofabric_uid', help='Unique identifier of required hydrofabric')
    new_parser.add_argument('config_data_id', help='Identifier of composite config dataset with required configs')
    new_parser.add_argument('cpu_count', type=int, help='Provide the desired number of processes for the execution')

    return new_parser


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

    See Also
    ----------
    _create_ngen_based_exec_subparser
    """
    # A parser for the 'exec' command itself, underneath the parent 'command' subparsers container
    command_parser = parent_subparsers_container.add_parser('exec')

    # Subparser under the exec command's parser for handling the different job workflows that might be started
    workflow_subparsers = command_parser.add_subparsers(dest='workflow_starter')
    workflow_subparsers.required = True

    # Add some parsers to deserialize a request from a JSON string, or ...
    parser_from_json = workflow_subparsers.add_parser("from_json")
    #parser_from_json.add_argument('--partition-config-data-id', dest='partition_cfg_data_id', default=None,
    #                                      help='Provide data_id for desired partition config dataset.')
    parser_from_json.add_argument('job_type', choices=['ngen', 'ngen_cal'],
                                  help="Set type of for request object so it is deserialized correctly")
    parser_from_json.add_argument('request_json',
                                  help='JSON string for exec request object to use to start a job')
    # ... from JSON contained within a file
    parser_from_file = workflow_subparsers.add_parser("from_file")
    parser_from_file.add_argument('job_type', choices=['ngen', 'ngen_cal'],
                                  help="Set type of for request object so it is deserialized correctly")
    parser_from_file.add_argument('request_file', type=Path,
                                  help='Path to file containing JSON exec request object to use to start a job')

    # Nested parser for the 'ngen' action
    parser_ngen = _create_ngen_based_exec_parser(subcommand_container=workflow_subparsers, parser_name='ngen',
                                                 default_alloc_paradigm=AllocationParadigm.get_default_selection())

    # TODO: default alloc paradigm needs to be GROUPED_SINGLE_NODE once that has been approved and added
    # Nested parser for the 'ngen_cal' action, which is very similar to the 'ngen' parser
    parser_ngen_cal = _create_ngen_based_exec_parser(subcommand_container=workflow_subparsers, parser_name='ngen_cal',
                                                     default_alloc_paradigm=AllocationParadigm.get_default_selection())

    # Calibration parser needs a few more calibration-specific items
    def positive_int(arg_val: str):
        try:
            arg_as_int = int(arg_val)
        except ValueError:
            raise argparse.ArgumentTypeError("Non-integer value '%s' provided when positive integer expected" % arg_val)
        if arg_as_int <= 0:
            raise argparse.ArgumentTypeError("Invalid value '%s': expected integer greater than 0" % arg_val)
        return arg_as_int

    def model_calibration_param(arg_val: str):
        split_arg = arg_val.split(',')
        try:
            if len(split_arg) != 4:
                raise RuntimeError
            # Support float args in any order by sorting, since min, max, and other/init will always be self-evident
            float_values = sorted([float(split_arg[i]) for i in [1, 2, 3]])
            # Return is (param, (min, max, init))
            return split_arg[0], (float_values[0], float_values[2], float_values[1])
        except:
            raise argparse.ArgumentTypeError("Invalid arg '%s'; format must be <str>,<float>,<float>,<float>" % arg_val)

    parser_ngen_cal.add_argument('--calibrated-param', dest='model_cal_params', type=model_calibration_param,
                                 nargs='+', metavar='PARAM_NAME,MIN_VAL,MAX_VAL,INIT_VAL',
                                 help='Description of parameters to calibrate, as comma delimited string')

    parser_ngen_cal.add_argument('--job-name', default=None, dest='job_name', help='Optional job name.')
    # TODO (later): add more choices once available
    parser_ngen_cal.add_argument('--strategy', default='estimation', dest='cal_strategy_type',
                                 choices=['estimation'], help='The ngen_cal calibration strategy.')
    # TODO (later): need to add other supported algorithms (there should be a few more now)
    parser_ngen_cal.add_argument('--algorithm', type=str, default='dds', dest='cal_strategy_algorithm',
                                 choices=['dds'], help='The ngen_cal parameter search algorithm.')
    parser_ngen_cal.add_argument('--objective-function', default='nnse', dest='cal_strategy_objective_func',
                                 choices=["kling_gupta", "nnse", "custom", "single_peak", "volume"],
                                 help='The ngen_cal objective function.')
    parser_ngen_cal.add_argument('--is-objective-func-minimized', type=bool, default=True,
                                 dest='is_objective_func_minimized',
                                 help='Whether the target of objective function is minimized or maximized.')
    parser_ngen_cal.add_argument('--iterations', type=positive_int, default=100, dest='iterations',
                                 help='The number of ngen_cal iterations.')
    # TODO (later): in the future, figure out how to best handle this kind of scenario
    #parser_ngen_cal.add_argument('--is-restart', action='store_true', dest='is_restart',
    #                             help='Whether this is restarting a previous job.')
    #ngen calibration strategies include
    #uniform: Each catchment shares the same parameter space, evaluates at one observable nexus
    #independet: Each catchment upstream of observable nexus gets its own permuated parameter space, evalutates at one observable nexus
    #explicit: only calibrates basins in the realization_config with a "calibration" definition and an observable nexus
    # TODO: add this kind of information to the help message
    parser_ngen_cal.add_argument('--model-strategy', default='uniform', dest='model_strategy',
                                 choices=["uniform", "independent", "explicit"],
                                 help='The model calibration strategy used by ngen_cal.')


def _handle_data_service_action_args(parent_subparsers_container):
    """
    Handle setup of arg parsing for 'data' command, which allows for various operations related to datasets.

    Parameters
    ----------
    parent_subparsers_container
        The top-level parent container for subparsers of various commands, including the 'data' command, to which
        some numbers of nested subparser containers and parsers will be added.
    """
    # A parser for the 'data' command itself, underneath the parent 'command' subparsers container
    command_parser = parent_subparsers_container.add_parser('dataset',
                                                            description="Perform various dataset-related actions.")

    # Subparser under the dataset command's parser for handling the different actions that might be done relating to a
    # dataset (e.g., creation or uploading of data)
    action_subparsers = command_parser.add_subparsers(dest='action')
    action_subparsers.required = True

    dataset_categories = [e for e in DataCategory]
    dataset_formats = [e for e in DataFormat]

    # Nested parser for the 'create' action, with required argument for dataset name, category, and format
    parser_create = action_subparsers.add_parser('create', description="Create a new dataset.")
    parser_create.add_argument('name', help='Specify the name of the dataset to create.')
    parser_create.add_argument('--paths', dest='upload_paths', type=Path, nargs='+',
                               help='Specify files/directories to upload.')
    parser_create.add_argument('--data-root', dest='data_root', type=Path,
                               help='Relative data root directory, used to adjust the names for uploaded items.')
    c_json_form = '{"variable": "<variable_name>", "begin": "<value>", "end": "<value>"}'
    d_json_form = '{"variable": "<variable_name>", "values": [<value>, ...]}'
    c_restrict_help_str = 'Specify continuous domain restriction as (simplified) serialized JSON - {}'
    d_restrict_help_str = 'Specify discrete domain restriction as (simplified) serialized JSON - {}'
    # TODO: need to test that this works as expected
    parser_create.add_argument('--continuous-restriction', type=lambda s: ContinuousRestriction(**json.loads(s)),
                               dest='continuous_restrictions', nargs='*', help=c_restrict_help_str.format(c_json_form))
    parser_create.add_argument('--discrete-restriction', type=lambda s: DiscreteRestriction(**json.loads(s)),
                               dest='discrete_restrictions', nargs='*', help=d_restrict_help_str.format(d_json_form))
    parser_create.add_argument('--format', dest='data_format', choices=dataset_formats, type=DataFormat.get_for_name,
                               metavar=f"{{{', '.join(f.name for f in dataset_formats)}}}", help='Specify dataset domain format.')
    parser_create.add_argument('--domain-json', dest='domain_file', type=Path, help='Deserialize the dataset domain from a file.')
    parser_create.add_argument('category', type=DataCategory.get_for_name, choices=dataset_categories,
                               metavar=f"{{{', '.join(c.name.lower() for c in dataset_categories)}", help='Specify dataset category.')

    # Nested parser for the 'delete' action, with required argument for dataset name
    parser_delete = action_subparsers.add_parser('delete', description="Delete a specified (entire) dataset.")
    parser_delete.add_argument('name', help='Specify the name of the dataset to delete.')

    # Nested parser for the 'upload' action, with required args for dataset name and files to upload
    parser_upload = action_subparsers.add_parser('upload', description="Upload local files to a dataset.")
    parser_upload.add_argument('--data-root', dest='data_root', type=Path,
                               help='Relative data root directory, used to adjust the names for uploaded items.')
    parser_upload.add_argument('dataset_name', help='Specify the name of the desired dataset.')
    parser_upload.add_argument('paths', type=Path, nargs='+', help='Specify files or directories to upload.')

    # Nested parser for the 'download' action, with required args for dataset name and files to upload
    parser_download = action_subparsers.add_parser('download', description="Download some or all items from a dataset.")
    parser_download.add_argument('--items', dest='item_names', nargs='+',
                                 help='Specify files/items within dataset to download.')
    parser_download.add_argument('dataset_name', help='Specify the name of the desired dataset.')
    parser_download.add_argument('dest_dir', type=Path, help='Specify local destination directory to save to.')

    # Nested parser for the 'list_datasets' action
    parser_list = action_subparsers.add_parser('list', description="List available datasets.")
    parser_list.add_argument('--category', dest='category', choices=dataset_categories, type=DataCategory.get_for_name,
                             metavar=f"{{{', '.join(c.name.lower() for c in dataset_categories)}", help='Specify the category of dataset to list')

    # Nested parser for the 'list_items' action
    parser_list = action_subparsers.add_parser('items', description="List items within a specified dataset.")
    parser_list.add_argument('dataset_name', help='Specify the dataset for which to list items')


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
    job_command_subparsers = command_parser.add_subparsers(dest='job_command')
    job_command_subparsers.required = True

    # Nested parser for the 'list' action
    parser_list_jobs = job_command_subparsers.add_parser('list')
    parser_list_jobs.add_argument('--active', dest='jobs_list_active_only', action='store_true',
                                  help='List only jobs with "active" status')

    # Nested parser for the 'info' action
    parser_job_info = job_command_subparsers.add_parser('info')
    parser_job_info.add_argument('job_id', help='The id of the job for which to retrieve job state info')

    # Nested parser for the 'release' action
    parser_job_release = job_command_subparsers.add_parser('release')
    parser_job_release.add_argument('job_id', help='The id of the job for which to release resources')

    # Nested parser for the 'status' action
    parser_job_status = job_command_subparsers.add_parser('status')
    parser_job_status.add_argument('job_id', help='The id of the job for which to retrieve status')

    # Nested parser for the 'stop' action
    parser_job_stop = job_command_subparsers.add_parser('stop')
    parser_job_stop.add_argument('job_id', help='The id of the job to stop')


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='dmod.client')
    parser.add_argument('--client-config',
                        help='Set path to client configuration file',
                        type=Path,
                        dest='client_config',
                        default=Path('.dmod_client_config.json'))
    parser.add_argument('--bypass-request-service', '-b', dest='bypass_reqsrv', action='store_true', default=False,
                        help='Attempt to connect directly to the applicable service')
    parser.add_argument('--remote-debug', '-D', dest='remote_debug', action='store_true', default=False,
                        help='Activate remote debugging, according to loaded client configuration.')
    # Top-level subparsers container, splitting off a variety of handled commands for different behavior
    # e.g., 'dataset' to do things related to datasets, like creation
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    # Nested command parsers handling actions of dataset command
    _handle_data_service_action_args(parent_subparsers_container=subparsers)
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


def execute_dataset_command(args, client: DmodClient):
    async_loop = get_or_create_eventloop()
    try:
        result = async_loop.run_until_complete(client.data_service_action(**(vars(args))))
        print(result)
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    except NotImplementedError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print("ERROR: Encountered {} - {}".format(e.__class__.__name__, str(e)))
        sys.exit(1)


def execute_config_command(parsed_args, client: DmodClient):
    if parsed_args.action == 'print':
        client.print_config()
    elif parsed_args.action == 'validate':
        client.validate_config()
    else:
        raise RuntimeError("Bad client command action '{}'".format(parsed_args.action))


def execute_job_command(args, client: DmodClient):
    async_loop = get_or_create_eventloop()
    try:
        result = async_loop.run_until_complete(client.job_command(**(vars(args))))
        print(result)
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    except NotImplementedError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print("ERROR: Encountered {} - {}".format(e.__class__.__name__, str(e)))
        sys.exit(1)


def execute_workflow_command(args, client: DmodClient):
    async_loop = get_or_create_eventloop()
    try:
        result = async_loop.run_until_complete(client.execute_job(**(vars(args))))
        print(result)
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"Encounted {e.__class__.__name__}: {str(e)}")
        sys.exit(1)

# TODO: (later) add something to TransportLayerClient to check if it supports multiplexing


def _load_debugger_and_settrace(debug_cfg):
    """
    Helper function to append the path of Pycharm debug egg to system path, import it, and set the remote debug trace.

    Parameters
    ----------
    debug_cfg

    Returns
    -------

    """
    if debug_cfg is None:
        return False
    import sys
    sys.path.append(str(debug_cfg.egg_path))
    import pydevd_pycharm
    try:
        pydevd_pycharm.settrace(debug_cfg.debug_host, port=debug_cfg.port, stdoutToServer=True, stderrToServer=True)
        return True
    except Exception as error:
        print(f'Warning: could not set debugging trace to {debug_cfg.debug_host} on {debug_cfg.port!s} due to'
              f' {error.__class__.__name__} - {error!s}')
        return False


def main():
    args = _handle_args()
    client_config_path = find_client_config() if args.client_config is None else Path(args.client_config)
    if client_config_path is None:
        print("ERROR: Could not find any suitable DMOD CLI client configuration file")
        sys.exit(1)

    try:

        client_config = ClientConfig.parse_file(client_config_path)
        if args.remote_debug and client_config.pycharm_debug_config is not None:
            _load_debugger_and_settrace(debug_cfg=client_config.pycharm_debug_config)
        elif args.remote_debug:
            print("ERROR: received arg to activate remote debugging, but client config lacks debugging parameters.")
            sys.exit(1)

        client = DmodClient(client_config=client_config, bypass_request_service=args.bypass_reqsrv)

        if args.command == 'config':
            execute_config_command(args, client)
        elif args.command == 'dataset':
            execute_dataset_command(args, client)
        elif args.command == 'exec':
            execute_workflow_command(args, client)
        elif args.command == 'jobs':
            execute_job_command(args, client)
        else:
            raise ValueError("Unsupported command {}".format(args.command))

    except Exception as error:
        print(f"ERROR: {error!s}")
        sys.exit(1)


if __name__ == '__main__':
    main()
