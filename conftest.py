import os
import sys
from pathlib import Path
import logging
from typing import Dict, List, Set, TYPE_CHECKING, Optional
from pytest import Item, CallInfo, Session
import subprocess

logger = logging.getLogger("dmod_conftest")

if TYPE_CHECKING:
    from pytest import Config, Parser

REPO_ROOT = Path(__file__).parent.resolve()

# this is analogous to running `python -m pytest`
# this is needed for `pytest` discovery reasons specific to `dmod`'s package structure
sys.path.insert(0, str(REPO_ROOT))

integration_testing: bool = False
modules: Set[Path] = set()
active: Set[Path] = set()


def integration_testing_flag():
    global integration_testing
    integration_testing = True
    logger.debug("integration testing flag on")


def pytest_addoption(parser: "Parser"):
    parser.addoption(
        "--it", action="store_true", default=False, help="run integration tests"
    )
    parser.addini(
        "it_env_vars", "Environment variables for integration tests", type="args"
    )


def parse_it_env_vars(name_values: List[str]) -> Dict[str, str]:
    return dict(map(lambda pair: pair.split("="), name_values))


def pytest_configure(config: "Config"):
    if config.getoption("it"):
        python_files = config.getini("python_files")
        assert isinstance(python_files, list)
        python_files[:] = ["it_*.py"]

        it_env_vars = config.getini("it_env_vars")
        integration_testing_flag()

        parsed_vars = parse_it_env_vars(it_env_vars)
        logger.debug(f"Adding these environment variables: {parsed_vars}")

        os.environ.update(parsed_vars)


def get_setup_script_path(module: Path) -> Path:
    return module / "setup_it_env.sh"


def setup(setup_script: Path) -> "subprocess.CompletedProcess[bytes]":
    cmd = " ".join(["source", str(setup_script), "&&", "do_setup"])
    logger.debug(f"launching setup script: {cmd!r}")
    return subprocess.run(
        cmd,
        capture_output=True,
        shell=True,
    )


def teardown(setup_script: Path) -> "subprocess.CompletedProcess[bytes]":
    cmd = " ".join(["source", str(setup_script), "&&", "do_teardown"])
    logger.debug(f"launching teardown script: {cmd!r}")
    return subprocess.run(
        cmd,
        capture_output=True,
        shell=True,
    )


def format_completed_process(cp: "subprocess.CompletedProcess[bytes]") -> str:
    return (
        f"args:   {cp.args!r}\n"
        f"stdout: {cp.stdout.decode('utf-8').strip()}\n"
        f"stderr: {cp.stderr.decode('utf-8').strip()}"
    )


def pytest_runtest_setup(item: Item):
    if not integration_testing:
        return

    module = item.path.parent
    if module not in modules:
        modules.add(module)

        setup_script = get_setup_script_path(module)

        if setup_script.exists():
            out = setup(setup_script)
            logger.info(f"setup: {module.parent.parent.name!r}")
            logger.debug(format_completed_process(out))

            if out.returncode != 0:
                logger.debug(
                    f"non-zero return code ({out.returncode:3}): {module.parent.parent.name!r}"
                )
                logger.debug(format_completed_process(out))

                out = teardown(setup_script)
                logger.info(f"tearing down {module.parent.parent.name!r} early")

                if out.returncode != 0:
                    logger.debug(
                        f"non-zero return code ({out.returncode:3}): {module.parent.parent.name!r}"
                    )
                    logger.debug(format_completed_process(out))

                item.session.shouldstop = True
                # dont add to active
                return

            active.add(module)


def pytest_runtest_teardown(item: Item, nextitem: Optional[Item]):
    if not integration_testing:
        return

    next_item_module = nextitem.path.parent if nextitem is not None else None
    if next_item_module is None or next_item_module not in modules:
        # do item tear down
        module = item.path.parent
        setup_script = get_setup_script_path(module)

        out = teardown(setup_script)
        logger.info(f"tearing down: {module.parent.parent.name!r}")
        logger.debug(format_completed_process(out))

        active.remove(module)


def pytest_sessionfinish(session: Session, exitstatus: int):
    if not integration_testing:
        return

    while True:
        try:
            module = active.pop()
        except KeyError:
            break

        setup_script = get_setup_script_path(module)
        out = teardown(setup_script)

        logging.info(f"tearing down: {module.parent.parent.name!r}")
        logging.debug(format_completed_process(out))

