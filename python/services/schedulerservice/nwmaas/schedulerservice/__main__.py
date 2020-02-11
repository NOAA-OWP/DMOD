import argparse
from pathlib import Path
from . import name as package_name
from nwmaas.scheduler import Scheduler
from .service import SchedulerHandler


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--images-and-domains-yaml',
                        help='Set the YAML file for the images and domains configuration',
                        dest='images_and_domains_yaml',
                        default='image_and_domain.list')
    parser.add_argument('--port',
                        help='Set the appropriate listening port value',
                        dest='port',
                        type=int,
                        default=3013)
    # TODO: improve to be more intelligent about the argument to accept and making it a Path (argparse Action perhaps)
    parser.add_argument('--ssl-dir',
                        #help='Change the base directory when using SSL certificate and key files with default names',
                        help='Set the ssl directory for scheduler certs',
                        dest='ssl_dir',
                        default='/ssl/scheduler/')
    parser.prog = package_name
    return parser.parse_args()


def main():
    args = _handle_args()

    # TODO: look at handling if the value in args.images_and_domains_yaml doesn't correspond to an actual file
    # instantiate the scheduler
    scheduler = Scheduler(images_and_domains_yaml=args.images_and_domains_yaml)

    # build resource database
    #scheduler.create_resources()

    #Instansite the handle_job_request
    handler = SchedulerHandler(scheduler, ssl_dir=Path(args.ssl_dir), port=args.port)
    #keynamehelper.set_prefix("stack0")
    handler.run()


if __name__ == '__main__':
    main()
