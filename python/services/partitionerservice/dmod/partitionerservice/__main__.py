import argparse
from . import name as package_name
from . import PartitionerHandler


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--listen-port',
                        '-l',
                        help='Port that the service listens on for incoming websocket connections',
                        dest='listen_port',
                        default=3014)
    parser.add_argument('--partitioner-image',
                        '-i',
                        help='Name of the constructed Docker image in which the partitioner executable is run',
                        dest='partitioner_image',
                        default='ngen-partitioner')
    parser.add_argument('--image-tag',
                        '-t',
                        help='Image tag/version to use for partitioner image',
                        dest='image_tag',
                        default='latest')
    parser.add_argument('--public-registry',
                        '-p',
                        help='Use public Docker image registry instead of private',
                        dest='use_public',
                        action='store_true')
    parser.add_argument('--docker-registry',
                        '-r',
                        help='Private Docker image registry to use',
                        dest='docker_registry',
                        default='127.0.0.1:5000')
    parser.add_argument('--docker-volume',
                        '-v',
                        help='Name of the Docker volume used for mounting the partitioner inputs and outputs.',
                        dest='docker_volume',
                        default='partition_vol')
    parser.add_argument('--volume-storage-dir',
                        '-v',
                        help='Name of the Docker volume used for mounting the partitioner inputs and outputs.',
                        dest='volume_storage_dir',
                        default='partition_data')
    parser.prog = package_name
    return parser.parse_args()


def _process_path(files_dir_arg: str, file_name: str):
    if not files_dir_arg:
        return file_name
    else:
        return files_dir_arg + "/" + file_name


def main():
    args = _handle_args()
    image = args.partitioner_image + ":" + args.image_tag
    if not args.use_public:
        image = args.docker_registry + "/" + image
    handler = PartitionerHandler(listen_port=int(args.listen_port), image_name=image,
                                 data_volume_name=args.docker_volume, volume_storage_dir=args.volume_storage_dir)
    handler.run()


if __name__ == '__main__':
    main()
