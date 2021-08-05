import argparse
import flask
import json
from dmod.modeldata import SubsetDefinition, SubsetHandler
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
                        dest='files_directory',
                        default='')
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
                        help="Run CLI operation to get upstream subset that starts from provided catchments.",
                        dest='do_upstream_subset',
                        action='store_true')
    parser.add_argument('--subset',
                        '-S',
                        help="Run CLI operation to get basic subset of provided catchments and their downstream nexus.",
                        dest='do_simple_subset',
                        action='store_true')
    parser.add_argument('--output-file',
                        '-o',
                        help='Write CLI operation output to given file (in working directory) instead of printing.',
                        dest='output_file',
                        default='')
    parser.add_argument('--catchment-ids',
                        '-C',
                        help="Provide one or more catchment ids to include when running CLI operation.",
                        nargs='+',
                        dest='cat_ids')
    parser.add_argument('--format-output',
                        '-F',
                        help="When running CLI operation, use pretty formatting of the printed or written output.",
                        action="store_true",
                        dest='do_formatting')
    parser.prog = package_name
    return parser.parse_args()


def _process_path(files_dir_arg: str, file_name: str):
    if not files_dir_arg:
        return file_name
    else:
        return files_dir_arg + "/" + file_name


def main():
    global subset_handler
    args = _handle_args()

    is_do_simple = args.do_simple_subset
    is_do_upstream = args.do_upstream_subset
    is_cli_only = is_do_simple or is_do_upstream

    # TODO: put warning in about not trying both simple and upstream at once

    files_dir = args.files_directory

    # TODO: try to split off functionality so that Flask stuff (though declared globally) isn't started for CLI ops

    catchment_geojson = _process_path(files_dir, args.catchment_data_file)
    nexus_geojson = _process_path(files_dir, args.nexus_data_file)
    crosswalk_json = _process_path(files_dir, args.crosswalk_file)

    subset_handler = SubsetHandler.factory_create_from_geojson(catchment_data=catchment_geojson,
                                                               nexus_data=nexus_geojson,
                                                               cross_walk=crosswalk_json)

    if is_cli_only and len(args.cat_ids) == 0:
        print("Cannot run CLI operation without specifying at least one catchment id (see --help for details).")
        exit(1)
    elif is_cli_only:
        if is_do_upstream:
            subset = subset_handler.get_upstream_subset(args.cat_ids)
        else:
            subset = subset_handler.get_subset_for(args.cat_ids)
        json_output_str = subset.to_json()
        if args.do_formatting:
            json_output_str = json.dumps(json.loads(json_output_str), indent=4, sort_keys=True)
        # If an output file was designated, write the output there
        if len(args.output_file) > 0:
            from pathlib import Path
            Path('.').joinpath(args.output_file).write_text(json_output_str)
        else:
            print(json_output_str)
    else:
        app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
