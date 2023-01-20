import argparse
import flask
import json
from dmod.modeldata import SubsetDefinition
from dmod.modeldata.subset.subset_handler import GeoJsonBackedSubsetHandler
from pathlib import Path
from typing import Dict
from .cli import Cli
from . import name as package_name

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

app = flask.Flask(__name__)
app.config["DEBUG"] = True

subset_handlers: Dict[str, GeoJsonBackedSubsetHandler] = dict()


@app.route('/', methods=['GET'])
def home():
    return "<h1>DMoD Subset API</h1><p>This site is a prototype API for generating and retrieving model subsets.</p>"


# A route to verify a catchment id is valid (i.e., exists in the known hydrofabric
@app.route('/subset/cat_id_valid', methods=['POST'])
def is_catchment_id_valid():
    record = json.loads(flask.request.data)
    # Expect JSON with 'id' key, 'fabric_name' key for the hydrofabric, and then a single string id
    subset_handler = subset_handlers[record['fabric_name']]
    is_recognized = subset_handler.is_catchment_recognized(record['id'])
    return flask.jsonify({'catchment_id': record['id'], 'valid': is_recognized})


# A route to get a subset for a particular set of one or more catchment ids
@app.route('/subset/for_cat_id', methods=['POST'])
def get_subset_for_catchment_id():
    record = json.loads(flask.request.data)
    subset_handler = subset_handlers[record['fabric_name']]
    # Expect JSON with 'ids' key, 'fabric_name' key for the hydrofabric, and then a list of ids
    subset = subset_handler.get_subset_for(record['ids'])
    return flask.jsonify(subset.to_dict())


@app.route('/subset/bounds', methods=['POST'])
def get_subset_hydrofabric_for_bounds():
    # min_x, min_y, max_x, max_y
    record = json.loads(flask.request.data)
    subset_handler = subset_handlers[record['fabric_name']]
    features = subset_handler.get_geojson_for_bounds(record['feature_type'], record['min_x'], record['min_y'],
                                                     record['max_x'], record['max_y'])
    return flask.jsonify(features)


# A route to get a subset the goes upstream from one or more catchments specified by their ids
@app.route('/subset/upstream', methods=['POST'])
def get_upstream_subset():
    record = json.loads(flask.request.data)
    # Expect JSON with 'ids' key, 'fabric_name' key for the hydrofabric, and then a list of ids
    subset_handler = subset_handlers[record['fabric_name']]
    # Potentially a limit key can also be provided
    limit = None
    if 'limit' in record:
        jl = record['limit']
        if isinstance(jl, str) and jl.isdigit():
            jl = int(jl)
        if isinstance(jl, int) and jl > 0:
            limit = jl
    subset = subset_handler.get_upstream_subset(record['ids'], link_limit=limit)
    return flask.jsonify(subset.to_dict())


def _validate_subset(subset_handler, json_data):
    subset = SubsetDefinition.factory_init_from_deserialized_json(json_data)
    if subset is None:
        return flask.jsonify({'valid': False, 'reason': 'Could not deserialize to subset definition object'})
    is_valid, invalid_reason = subset_handler.validate(subset)
    return flask.jsonify({'valid': is_valid, 'reason': '' if is_valid else invalid_reason})


@app.route('/subset/validate', methods=['POST'])
def validate_subset():
    record = json.loads(flask.request.data)
    return _validate_subset(subset_handler=subset_handlers[record['fabric_name']],
                            json_data=record['subset'] if 'subset' in record else record)


@app.route('/subset/validate_file', methods=['POST'])
def validate_subset_file():
    uploaded_file = flask.request.files['file']
    record = json.loads(flask.request.data)
    if uploaded_file.filename == '':
        return flask.jsonify({'valid': False, 'reason': 'Invalid file or filename provided to validation routine'})
    return _validate_subset(subset_handler=subset_handlers[record['fabric_name']], json_data=json.load(uploaded_file))


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--catchment-data-file',
                        '-c',
                        help='Set the path (relative to files_directory) to the hydrofabric catchment data file',
                        dest='catchment_data_file',
                        default='catchment_data.geojson')
    parser.add_argument('--nexus-data-file',
                        '-n',
                        help='Set the path (relative to files_directory) to the hydrofabric nexus data file',
                        dest='nexus_data_file',
                        default='nexus_data.geojson')
    parser.add_argument('--crosswalk-file',
                        '-x',
                        help='Set the path (relative to files_directory) to the hydrofabric crosswalk file',
                        dest='crosswalk_file',
                        default='crosswalk.json')
    parser.add_argument('--files-directory',
                        '-d',
                        help='Specify base/prefix directory for hydrofabric files',
                        type=Path,
                        dest='files_directory',
                        default=Path.cwd())
    parser.add_argument('--port',
                        '-p',
                        help='Set the port on which the API is hosted',
                        dest='port',
                        default=5000)
    parser.add_argument('--host',
                        '-H',
                        help='Set the host on which the API is hosted',
                        dest='host',
                        default='0.0.0.0')
    parser.add_argument('--upstream',
                        '-U',
                        help="Run CLI operation to print upstream subset definition starting from provided catchments.",
                        dest='do_upstream_subset',
                        action='store_true')
    parser.add_argument('--subset',
                        '-S',
                        help="Run CLI operation to print basic subset definition containing the provided catchments and each's downstream nexus.",
                        dest='do_simple_subset',
                        action='store_true')
    parser.add_argument('--output-file',
                        '-o',
                        help='Instead of printing, output any subset definition from a run CLI operation to this file.',
                        type=Path,
                        dest='output_file')
    parser.add_argument('--catchment-ids',
                        '-C',
                        help="Provide one or more catchment ids to include when running CLI operation.",
                        nargs='+',
                        dest='cat_ids')
    parser.add_argument('--format-output',
                        '-F',
                        help="When running CLI operation, use pretty formatting of printed or written JSON.",
                        action="store_true",
                        dest='do_formatting')
    parser.add_argument('--partition-file',
                        '-P',
                        help="When given, run CLI operation to create subdivided hydrofabric files according to partitions configured in this file.",
                        dest='partition_file')
    parser.add_argument('--partition-index',
                        '-I',
                        help="When running CLI operation to create subdivided hydrofabric, only write files for this partition index.",
                        dest='partition_index')
    parser.add_argument('--pycharm-remote-debug',
                        help='Activate Pycharm remote debugging support',
                        dest='pycharm_debug',
                        action='store_true')
    parser.add_argument('--pycharm-remote-debug-egg',
                        help='Set path to .egg file for Python remote debugger util',
                        dest='remote_debug_egg_path',
                        default='/pydevd-pycharm.egg')
    parser.add_argument('--remote-debug-host',
                        help='Set remote debug host to connect back to debugger',
                        dest='remote_debug_host',
                        default='host.docker.internal')
    parser.add_argument('--remote-debug-port',
                        help='Set remote debug port to connect back to debugger',
                        dest='remote_debug_port',
                        type=int,
                        default=55874)
    parser.prog = package_name
    return parser.parse_args()


def exec_cli_op(cli, args) -> bool:
    if args.partition_file:
        return cli.divide_hydrofabric(args.partition_index)
    else:
        return cli.output_subset(cat_ids=args.cat_ids, is_simple=args.do_simple_subset, format_json=args.do_formatting,
                                 output_file_name=args.output_file)


def _is_hydrofabric_dir(directory: Path, cat_file_name: str, nexus_file_name: str) -> bool:
    catchment_data_path = directory.joinpath(cat_file_name)
    nexus_data_path = directory.joinpath(nexus_file_name)
    return directory.is_dir() and catchment_data_path.is_file() and nexus_data_path.is_file()


def _determine_xwalk(hy_dir: Path, first_name: str) -> Path:
    # Do some extra checking for crosswalk for alternative path/suffix
    # TODO: this needs to be improved somehow
    crosswalk_path: Path = hy_dir.joinpath(first_name)
    if crosswalk_path.exists():
        return crosswalk_path
    else:
        alt_xwalk = crosswalk_path.with_suffix('.csv')
        if not alt_xwalk.exists():
            msg = "Required crosswalk file to load hydrofabric not found at {} or {}"
            logging.error(msg.format(crosswalk_path, alt_xwalk))
            raise RuntimeError(msg.format(crosswalk_path, alt_xwalk))
        else:
            return alt_xwalk


def _load_subset_handler(hy_dir: Path, catchment_file_name: str, nexus_file_name: str, crosswalk_name: str) -> GeoJsonBackedSubsetHandler:
    # TODO: add more intelligence to file base names and detection
    #logging.info("Loading hydrofabric files from {}".format(args.files_directory))
    logging.info("Loading hydrofabric files from {}".format(hy_dir))

    #catchment_data_path = args.files_directory.joinpath(args.catchment_data_file)
    #nexus_data_path = args.files_directory.joinpath(args.nexus_data_file)
    catchment_data_path = hy_dir.joinpath(catchment_file_name)
    nexus_data_path = hy_dir.joinpath(nexus_file_name)

    try:
        crosswalk_path: Path = _determine_xwalk(hy_dir=hy_dir, first_name=crosswalk_name)
    except RuntimeError as e:
        msg = "Subset service start failed: {}".format(str(e))
        logging.error(msg)
        raise RuntimeError(msg)

    subset_handler = GeoJsonBackedSubsetHandler(catchment_data=catchment_data_path, nexus_data=nexus_data_path,
                                                cross_walk=crosswalk_path)
    logging.info("{} hydrofabric loaded into subset handler".format(hy_dir.name))
    return subset_handler


def main():
    global subset_handlers
    args = _handle_args()

    if args.pycharm_debug:
        logging.info("Preparing remote debugging connection for subset service.")
        if args.remote_debug_egg_path == '':
            print('Error: set to debug with Pycharm, but no path to remote debugger egg file provided')
            exit(1)
        if not Path(args.remote_debug_egg_path).exists():
            print('Error: no file at given path to remote debugger egg file "{}"'.format(args.remote_debug_egg_path))
            exit(1)
        import sys
        sys.path.append(args.remote_debug_egg_path)
        import pydevd_pycharm
        try:
            pydevd_pycharm.settrace(args.remote_debug_host, port=args.remote_debug_port, stdoutToServer=True,
                                    stderrToServer=True)
        except Exception as error:
            msg = 'Warning: could not set debugging trace to {} on {} due to {} - {}'
            print(msg.format(args.remote_debug_host, args.remote_debug_port, error.__class__.__name__, str(error)))
    else:
        logging.info("Skipping subset service remote debugging setup.")

    # TODO: put warning in about not trying multiple CLI operations at once

    # TODO: try to split off functionality so that Flask stuff (though declared globally) isn't started for CLI ops

    if not args.files_directory.is_dir():
        logging.error("Given param '{}' for files directory is not an existing directory".format(args.files_directory))

    running_cli = args.partition_file or args.do_simple_subset or args.do_upstream_subset

    subdirs = [d for d in args.files_directory.glob('*') if d.is_dir()]

    if len(subdirs) == 0 and _is_hydrofabric_dir(directory=args.files_directory, cat_file_name=args.catchment_data_file,
                                                 nexus_file_name=args.nexus_data_file):
        sub_handler = _load_subset_handler(hy_dir=args.files_directory, catchment_file_name=args.catchment_data_file,
                                           nexus_file_name=args.nexus_data_file, crosswalk_name=args.crosswalk_file)
        subset_handlers[args.files_directory.name] = sub_handler

        if running_cli:
            cli = Cli(catchment_geojson=args.files_directory.joinpath(args.catchment_data_file),
                      nexus_geojson=args.files_directory.joinpath(args.catchment_data_file),
                      crosswalk_json=_determine_xwalk(hy_dir=args.files_directory, first_name=args.crosswalk_file),
                      partition_file_str=args.partition_file, subset_handler=sub_handler)
        else:
            cli = None
    else:
        cli = None
        for hy_dir in subdirs:
            if _is_hydrofabric_dir(hy_dir, args.catchment_data_file, args.nexus_data_file):
                subset_handlers[hy_dir.name] = _load_subset_handler(hy_dir=hy_dir,
                                                                    catchment_file_name=args.catchment_data_file,
                                                                    nexus_file_name=args.nexus_data_file,
                                                                    crosswalk_name=args.crosswalk_file)
            else:
                logging.info("Skipping subdirectory {} without hydrofabric data files from".format(hy_dir))

    if running_cli and cli is None:
        logging.error('Cannot run subset CLI functionality without valid directory containing a single hydrofabric')
        exit(1)
    elif running_cli and cli is not None:
        result = exec_cli_op(cli, args)
    else:
        logging.info("Starting app API service on port {}".format(args.port))
        app.run(host=args.host, port=args.port)
        result = True

    if not result:
        exit(1)


if __name__ == '__main__':
    main()
