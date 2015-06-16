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

    - Good organization of experiments aiming at a better reproductibility.
    - Aggregating and writing analysis meta data, results files and databases.

"""

try:
    import cPickle as pickle
except ImportError:
    import pickle  # Py3

import os
import datetime
import logging
logger = logging.getLogger()

import numpy as np
import sqlalchemy
from sqlalchemy import Column, Enum, String, Float

from . import SQLAlchemySession, SQLAlchemyBase, FORWARD_INIT_TIME
from .utils import format_time_delta
from .phenotype.variables import Variable, DiscreteVariable, ContinuousVariable


class ExperimentResult(SQLAlchemyBase):
    __tablename__ = "results"

    # Test information
    tested_entity = Column(Enum("variant", "snp-set"), default="variant")
    task_name = Column(String(25), primary_key=True)
    entity_name = Column(String(25), primary_key=True)
    phenotype = Column(String(30), primary_key=True)

    # Statistics
    significance = Column(Float())  # e.g. p-value
    coefficient = Column(Float())  # e.g. beta
    standard_error = Column(Float())
    confidence_interval_min = Column(Float())  # min of 95% CI on coefficient
    confidence_interval_max = Column(Float())  # max of 95% CI on coefficient


class Experiment(object):
    """Class representing an experiment."""
    def __init__(self, name, phenotype_container, genotype_container,
                 variables, tasks, cpu=1):

        # Create a directory for the experiment.
        try:
            os.makedirs(name)
        except OSError as e:
            logger.critical("Please delete the {} directory manually if you "
                            "want to overwrite it. Alternatively, choose "
                            "another experiment name.".format(name))
            raise e

        # Create a sqlalchemy engine and bind it to the session.
        self.engine = Experiment.get_engine(name, "sqlite")
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

        # Bind the different components.
        self.name = name
        self.phenotypes = phenotype_container
        self.genotypes = genotype_container
        self.variables = variables
        self.tasks = tasks
        self.info = {}

        self.cpu = max(1, cpu)

        # Make the genotypes and phenotypes sample order consistent.
        self.phenotypes.set_sample_order(self.genotypes.get_sample_order(),
                                         allow_subset=True)

        # Do experiment initialization on the database objects.
        self.genotypes.experiment_init(self)
        self.experiment_info_init()
        self.results_init()

        # Initialize the variables (generates some statistics).
        self.variables_init()

    def experiment_info_init(self):
        """Initialize a dict containing experiment metadata."""

        self.info.update({
            "name": self.name,
            "engine_url": self.engine.url,
            "start_time": FORWARD_INIT_TIME
        })
        # TODO using this constant will not be representative if the user is
        # not using the scripts/cli.py

    def results_init(self):
        """Initialize the results table."""
        ExperimentResult.__table__.create(self.engine)

    def variables_init(self):
        """Initialize the variables table and computes some statistics."""
        for obj in (Variable, DiscreteVariable, ContinuousVariable):
            obj.__table__.create(self.engine)

        for variable in self.variables:
            variable.compute_statistics(self.phenotypes)
            self.session.add(variable)

        # We also compute a correlation matrix and serialize it.
        var_names = [var.name for var in self.variables]
        corr_mat = self.phenotypes.get_correlation_matrix(var_names)

        mat_filename = os.path.join(self.name, "phen_correlation_matrix.npy")
        np.save(mat_filename, corr_mat)

        self.info.update({
            "phen_correlation": mat_filename,
            "outcomes": var_names,
        })

    def add_result(self, entity_type, task, entity, phenotype, significance,
                   coefficient, standard_error, confidence_interval_min,
                   confidence_interval_max):

        if hasattr(phenotype, "name"):
            phenotype = phenotype.name  # Variable object.

        result = ExperimentResult(
            tested_entity=entity_type,
            task_name=task,
            entity_name=entity,
            phenotype=phenotype,

            significance=significance,
            coefficient=coefficient,
            standard_error=standard_error,
            confidence_interval_min=confidence_interval_min,
            confidence_interval_max=confidence_interval_max,
        )
        self.session.add(result)

    @staticmethod
    def get_engine(experiment_name, engine_type):
        """Get an SQLAlchemy engine for a given experiment."""

        if engine_type == "sqlite":
            db_path = os.path.join(experiment_name, "forward_database.db")
            return sqlalchemy.create_engine("sqlite:///{}".format(db_path))
        else:
            raise NotImplementedError("Only sqlite is supported (for now).")

    def run_tasks(self):
        # Create a directory for tasks to be able to have meta-data.
        tasks_dir = os.path.join(self.name, "tasks")

        for i, task in enumerate(self.tasks):
            task_id = "task{}_{}".format(i, task.__class__.__name__)
            work_dir = os.path.join(tasks_dir, task_id)
            os.makedirs(work_dir)
            task.run_task(self, task_id, work_dir)
            task.done()

        # Commit the database.
        self.session.commit()

        # All tasks are done, set the walltime.
        self.info["walltime"] = (datetime.datetime.now() -
                                 self.info["start_time"])

        # Write the metadata to disk.
        with open(os.path.join(self.name, "experiment_info.pkl"), "wb") as f:
            pickle.dump(self.info, f)

        logger.info("Completed all tasks in {}.".format(
            format_time_delta(self.info["walltime"])
        ))
