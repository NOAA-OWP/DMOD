import argparse
from pathlib import Path
from . import name as package_name
from .scheduler import Scheduler
from .service import SchedulerHandler


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
                        default='/nwm/scheduler/ssl/scheduler/')
    parser.prog = package_name
    return parser.parse_args()


def main():
    args = _handle_args()

    # instantiate the scheduler
    scheduler = Scheduler()

    # initialize redis client
    scheduler.clean_redisKeys()

    # build resource database
    #scheduler.create_resources()

    #Instansite the handle_job_request
    handler = SchedulerHandler(scheduler, ssl_dir=Path(args.ssl_dir), port=args.port)
    #keynamehelper.set_prefix("stack0")
    handler.run()


if __name__ == '__main__':
    main()
