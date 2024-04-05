import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set

import pytest
from pytest import CallInfo, Item, Session

logger = logging.getLogger("dmod_conftest")

if TYPE_CHECKING:
    from pytest import Config, Parser

REPO_ROOT = Path(__file__).parent.resolve()

# this is analogous to running `python -m pytest`
# this is needed for `pytest` discovery reasons specific to `dmod`'s package structure
sys.path.insert(0, str(REPO_ROOT))

# Project Level pytest fixtures
# these fixtures are available to any test in the repository

@pytest.fixture(scope="session")
def repo_root() -> Path:
    """
    Returns absolute path to repository's root directory.
    Only functional with `pytest` style tests.
    Use `repo_root_unittest` to add similar functionality to `unittest.TestCase` tests.
    """
    return REPO_ROOT

@pytest.fixture(scope="session")
def test_data_dir(request: pytest.FixtureRequest) -> Path:
    """
    Returns absolute path to repository's root data directory. 
    Only functional with `pytest` style tests. 
    Use `test_data_dir_unittest` to add similar functionality to `unittest.TestCase` tests.
    """
    if request.cls is not None:
        request.cls.__test_data_dir = REPO_ROOT / "data"
    return REPO_ROOT / "data"

# fixture variants designated for use with `unittest.TestCase`
# NOTE: fixture `scope` must be "class" to use with `unittest.TestCase` tests

@pytest.fixture(scope="class")
def repo_root_unittest(request: pytest.FixtureRequest, repo_root: Path) -> Path:
    """
    Sets `._repo_root` property on class to the absolute path to repository's root directory.
    Returns absolute path to repository's root directory if `pytest` style test.
    Functional with both `unittest.TestCase` and `pytest` style tests.

    Example:
        import unittest
        import pytest

        @pytest.mark.usefixtures("repo_root_unittest")
        class TestFoo(unittest.TestCase):
            def test_foo(self):
                # do something with repo root
                (self._repo_root / "LICENSE").read_text()
    """
    assert request.cls is not None
    request.cls._repo_root = repo_root
    return repo_root

@pytest.fixture(scope="class")
def repo_data_dir_unittest(request: pytest.FixtureRequest, repo_data_dir: Path) -> Path:
    """
    Sets `._repo_data_dir` property on class to the absolute path to repository's root data directory.
    Returns absolute path to repository's root data directory if `pytest` style test.
    Functional with both `unittest.TestCase` and `pytest` style tests.

    Example:
        import unittest
        import pytest

        @pytest.mark.usefixtures("repo_data_dir_unittest")
        class TestFoo(unittest.TestCase):
            def test_foo(self):
                # do something with data dir
                (self._repo_data_dir / "example_image_and_domain.yaml").read_text()
    """
    assert request.cls is not None
    request.cls._repo_data_dir = repo_data_dir
    return repo_data_dir

# Pytest CLI customization
# Includes logic for setting environment variables and running integration tests

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
    parser.addini(
        "env_vars", "Environment variables to set", type="args"
    )


def parse_env_vars(name_values: List[str]) -> Dict[str, str]:
    return dict(map(lambda pair: pair.split("="), name_values))


def _configure_it_env_vars(config: "Config"):
    if config.getoption("it"):
        python_files = config.getini("python_files")
        assert isinstance(python_files, list)
        python_files[:] = ["it_*.py"]

        it_env_vars = config.getini("it_env_vars")
        integration_testing_flag()

        parsed_vars = parse_env_vars(it_env_vars)
        logger.debug(f"Adding these environment variables: {parsed_vars}")

        os.environ.update(parsed_vars)

def _configure_env_vars(config: "Config"):
    env_vars = config.getini("env_vars")
    assert isinstance(env_vars, list)
    parsed_vars = parse_env_vars(env_vars)
    logger.debug(f"Adding these environment variables: {parsed_vars}")
    os.environ.update(parsed_vars)

def pytest_configure(config: "Config"):
    _configure_env_vars(config)
    _configure_it_env_vars(config)


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

