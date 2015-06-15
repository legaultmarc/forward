# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides utilities to parse the yaml configuration file into
`forward` objects.
"""

import logging
logging.basicConfig()

from .phenotype.variables import DiscreteVariable, ContinuousVariable
from .experiment import Experiment

from .phenotype.db import *
from .genotype import *
from .tasks import *

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

    # Parse the "Experiments" section which is actually a list of analysis
    # to do.
    tasks = config["Experiment"].pop("tasks")
    if tasks:
        tasks = _parse_tasks(tasks)

    # Create the experiment object
    experiment_name = config["Experiment"].pop("name", "forward_experiment")
    experiment_correction = config["Experiment"].pop("correction",
                                                     "bonferroni")
    experiment_cpu = int(config["Experiment"].pop("cpu", 1))

    return Experiment(experiment_name, database, genotypes, variables, tasks,
                      cpu=experiment_cpu, correction=experiment_correction)


def _parse_database(database):
    class_name = database.pop("pyclass", None)
    return get_class(class_name, "database")(**database)


def _parse_variables(variables):
    variable_objects = []
    for variable in variables:
        var_type = variable.pop("type", None)
        name = variable.pop("name", None)
        is_covar = variable.pop("covariate", False)

        if var_type == "discrete":
            variable_objects.append(DiscreteVariable(name, is_covar))

        elif var_type == "continuous":
            variable_objects.append(ContinuousVariable(name, is_covar))

        else:
            raise Exception("Unknown variable type '{}'.".format(var_type))

    return variable_objects


def _parse_genotypes(genotypes):
    class_name = genotypes.pop("pyclass", None)
    return get_class(class_name, "genotypes")(**genotypes)


def _parse_tasks(tasks):
    task_objects = []
    for task in tasks:
        class_name = task.pop("pyclass", None)
        task_objects.append(get_class(class_name, "tasks")(**task))
    return task_objects


def get_class(name, class_type=None):
    if not name:
        raise AttributeError("You need to provide a 'pyclass' field.")
    if name in globals():
        # TODO We will certainly use some kind of dynamic imports so that the
        # use can easily add classes.
        return globals()[name]
    else:
        raise AttributeError("Could not find class '{}'.".format(name))
