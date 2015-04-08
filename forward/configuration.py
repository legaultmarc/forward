# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides utilities to parse the yaml configuration file into
`foward` objects.
"""

import logging
logging.basicConfig()

from .phenotype.db import *

try:
    import yaml
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.critical("Install the yaml package: "
                    "https://pypi.python.org/pypi/PyYAML")
    raise e

def parse_configuration(filename):
    with open(filename, "r") as f:
        config = yaml.load(f)

    # Parse the Database section:
    database = config.pop("Database", None)
    if database:
        database = _parse_database(database)

    # Parse the Variables section:
    variables = config.pop("Variables", None)
    if variables:
        variables = _parse_variables(variables)

    # Parse the Genotypes section:
    genotypes = config.pop("Genotypes", None)
    if genotypes:
        genotypes = _parse_genotypes(genotypes)

def _parse_database(database):
    class_name = database.pop("pyclass", None)
    if not class_name:
        raise AttributeError("You need to provide a 'pyclass' field for the "
                             "'Database' configuration.")
    if class_name in globals():
        globals()[class_name](**database)

def _parse_variables(variables):
    pass

def _parse_genotypes(genotypes):
    pass
