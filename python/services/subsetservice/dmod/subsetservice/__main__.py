import argparse
import sys
import flask
import json
from dmod.modeldata import SubsetDefinition, SubsetHandler
from pathlib import Path
from typing import Optional
from .cli import Cli
from . import name as package_name

app = flask.Flask(__name__)
app.config["DEBUG"] = True

subset_handler: SubsetHandler = None


@app.route('/', methods=['GET'])
def home():
    return "<h1>DMoD Subset API</h1><p>This site is a prototype API for generating and retrieving model subsets.</p>"


# A route to verify a catchment id is valid (i.e., exists in the known hydrofabric
@app.route('/subset/cat_id_valid', methods=['POST'])
def is_catchment_id_valid():
    record = json.loads(flask.request.data)
    # Expect JSON with 'id' key and then a single string id
    is_recognized = subset_handler.is_catchment_recognized(record['id'])
    return flask.jsonify({'catchment_id': record['id'], 'valid': is_recognized})


# A route to get a subset for a particular set of one or more catchment ids
@app.route('/subset/for_cat_id', methods=['POST'])
def get_subset_for_catchment_id():
    record = json.loads(flask.request.data)
    # Expect JSON with 'ids' key and then a list of ids
    subset = subset_handler.get_subset_for(record['ids'])
    return flask.jsonify(subset.to_dict())


# A route to get a subset the goes upstream from one or more catchments specified by their ids
@app.route('/subset/upstream', methods=['POST'])
def get_upstream_subset():
    record = json.loads(flask.request.data)
    # Expect JSON with 'ids' key and then a list of ids
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


def _validate_subset(json_data):
    subset = SubsetDefinition.factory_init_from_deserialized_json(json_data)
    if subset is None:
        return flask.jsonify({'valid': False, 'reason': 'Could not deserialize to subset definition object'})
    is_valid, invalid_reason = subset_handler.validate(subset)
    return flask.jsonify({'valid': is_valid, 'reason': '' if is_valid else invalid_reason})


@app.route('/subset/validate', methods=['POST'])
def validate_subset():
    record = json.loads(flask.request.data)
    return _validate_subset(json_data=record['subset'] if 'subset' in record else record)


@app.route('/subset/validate_file', methods=['POST'])
def validate_subset_file():
    uploaded_file = flask.request.files['file']
    if uploaded_file.filename == '':
        return flask.jsonify({'valid': False, 'reason': 'Invalid file or filename provided to validation routine'})
    return _validate_subset(json_data=json.load(uploaded_file))


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
    parser.prog = package_name
    return parser.parse_args()


def exec_cli_op(cli, args) -> bool:
    if args.partition_file:
        return cli.divide_hydrofabric(args.partition_index)
    else:
        return cli.output_subset(cat_ids=args.cat_ids, is_simple=args.do_simple_subset, format_json=args.do_formatting,
                                 output_file_name=args.output_file)


def main():
    global subset_handler
    args = _handle_args()

    # TODO: put warning in about not trying multiple CLI operations at once

    # TODO: try to split off functionality so that Flask stuff (though declared globally) isn't started for CLI ops

    if not args.files_directory.is_dir():
        print("Error: given param '{}' for files directory is not an existing directory".format(args.files_directory))

    catchment_data_path = args.files_directory.joinpath(args.catchment_data_file)
    nexus_data_path = args.files_directory.joinpath(args.nexus_data_file)
    crosswalk_path = args.files_directory.joinpath(args.crosswalk_file)

    subset_handler = SubsetHandler.factory_create_from_geojson(catchment_data=catchment_data_path,
                                                               nexus_data=nexus_data_path,
                                                               cross_walk=crosswalk_path)

    if args.partition_file or args.do_simple_subset or args.do_upstream_subset:
        cli = Cli(catchment_geojson=catchment_data_path, nexus_geojson=nexus_data_path, crosswalk_json=crosswalk_path,
                  partition_file_str=args.partition_file, subset_handler=subset_handler)
        result = exec_cli_op(cli, args)

    else:
        app.run(host=args.host, port=args.port)
        result = True

    if not result:
        sys.exit(1)


if __name__ == '__main__':
    main()
