#!/usr/bin/env python

# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

from __future__ import print_function

"""
Command line interface script to run gene-phenome experiments using the forward
package.
"""

import sys
import argparse

from forward.configuration import parse_configuration
from forward import backend, FORWARD_REPORT_ROOT


def run_from_configuration(yaml_file):
    # Run an experiment.
    experiment = parse_configuration(yaml_file)
    experiment.run_tasks()

    print()
    print("To view the interactive report, use the forward-cli script:")
    print()
    print("forward-cli report {}".format(experiment.name))
    print()


def show_report(experiment_name):
    backend.initialize_application(experiment_name)
    backend.serve()


def parse_args():
    passthrough = sys.argv[-1] == "passthrough"
    if passthrough:
        sys.argv.pop()

    description = ("Command line utility to run Forward or to launch the "
                   "interactive report.")
    parser = argparse.ArgumentParser(description=description)

    subparser = parser.add_subparsers(dest="command")
    run_parser = subparser.add_parser(
        "run",
        help=("Run a YAML configuration file to file to execute the Forward "
              "experiment.")
    )

    run_parser.add_argument(
        "yaml_filename",
        help="Path to the YAML configuration file."
    )

    report_parser = subparser.add_parser(
        "report",
        help="Serve the report locally (A web browser is needed)."
    )

    report_parser.add_argument(
        "experiment",
        help="Name of the experiment for the dynamic report."
    )

    args = parser.parse_args()
    if args.command == "run":
        return run_from_configuration(args.yaml_filename)

    if args.command == "report":
        if not passthrough:
            print("Starting the server. Visit:")
            print()
            print("http://localhost:5000{}".format(FORWARD_REPORT_ROOT))
            print()

        sys.argv.append("passthrough")
        return show_report(args.experiment)

if __name__ == "__main__":
    parse_args()
