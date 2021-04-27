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


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--catchment-data-file',
                        '-c',
                        help='Set the path (relative to files_directory) to the hydrofabric catchment data file',
                        dest='catchment_data_file',
                        default='catchment_data.geojson')
    parser.add_argument('--nexus-data-file',
                        '-n',
                        help='Set the path (relative to files_directory to the hydrofabric nexus data file',
                        dest='nexus_data_file',
                        default='nexus_data.geojson')
    parser.add_argument('--crosswalk-file',
                        '-x',
                        help='Set the path (relative to files_directory to the hydrofabric crosswalk file',
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
    # For now, these are not needed, as subset are simple type and thus can always be read directly from hydrofabric
    # Keep though in case that changes (i.e., includes data)
    # parser.add_argument('--redis-host',
    #                     help='Set the host value for making Redis connections',
    #                     dest='redis_host',
    #                     default=None)
    # parser.add_argument('--redis-pass',
    #                     help='Set the password value for making Redis connections',
    #                     dest='redis_pass',
    #                     default=None)
    # parser.add_argument('--redis-port',
    #                     help='Set the port value for making Redis connections',
    #                     dest='redis_port',
    #                     default=None)
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
    files_dir = args.files_directory

    catchment_geojson = _process_path(files_dir, args.catchment_data_file)
    nexus_geojson = _process_path(files_dir, args.nexus_data_file)
    crosswalk_json = _process_path(files_dir, args.crosswalk_file)

    subset_handler = SubsetHandler.factory_create_from_geojson(catchment_data=catchment_geojson,
                                                               nexus_data=nexus_geojson,
                                                               cross_walk=crosswalk_json)
    app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
