# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides ways to manage experiments. The experiment objects can
be parsed from the CLI, a yaml configuration file or, eventually, a web
interface.

Overall goals for this module will be to provide:

    - Automated reports.
    - Good organization of experiments aiming at a better reproductibility.
    - Aggregating and writing results files.

"""

import os
import logging
logger = logging.getLogger()

import sqlalchemy

from . import SQLAlchemySession, SQLAlchemyBase


class Experiment(object):
    """Class representing an experiment."""
    def __init__(self, name, phenotype_container, genotype_container,
                 variables, tasks, cpu=1, correction="bonferonni"):

        # Create a directory for the experiment.
        try:
            os.makedirs(name)
        except OSError as e:
            logger.critical("Please delete the {} directory manually if you "
                            "want to overwrite it. Alternatively, choose "
                            "another experiment name.".format(name))
            raise e

        db_path = os.path.join(name, "forward_database.db")

        # Create a sqlalchemy engine and bind it to the session.
        self.engine = sqlalchemy.create_engine("sqlite:///{}".format(db_path))
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

        # Bind the different components.
        self.name = name
        self.phenotypes = phenotype_container
        self.genotypes = genotype_container
        self.variables = variables
        self.tasks = tasks

        self.cpu = min(1, cpu)
        self.correction = correction

        # Make the genotypes and phenotypes sample order consistent.
        self.phenotypes.set_sample_order(self.genotypes.get_sample_order(),
                                         allow_subset=True)

        # Do experiment initialization on the database objects.
        self.genotypes.experiment_init(self)

    def run_tasks(self):
        for task in self.tasks:
            task.run_task(self)
