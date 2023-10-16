#!/usr/bin/env python3
"""
@TODO: Describe the application here
"""
import os
import sys
import typing

import multiprocessing

from pathlib import Path

import dmod.evaluations.specification as specification

from argparse import ArgumentParser


try:
    import erdantic
except:
    print(
        "Erdantic is required in order to produce diagrams, but was not found. "
        "Please install a compatible version if updated diagrams are needed.",
        file=sys.stderr
    )
    exit(255)


DIAGRAM_DIRECTORY = "./images"


class Arguments(object):
    def __init__(self, *args):
        # Replace '__option' with any of the expected arguments
        self.__option: typing.Optional[str] = None

        self.__parse_command_line(*args)

    # Add a property for each argument
    @property
    def option(self) -> str:
        return self.__option

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Put the description of your application here")

        # Add Arguments
        parser.add_argument(
            "-o",
            metavar="option",
            dest="option",
            type=str,
            default="default",
            help="This is an example of an option"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__option = parameters.option


def main():
    """
    Define your main function here
    """
    arguments = Arguments()
    classes_to_diagram: typing.Sequence[typing.Type[specification.Specification]] = specification.get_specification_types(all_specifications=True)
    failures: typing.List[str] = []

    class_to_diagram: typing.Optional[typing.Type[specification.Specification]] = None

    for class_to_diagram in classes_to_diagram:
        full_name = f"{class_to_diagram.__module__}.{class_to_diagram.__qualname__}"
        output_path = os.path.join(DIAGRAM_DIRECTORY, f"{full_name}.png")

        try:
            erdantic.draw(class_to_diagram, out=output_path, depth_limit=0)
        except BaseException as exception:
            message = f"Failed to draw a graph at: '{full_name}'{os.linesep}    {exception}"
            failures.append(message)
        else:
            real_path = Path(output_path)
            print(f"Wrote a diagram for '{full_name}' to '{real_path.resolve()}'")

    if classes_to_diagram is not None:
        diagram_for_all_path = f"all-from-dmod.evaluations.specification"
        output_path = os.path.join(DIAGRAM_DIRECTORY, f"{diagram_for_all_path}.png")

        try:
            erdantic.draw(*classes_to_diagram, out=output_path, depth_limit=9999, orientation=erdantic.Orientation.VERTICAL)
        except BaseException as exception:
            message = f"Failed to draw a graph at: '{diagram_for_all_path}'{os.linesep}    {exception}"
            failures.append(message)
        else:
            real_path = Path(output_path)
            print(f"Wrote a diagram for '{diagram_for_all_path}' to '{real_path.resolve()}'")

    for message in failures:
        print(message, file=sys.stderr)

    exit(len(failures))

if __name__ == "__main__":
    main()
