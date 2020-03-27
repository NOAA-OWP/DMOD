import argparse
from . import name as package_name
from . import MonitorService
from pathlib import Path
from socket import gethostname


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.prog = package_name
    return parser.parse_args()


def _sanity_check_path_arg(path_as_str, is_directory=False):
    path_value = Path(path_as_str)
    if not path_value.exists():
        return False
    if is_directory and not path_value.is_dir():
        return False
    if not is_directory and not path_value.is_file():
        return False
    return True


def main():
    args = _handle_args()

    # Sanity check any provided path arguments

    # Init monitor service
    handler = MonitorService()
    handler.run()


if __name__ == '__main__':
    main()
