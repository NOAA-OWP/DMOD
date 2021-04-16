#!/usr/bin/env python

from argparse import ArgumentParser


def create_commandline_parser() -> ArgumentParser:
    parser = ArgumentParser("Put a description for your script here")

    # Add options
    # parser.add_argument(
    #    "-o",
    #    metavar="option",
    #    type=str,
    #    default="default",
    #    help="This is an example of an option"
    # )

    return parser


def main():
    """
    Define your initial application code here
    """
    parameters = create_commandline_parser().parse_args()


# Run the following if the script was run directly
if __name__ == "__main__":
    main()