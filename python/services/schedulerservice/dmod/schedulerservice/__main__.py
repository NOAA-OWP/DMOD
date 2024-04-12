import argparse
import sys
import yaml
from os import getenv
from pathlib import Path
from . import name as package_name
from .service import SchedulerHandler
from dmod.scheduler import Launcher, RedisManager, Resource
from dmod.scheduler.job import JobManagerFactory, JobManager

def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--images-and-domains-yaml',
                        help='Set the YAML file for the images and domains configuration',
                        dest='images_and_domains_yaml',
                        default='image_and_domain.yaml')
    parser.add_argument('--port',
                        help='Set the appropriate listening port value',
                        dest='port',
                        type=int,
                        default=3013)
    parser.add_argument('--redis-host',
                        help='Set the host value for making Redis connections',
                        dest='redis_host',
                        default=None)
    parser.add_argument('--redis-pass',
                        help='Set the password value for making Redis connections',
                        dest='redis_pass',
                        default=None)
    parser.add_argument('--redis-port',
                        help='Set the port value for making Redis connections',
                        dest='redis_port',
                        default=None)
    # TODO: improve to be more intelligent about the argument to accept and making it a Path (argparse Action perhaps)
    parser.add_argument('--ssl-dir',
                        #help='Change the base directory when using SSL certificate and key files with default names',
                        help='Set the ssl directory for scheduler certs',
                        dest='ssl_dir',
                        default='/ssl/scheduler/')
    parser.add_argument('--resource-list',
                        help='yaml file with a list of resources to use',
                        dest='resource_list_file',
                        default='./resources.yaml')
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
                        default=55872)

    parser.prog = package_name
    return parser.parse_args()


def read_resource_list(resource_file : Path):
    with open(resource_file) as file:
        resource_list = yaml.load(file, Loader=yaml.FullLoader)
        resource_list = [ Resource.factory_init_from_dict(resource) for resource in resource_list['resources'] ]
        return resource_list


def _get_parsed_or_env_val(parsed_val, env_var_suffix, fallback):
    """
    Return either a passed parsed value, if it is not ``None``, the value from one of several environmental variables
    with a standard beginning to their name, if one is found with a non-``None`` value, or a given fallback value.

    When proceeding to check environment variables, the following variables are checked in the following order, with the
    first existing and non-``None`` value returned:

        - DOCKER_SECRET_REDIS_<SUFFIX>
        - REDIS_<SUFFIX>
        - DOCKER_REDIS_<SUFFIX>

    The actual names have ``<SUFFIX>`` replaced with the provided suffix parameter.

    Finally, the fallback value is returned when necessary.

    Parameters
    ----------
    parsed_val
    env_var_suffix
    fallback

    Returns
    -------
    The appropriate value, given the params and the existing environment variables.
    """
    if parsed_val is not None:
        return parsed_val
    env_prefixes = ['REDIS_', 'DOCKER_SECRET_REDIS_', 'DOCKER_REDIS_']
    for prefix in env_prefixes:
        env_var = prefix + env_var_suffix
        if getenv(env_var, None) is not None:
            return getenv(env_var)
    return fallback


def redis_params(parsed_args) -> tuple:
    """
    Return the Redis host, port, and password for connections, obtained from the parsed arguments and/or environment.

    Parameters
    ----------
    parsed_args

    Returns
    -------
    tuple
        The Redis host, port, and password for connections.
    """
    host = _get_parsed_or_env_val(parsed_args.redis_host, 'HOST', 'localhost')
    port = _get_parsed_or_env_val(parsed_args.redis_port, 'PORT', 6379)
    passwd = _get_parsed_or_env_val(parsed_args.redis_pass, 'PASS', '')

    return host, port, passwd


def main():
    args = _handle_args()
    #TODO add args to allow different service definition,
    #i.e. dev test
    #if args.dev:
    #   run_dev_stuff()
    #else: run_prod()

    if args.pycharm_debug:
        if args.remote_debug_egg_path == '':
            print('Error: set to debug with Pycharm, but no path to remote debugger egg file provided')
            sys.exit(1)
        if not Path(args.remote_debug_egg_path).exists():
            print('Error: no file at given path to remote debugger egg file "{}"'.format(args.remote_debug_egg_path))
            sys.exit(1)
        sys.path.append(args.remote_debug_egg_path)
        import pydevd_pycharm
        try:
            pydevd_pycharm.settrace(args.remote_debug_host, port=args.remote_debug_port, stdoutToServer=True,
                                    stderrToServer=True)
        except Exception as error:
            msg = 'Warning: could not set debugging trace to {} on {} due to {} - {}'
            print(msg.format(args.remote_debug_host, args.remote_debug_port, error.__class__.__name__, str(error)))

    resource_list = read_resource_list(Path(args.resource_list_file))

    # Obtain Redis params
    redis_host, redis_port, redis_pass = redis_params(args)

    # instantiate the resource manager for the scheduler
    resource_manager = RedisManager("maas", redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass)
    resource_manager.set_resources(resource_list)

    # instantiate the scheduler
    # TODO: look at handling if the value in args.images_and_domains_yaml doesn't correspond to an actual file
    launcher = Launcher(images_and_domains_yaml=args.images_and_domains_yaml, type="dev")
    # instantiate the job manager
    job_manager: JobManager = JobManagerFactory.factory_create(resource_manager, launcher, host=redis_host, port=redis_port, redis_pass=redis_pass)

    #Instansite the handle_job_request
    handler = SchedulerHandler(job_manager, ssl_dir=Path(args.ssl_dir), port=args.port)
    # Create the async task for processing Jobs within queue and scheduling
    handler.add_async_task(job_manager.manage_job_processing())
    #keynamehelper.set_prefix("stack0")
    handler.run()


if __name__ == '__main__':
    main()
