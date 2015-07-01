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
logger = logging.getLogger(__name__)

from .phenotype.variables import DiscreteVariable, ContinuousVariable
from .experiment import Experiment

try:
    import yaml
except ImportError as e:
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
    experiment_cpu = int(config["Experiment"].pop("cpu", 1))

    return Experiment(experiment_name, database, genotypes, variables, tasks,
                      cpu=experiment_cpu)


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
    # If it's already in scope, just return it.
    if name in globals():
        return globals()[name]

    # Try importing it from the forward package.
    package = None
    if class_type == "tasks":
        package = "tasks"
    elif class_type == "genotypes":
        package = "genotype"
    elif class_type == "database":
        package = "phenotype.db"

    try:
        pkg = __import__(package, globals(), locals(), [name], 1)
        if hasattr(pkg, name):
            return getattr(pkg, name)
    except ImportError:
        pass

    # Try importing from user class.
    path, class_name = name.rsplit(".", 1)
    try:

        print "BANANA", path, class_name
        pkg = __import__(path, globals(), locals(), [class_name], 0)
        print "User in path", path, class_name

        if hasattr(pkg, class_name):
            return getattr(pkg, class_name)
    except ImportError:
        pass

    raise AttributeError("Could not find class '{}'.".format(name))
