import argparse
import flask
import json
from dmod.modeldata import SubsetDefinition, SubsetHandler
from pathlib import Path
from typing import Optional
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
    parser.prog = package_name
    return parser.parse_args()


def _cli_output_subset(handler, cat_ids, is_simple, format_json, file_name: Optional[Path] = None) -> bool:
    """
    Perform CLI operations to output a subset, either to standard out or a file.

    Parameters
    ----------
    handler: SubsetHandler
        The previously created handler object doing the subsetting.
    cat_ids: list
        A list of string catchment ids from which the subset will be created.
    is_simple: bool
        Whether a simple subset is created (when ``False``, and upstream type subset will be created).
    format_json: bool
        Whether the output should have pretty JSON formatting.
    file_name: Optional[str]
        Optional file in which to write the output; when ``None``, output is printed.

    Returns
    -------
    bool
        Whether the CLI operation was completed successfully.
    """
    if not cat_ids:
        print("Cannot run CLI operation without specifying at least one catchment id (see --help for details).")
        return False
    subset = handler.get_subset_for(cat_ids) if is_simple else handler.get_upstream_subset(cat_ids)
    json_output_str = subset.to_json()
    if format_json:
        json_output_str = json.dumps(json.loads(json_output_str), indent=4, sort_keys=True)
    if file_name:
        file_name.write_text(json_output_str)
    else:
        print(json_output_str)
    return True


# TODO: incorporate a little more tightly with the modeldata package and the Hydrofabric and SubsetDefinition types
def _cli_divide_hydrofabric(files_dir: Path, catchment_file: Path, nexus_file: Path, partition_file_arg: str) -> bool:
    """
    Subdivide a GeoJSON hydrofabric according to a supplied partitions config, writing to new partition-specific files.

    Function reads partition config from the supplied file location relative to either the ``files_dir`` or the current
    working directory (it returns ``False`` immediately if there it fails to find a file there).  Next it reads in the
    full hydrofabric files into catchment and nexus ::class:`GeoDataFrame` objects.  It then iterates through each
    partition, extracting the subsets of catchments and nexuses of the each partition from the full hydrofabric and
    writing those subsets to files.

    The partition-specific output files are written in to same directory as the analogous full hydrofabric file.  Their
    names are based on partition index and the name of the full hydrofabric file, with a dot (``.``) and the index
    being added as a suffix to the latter to form the name.  E.g. for a ``catchment_data.geojson`` file, output files
    will have names like ``catchment_data.geojson.0``, ``catchment_data.geojson.1``, etc., with these being created in
    the same directory as the original ``catchment_data.geojson``.

    Parameters
    ----------
    files_dir: Path
        The parent directory for hydrofabric data files.
    catchment_file: Path
        The path to the hydrofabric catchment data file (already including the parent directory component).
    nexus_file: Path
        The path to the hydrofabric nexus data file (already including the parent directory component).
    partition_file_arg: str
        The string form of the relative path to the partition config file, relative either to ``files_dir`` or the
        current working directory.

    Returns
    -------
    bool
        Whether the CLI operation was completed successfully.
    """
    import geopandas as gpd

    # Look for partition file either relative to working directory or files directory
    partitions_file = Path.cwd() / partition_file_arg
    if not partitions_file.exists():
        partitions_file = files_dir / partition_file_arg
    # If it doesn't exist in either of these two places, then thats a problem
    if not partitions_file.exists():
        print("Error: cannot find partition file {} from either working directory or given files directory {}".format(
            partition_file_arg, files_dir))
        return False

    with partitions_file.open() as f:
        partition_config_json = json.load(f)

    hydrofabric_catchments = gpd.read_file(str(catchment_file))
    hydrofabric_catchments.set_index('id', inplace=True)

    hydrofabric_nexuses = gpd.read_file(str(nexus_file))
    hydrofabric_nexuses.set_index('id', inplace=True)

    for i in range(len(partition_config_json['partitions'])):
        partition_cat_ids = partition_config_json['partitions'][i]['cat-ids']
        partition_catchments: gpd.GeoDataFrame = hydrofabric_catchments.loc[partition_cat_ids]
        partition_catchment_file = catchment_file.parent / '{}.{}'.format(catchment_file.name, i)
        partition_catchments.to_file(str(partition_catchment_file), driver='GeoJSON')

        partition_nexus_ids = partition_config_json['partitions'][i]['nex-ids']
        partition_nexuses = hydrofabric_nexuses.loc[partition_nexus_ids]
        partition_nexuses_file = nexus_file.parent / '{}.{}'.format(nexus_file.name, i)
        partition_nexuses.to_file(str(partition_nexuses_file), driver='GeoJSON')
    return True


def main():
    global subset_handler
    args = _handle_args()

    # TODO: put warning in about not trying multiple CLI operations at once

    # TODO: try to split off functionality so that Flask stuff (though declared globally) isn't started for CLI ops

    if not args.files_directory.is_dir():
        print("Error: given param '{}' for files directory is not an existing directory".format(args.files_directory))

    catchment_geojson = args.files_directory.joinpath(args.catchment_data_file)
    nexus_geojson = args.files_directory.joinpath(args.nexus_data_file)
    crosswalk_json = args.files_directory.joinpath(args.crosswalk_file)

    subset_handler = SubsetHandler.factory_create_from_geojson(catchment_data=catchment_geojson,
                                                               nexus_data=nexus_geojson,
                                                               cross_walk=crosswalk_json)

    if args.partition_file:
        result = _cli_divide_hydrofabric(args.files_directory, catchment_geojson, nexus_geojson, args.partition_file)
    elif args.do_simple_subset or args.do_upstream_subset:
        result = _cli_output_subset(subset_handler, args.cat_ids, args.do_simple_subset, args.do_formatting, args.output_file)
    else:
        app.run(host=args.host, port=args.port)
        result = True

    if not result:
        exit(1)


if __name__ == '__main__':
    main()
