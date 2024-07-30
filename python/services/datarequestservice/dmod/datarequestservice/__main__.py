import argparse
import sys
import flask
import json
from dmod.modeldata.datarequest import DataRequestHandler, DataRequestReader
from . import name as package_name

app = flask.Flask(__name__)
app.config["DEBUG"] = True

request_handler: DataRequestHandler = None


@app.route('/', methods=['GET'])
def home():
    return "<h1>DMoD Data Request API</h1><p>This site is a prototype API for validating a data request against a stored catalog .</p>"


# A route to verify a request is a valid
@app.route('/datarequest/valid', methods=['POST'])
def is_request_valid():

    request = DataRequestReader(json.loads(flask.request.data)).request
    # Expect JSON with data-source start-date stop-date and variables
    is_recognized = request_handler.is_valid(request)
    return flask.jsonify({'valid': is_recognized})


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--catalog-data-file',
                        '-c',
                        help='Set the path (relative to files_directory) to the data catalog file file',
                        dest='catalog_file',
                        default='catalog.json')
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

    parser.prog = package_name
    return parser.parse_args()


def main():
    args = _handle_args()

    if not args.files_directory.is_dir():
        print("Error: given param '{}' for files directory is not an existing directory".format(args.files_directory))

    catalog_json = args.files_directory.joinpath(args.catalog_file)

    global request_handler
    request_handler = DataRequestHandler.factory_create_from_geojson(catchment_data=catalog_json)

    app.run(host=args.host, port=args.port)
    result = True

    if not result:
        sys.exit(1)


if __name__ == '__main__':
    main()
