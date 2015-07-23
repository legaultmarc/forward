#!/usr/bin/env python

# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Command line interface script to run gene-phenome experiments using the forward
package.
"""

import sys

from forward.configuration import parse_configuration
from forward.report import Report


def run_from_configuration(yaml_file):
    # Run an experiment.
    experiment = parse_configuration(yaml_file)
    experiment.run_tasks()

    # Generate an analysis report.
    report = Report(experiment)
    report.serve()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        run_from_configuration(sys.argv[1])
    else:
        raise Exception("CLI only supports running a 'yaml' experiment file.")
