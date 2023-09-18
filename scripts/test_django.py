#!/usr/bin/env python3
"""
Run tests against Django Servers
"""
import sys
import typing
import os
import subprocess
import multiprocessing
import re

from pathlib import Path
from argparse import ArgumentParser

from datetime import datetime

APPLICATION_ROOT = Path(__file__).parent.parent.resolve()
"""
The root of this application. Path(__file__) will be ./DMOD/scripts/test_django.py, 
Path(__file__).parent will be ./DMOD/scripts, so you have to hit Path(__file__).parent.parent 
to hit the root, i.e. ./DMOD
"""

DEFAULT_ROOT = str(APPLICATION_ROOT / "python")
"""The root of the python libraries and services"""

MANAGE_MARKER = "os.environ.setdefault('DJANGO_SETTINGS_MODULE'"
"""A line of text that will be common across all 'manage.py' files used to launch Django"""

TEST_COMMAND = "unset DJANGO_SETTINGS_MODULE; python manage.py test"
"""
The command used to launch a suite of Django tests

Removes any possible set DJANGO_SETTINGS_MODULE values (done if none is given and will last 
beyond a test process) and runs the tests against a Django application
"""

START_MESSAGE = "======================================================================"
"""A line of text indicating the beginning of an error/failure message from a unit test"""

LAST_END_MESSAGE = "----------------------------------------------------------------------"
"""A line of text indicating the end of the last error/failure message"""

TEST_COUNT_PATTERN = re.compile(r"(?<=Found )\d+")
"""
A regular expression describing how to find the number of tests that were run 
(the text will look something like 'Found 43 tests', but we're only interested in that '43')
"""


class Arguments(object):
    """
    A concrete definition for what arguments are accepted by this application and how to parse them
    """
    def __init__(self, *args):
        """
        Constructor

        Args:
            args: command line arguments. Only provide if you seek to bypass `sys.argv`
        """
        self.__root: typing.Optional[Path] = None
        """Where to start looking for manage.py files"""

        self.__verbose: bool = False
        """
        Whether to print as much testing information as possible. 
        This will print each error/failure message along with a summary at the very end.
        """

        self.__quiet: bool = False
        """Whether to print as little information as possible (such as 'python/service/example: passed')"""

        self.__list: bool = False
        """Whether to ONLY print found django applications to test"""

        self.__parse_command_line(*args)
        
    @property
    def root(self) -> Path:
        """
        Where to start looking for manage.py files
        """
        return self.__root

    @property
    def list(self) -> bool:
        """
        Whether to ONLY print found django applications to test
        """
        return self.__list

    @property
    def verbose(self) -> bool:
        """
        Whether to print as much testing information as possible. 
        This will print each error/failure message along with a summary at the very end.
        """
        return self.__verbose

    @property
    def quiet(self) -> bool:
        """
        Whether to print as little information as possible (such as 'python/service/example: passed')
        """
        return self.__quiet

    def __parse_command_line(self, *args):
        parser = ArgumentParser(
            "Run all found Django Tests",
            epilog=f"{os.linesep}A positive return code is the number of errors."
                f"{os.linesep}A negative return code represents an application failure."
                f"{os.linesep}A return code of 0 means that all tests passed. "
                f"{os.linesep}Check by referencing the '$?' variable in your terminal."
        )

        # Add Arguments
        parser.add_argument(
            "-r",
            metavar="path",
            dest="root",
            type=str,
            default=str(DEFAULT_ROOT),
            help="Where to start looking for Django Tests"
        )

        parser.add_argument(
            "--verbose",
            dest="verbose",
            action="store_true",
            default=False,
            help="Print extra information about each failure. Mutually exclusive with --quiet and --list"
        )

        parser.add_argument(
            "--quiet",
            dest="quiet",
            action="store_true",
            default=False,
            help="Only print the bare minimum. Mutally exclusive with --verbose and --list"
        )

        parser.add_argument(
            "--list",
            dest="list",
            action="store_true",
            default=False,
            help="Only list tests that may be run. Mutally exclusive with --quiet and --verbose"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__root = Path(parameters.root)
        self.__verbose = bool(parameters.verbose)
        self.__quiet = bool(parameters.quiet)
        self.__list = bool(parameters.list)

        if len([option for option in [self.quiet, self.verbose, self.list] if option is True]) > 1:
            print(
                "--quiet, --verbose, and --list are all mutually exclusive. Only call with one.",
                file=sys.stderr
            )
            exit(-1)


class TestMessage:
    """
    Specifies the components of an encountered message from a test
    """
    def __init__(self, status: str, content: str, description: str = None):
        """
        Constructor

        Messages are expected to look like:

    
        ================================================
        error: test.module.that.produced.message
        This was a test module that apparently produced a message
        ------------------------------------------------
        Traceback:
            some detail at file x
                the code at file x
            some detail at file y
                the code at file y


        Args:
            status: The line describing where the message originated and why
            content: The bulk content of the message
            description: An optional description of what the test was aiming to do
        """
        self.status = status
        """
        The line describing where the message originated and why
        This will look like: 'ERROR: whatever.whatever.whatever'
        """
        self.content = content
        self.description = description

    def __str__(self):
        lines = [
            START_MESSAGE,
            self.status
        ]

        if self.description:
            lines.append(self.description)

        lines.extend([LAST_END_MESSAGE, self.content])
        return os.linesep.join(lines)


class TestOutput:
    """
    Metadata read from all messages resulting from a Django unit test
    """
    def __init__(self, path: str, stdout: str, stderr: str, runtime: float):
        """
        Constructor

        Args:
            path: The path to the application where 'manage.py' was run
            stdout: The data written to stdout during the process of running the tests
            stderr: The data written to stderr during the process of running the tests. 
                This will hold the bulk of the data of interest
            runtime: The number of seconds that it took to run the test
        """
        self.path = path
        """The path to the application where 'manage.py' was run"""
        
        self.stdout = stdout
        """The data written to stdout during the process of running the tests"""

        self.stderr = stderr
        """
        The data written to stderr during the process of running the tests. 
        This will hold the bulk of the data of interest
        """

        self.messages: typing.List[TestMessage] = list()
        """Messages encountered when interpretting stderr"""

        self.runtime: float = runtime
        """The number of seconds it took to run the test that produced this output"""

        self.test_count = 0
        """The total number of tests that were run (might not match the number of messages)"""

        self.__interpret_stdout()
        self.__interpret_stderr()

    @property
    def relative_directory_path(self) -> str:
        """
        The relative path to the django application from the root DMOD directory
        """
        return self.path.replace(str(APPLICATION_ROOT) + "/", "")
    
    def __interpret_stdout(self):
        """
        Interprets the data read from stdout and stores them as helpful metadata
        """
        # stdout should have a line like 'Found 38 tests'. Use the regular expression to 
        # extract and store that number.
        test_count_matches = TEST_COUNT_PATTERN.search(self.stdout)

        if not test_count_matches:
            raise ValueError(f"No line stating the number of tests run could be found:{os.linesep}{os.linesep}{self.stderr}")

        self.test_count = int(test_count_matches.group())

    def __interpret_stderr(self):
        """
        Interprets the data read from stderr and stores them as messages with easier to 
        extract metadata
        """
        # Each line to parse
        message_lines: typing.Sequence[str] = self.stderr.splitlines()

        # Whether we are currently parsing a message
        in_message: bool = False

        # The parsed content for a message
        current_content: str = ""        

        # The parsed status for a message
        current_status: str = ""        

        # The parsed description for the message
        current_description = None

        # Whether we are currently parsing the header of a message
        in_header = False

        # Interpret the contents of stderr line by line
        for line in message_lines:
            # If we're not currently in a message and the start of a new message is encountered
            if in_message is False and line == START_MESSAGE:
                # Set all tracking variables to their required base state for reading in a new message
                in_message = True
                in_header = True
                current_content = ""
                current_status = ""
                current_description = None
            # If we're in a header and the line of '-' is found, we can surmise that we've reached the 
            # end of the header and that it's not time to parse the content of the message
            elif in_header and line == LAST_END_MESSAGE:
                # Stop parsing header data
                in_header = False
            # If we're in a message and we encounter the start of a new message or we're not in
            # the header reading stage and see the end of a header, we know we've reached the last of the messages in stderr
            # Lines following will consist of extra data, such as the number of tests run and failed
            elif in_message and (line == START_MESSAGE or not in_header and line == LAST_END_MESSAGE):
                current_content = current_content.strip()
                message = TestMessage(status=current_status, content=current_content, description=current_description)
                self.messages.append(message)
                in_message = False
                current_content = ""
                current_status = ""
                current_description = None
                in_header = False
            # Otherwise, if we're in a message, we want to append what we're reading to whatever we're currently building
            elif in_message:
                # If we're in the header, the status will be the first encountered line, so if we're in a header 
                # and we don't have a status, assign this line to the status
                if in_header and not current_status:
                    current_status = line.strip()
                # If we're still in the header, we know we want to attach this to the description
                elif in_header:
                    # Since we've read a new line, we want to add a line separator to make sure that this data is 
                    # separated from the previously read
                    if current_description:
                        current_description += os.linesep

                    current_description += line
                # Otherwise, we want to just tack the read data onto the content of the message we're building
                else:
                    # If we're on the final line of the messages, just tack on a new line to our content, 
                    # otherwise attach the new content after a new line in order to keep the natural separation from stderr
                    current_content += os.linesep if line == LAST_END_MESSAGE else f"{os.linesep}{line}"

        # If it's detected that we're still parsing and have reached the end of the document, we want to attach 
        # what we have as a new message
        if current_content and in_message:
            current_content = current_content.strip()
            message = TestMessage(status=current_status, content=current_content, description=current_description)
            self.messages.append(message)

    def print(self, verbose: bool = False, quiet: bool = False):
        """
        Print the test results in one of a different number of formats

        Args:
            verbose: Whether to print in verbose mode
            quiet: Whether to print in quiet mode
        """
        # verbose and quiet mode conflict, so throw an error if they are encountered
        if verbose and quiet:
            print(
                "Output cannot be both quiet and verbose; choose either '--quiet' or '--verbose', but not both",
                file=sys.stderr
            )
            # Exit with a code of 255 to indicate that this was an application error, not a test error or failure
            exit(255)

        # Print the maximum amount of data if in verbose mode
        if verbose:
            """
            Verbose mode output should look like:

            -----------------------------------
            python/service/example_service
            ======================================================================
            error: test.module.that.produced.message
            This was a test module that apparently produced a message
            ----------------------------------------------------------------------
            Traceback:
                some detail at file x
                    the code at file x
                some detail at file y
                    the code at file y

            ======================================================================
            error: test.module.that.produced.message2
            This was another test module that apparently produced a message
            ----------------------------------------------------------------------
            Traceback:
                some detail at file x2
                    the code at file x2
                some detail at file y2
                    the code at file y2

            ----------------------------------------------------------------------
            Ran 7 tests in 0.843s

            FAILED (errors=2)
            ======================================================================
            """
            # Print a basic test identifier
            print("-----------------------------------")
            print(self.relative_directory_path)

            # Print every encountered message
            for error in self.messages:
                print(error)
                print()

            # Create a barrier between messages and metadata
            print(LAST_END_MESSAGE)
            
            # Indicate how many tests were run and how long it took
            print(f"Ran {self.test_count} tests in {self.runtime}s")
            print()

            # Indicate if tests passed or failed in total
            print(
                f"{'FAILED' if self.failed else 'OK'}"
                f"{' (errors=' + str(self.count) + ')' if self.failed else ''}"
            )

            # End the message with a notable barrier and a buffer of whitespace
            print(START_MESSAGE)
            print()
            print()
        # if in quiet mode, print as little information as possible
        elif quiet:
            """
            This should look like:

            python/service/example_service: failed
            """
            print(
                f"{self.relative_directory_path} : {'failed' if self.failed else 'passed'}"
            )
        # Otherwise show basic information about what was run
        else:
            print(
                f"{self.relative_directory_path}: "
                f"{'FAILED' if self.failed else 'OK'}"
                f"{' (errors=' + str(self.count) + ')' if self.failed else ''}"
                f" (Ran {self.test_count} tests in {self.runtime}s)"
            )

    @property
    def count(self) -> int:
        """
        The number of notable errors or failures

        Feeds into the final exit code
        """
        return len(self.messages)

    @property
    def failed(self) -> bool:
        """
        Whether the test failed
        """
        return self.count != 0

    def __str__(self):
        return f"{self.path}: {'Failed' if self.failed else 'Passed'} {self.test_count} Tests"

    def __repr__(self):
        return self.__str__()


def find_django_applications(root: Path) -> typing.List[Path]:
    """
    Find the path to every testable Django application

    Args:
        root: Where to start looking for files

    Returns:
        A list of all found testable Django applications
    """
    application_paths = list()

    # Indicates if the current root directory might be able to be interpreted 
    # as a testable Django application
    has_manage = False

    # Iterate through each item to see if we've found a Django application 
    # or if we need to look deeper
    for path in root.iterdir():
        # A __pycache__ file or directory is a 'compiled' artifact that we want to ignore
        if "__pycache__" in path.parts:
            continue
        # Anything starting with '.' is considered 'hidden', so we need to skip that
        elif path.name.startswith("."):
            continue
        # If a file named 'manage.py' is found, we might need to check if we're in 
        # a Django application
        elif path.is_file() and path.name == "manage.py":
            has_manage = True
        # If the path is a directory, we need to dive deeper to see if a child directory is an application
        elif path.is_dir():
            application_paths.extend(find_django_applications(path))

    # If this directory has a file that looks like Django's 'manage.py', we need to check it and see if it 
    # probably is one
    if has_manage:
        # Build up the path to the manage.py file so we can open it
        possible_manage_py_path = root.joinpath("manage.py")

        # Open and read the manage.py file. If it contains a marker indicating that it is indeed the file 
        # we're looking for, add this current directory to the list of django applications
        with possible_manage_py_path.open() as manage_file:
            if MANAGE_MARKER in manage_file.read():
                application_paths.append(root)

    return application_paths


def run_django_test(path: typing.Union[Path, str]) -> TestOutput:
    """
    Test a Django application

    Args:
        path: The file path to the Django application

    Returns:
        Output explaining the results of the test
    """
    if isinstance(path, Path):
        path = str(path)

    # Record the start time so we get the overall time it takes to run the tests
    start_time = datetime.now()

    # Run the django tests in a shell at the path of the Django application of interest
    process = subprocess.Popen(
        TEST_COMMAND,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        cwd=path
    )

    # Wait for the tests to finish and collect the values from stdout and stderr
    stdout, stderr = process.communicate()

    # Mark the time of completion to the total runtime may be caalculated
    end_time = datetime.now()

    # Figured out the amount of time it took to run the tests
    duration = end_time - start_time

    # Record and return the results of the the test
    output = TestOutput(
        path=path,
        stdout=stdout.decode(),
        stderr=stderr.decode(),
        runtime=duration.total_seconds()
    )

    return output


def run_all_django_tests(django_paths: typing.Sequence[Path]) -> typing.Sequence[TestOutput]:
    """
    Run tests on every identified Django application

    Args:
        django_paths: The paths to each Django application to test

    Returns:
        A collection of test results from every identified Django application
    """
    result_data: typing.List[TestOutput] = list()

    # If only one path is found, run that naturally
    if len(django_paths) == 1:
        output = run_django_test(django_paths[0])
        result_data.append(output)
    # If multiple paths are found, run as many as possible in parallel
    elif len(django_paths) > 1:
        with multiprocessing.Pool(os.cpu_count()) as worker_pool:
            outputs = worker_pool.map(run_django_test, django_paths)

        for output in outputs:
            result_data.append(output)

    return result_data


def test_django_applications(root: typing.Union[str, Path] = None) -> typing.Sequence[TestOutput]:
    """
    Find and run all Django application tests found at or after the given path

    Args:
        root: Where to start looking for Django applications

    Returns:
        A list of test results from all found found Django applications
    """
    manage_files = find_django_applications(root or DEFAULT_ROOT)
    return run_all_django_tests(django_paths=manage_files)


def print_summary(outputs: typing.Sequence[TestOutput]):
    """
    Print a summary of the result of each Django test

    Args:
        The outputs from each Django test
    """
    # A record looking like `python/services/example: passed` needs to be print for each result
    for output in outputs:
        print(f"{output.relative_directory_path}: {'failed' if output.failed else 'passed'}")


def list_django_applications(root: typing.Union[Path, str]):
    """
    Print every found django application
    """
    manage_files = find_django_applications(root)
    for path in manage_files:
        print("    " + str(path).replace(str(APPLICATION_ROOT) + "/", ""))


def print_test_results(
    test_results: typing.Sequence[TestOutput],
    quiet: bool = None,
    verbose: bool = None
):
    """
    Format and print all encountered test results

    Args:
        test_results: The test results to print
        quiet: Whether to print in quiet mode
        verbose: Whether to print in verbose mode
    """
    # If no argument is passed to indicate quiet mode set it as False in order to be explicit
    if quiet is None:
        quiet = False

    # If no argument is passed to indicate verbose mode set it as False in order to be explicit
    if verbose is None:
        verbose = False

    # Print each test result in accordance to their verbose, quiet, and default modes
    for test_result in test_results:
        test_result.print(verbose, quiet)

    # Print an additional summary if working in verbose mode
    if verbose:
        print_summary(test_results)


def main() -> int:
    """
    The primary function within this script/application.
    Will run the tests for all detected django servers and print their output.

    Returns:
        The number of errors or failures resulting from tests
    """
    arguments = Arguments()

    # Start out by setting the initial code to 0 - this is the default 
    # 'success' return code and will indicate that there were no failed tests
    code = 0

    # If asked to just list data, call the listing function and continue on
    if arguments.list:
        list_django_applications(arguments.root)
    # Otherwise run each test and print the results
    else:
        test_results = test_django_applications(arguments.root)

        print_test_results(
            test_results=test_results,
            quiet=arguments.quiet,
            verbose=arguments.verbose
        )

        code += sum([test_result.count for test_result in test_results])

    return code


if __name__ == "__main__":
    # Test all available Django applications and return the number of failed tests
    error_count = main()
    exit(error_count)
