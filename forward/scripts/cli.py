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

from forward.configuration import parse_configuration
from forward import backend


def run_from_configuration(yaml_file):
    # Run an experiment.
    experiment = parse_configuration(yaml_file)
    experiment.run_tasks()

    # Generate an analysis report.
    backend.initialize_application(experiment.name)
    sys.argv[1] = "serve"
    sys.argv.append(experiment.name)
    backend.serve()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        run_from_configuration(sys.argv[1])

    elif len(sys.argv) == 3 and sys.argv[1] == "serve":
        backend.initialize_application(sys.argv[2])
        backend.serve()

    else:
        raise Exception("CLI only supports running a 'yaml' experiment file.")
