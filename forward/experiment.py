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

import os
import datetime
import logging
logger = logging.getLogger()

import numpy as np
import sqlalchemy
import h5py
from sqlalchemy import Column, Enum, String, Float, ForeignKey, Integer
from six.moves import cPickle as pickle

from . import SQLAlchemySession, SQLAlchemyBase, FORWARD_INIT_TIME
from .utils import format_time_delta
from .phenotype.variables import (Variable, DiscreteVariable,
                                  ContinuousVariable, TRANSFORMATIONS)


class RelatedPhenotypesExclusions(SQLAlchemyBase):
    """Record of the related phenotypes when the user asked for correlation
    based exclusions.

    When phenotypes are related (correlated), it is common practice in pheWAS
    to exclude samples that are unaffected for the considered outcome but
    affected for a correlated outcome. This keeps track of such exclusions.

    An important remark is that the sum of exclusions does not make up the
    total number of NAs, as we also need to count actual missing values.

    """
    __tablename__ = "related_phenotypes_exclusions"

    phen1 = Column(ForeignKey("variables.name"), primary_key=True)
    phen2 = Column(ForeignKey("variables.name"), primary_key=True)
    n_excluded = Column(Integer())


class ExperimentResult(SQLAlchemyBase):
    """SQLAlchemy class to handle experimental results.

    TODO. This could potentially be refactored so that tested_entity is a
    foreign key to the forward.genotype.Variant class. This would require
    using concrete table inheritance.

    """
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
                 variables, tasks, build, cpu=1):

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
        self.tasks = list(tasks)
        self.info = {}

        self.cpu = max(1, cpu)
        self.build = build
        logger.info("The build set for this experiment is {}.".format(build))

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
            "start_time": FORWARD_INIT_TIME,
            "build": self.build
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
            # Check the validity of the transformation.
            if hasattr(variable, "transformation"):
                transformation = variable.transformation
                if transformation and transformation not in TRANSFORMATIONS:
                    msg = ("Invalid transformation {}. Recognized "
                           "transformations are: {}.")
                    msg = msg.format(
                        variable.transformation, ", ".join(TRANSFORMATIONS)
                    )
                    raise ValueError(msg)
            variable.compute_statistics(self.phenotypes)
            self.session.add(variable)

        self.session.commit()

        # Serialize all the outcome data to disk using hdf5.
        # This is useful for the backend.
        hdf5_filename = os.path.join(self.name, "phenotypes.hdf5")
        hdf5_file = h5py.File(hdf5_filename, "w")

        for variable in self.variables:
            v = self.phenotypes.get_phenotype_vector(variable)
            dataset = hdf5_file.create_dataset(variable.name, data=v)

        hdf5_file.close()

        # We also compute a correlation matrix and serialize it.
        var_names = [var.name for var in self.variables]
        corr_mat = self.phenotypes.get_correlation_matrix(var_names)

        mat_filename = os.path.join(self.name, "phen_correlation_matrix.npy")
        np.save(mat_filename, corr_mat)

        # Set the variables list on the phenotype database side.
        self.phenotypes.set_experiment_variables(self.variables)
        corr_thresh = self.phenotypes.get_phenotype_relation_threshold()

        self.info.update({
            "phen_correlation": mat_filename,
            "outcomes": var_names,
            "phenotype_correlation_for_exclusion": corr_thresh
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
            db_url = "sqlite:///{}".format(db_path)
            return sqlalchemy.create_engine(db_url)
        else:
            raise NotImplementedError("Only sqlite is supported (for now).")

    def _write_exclusions(self):
        # Check if exclusions were made.
        try:
            exclusions = self.phenotypes._exclusion_mappings
        except Exception:
            logger.debug("Could not access the exclusions from the phenotype "
                         "database.")
            return

        # Create the table.
        RelatedPhenotypesExclusions.__table__.create(self.engine)

        for phen1, phen2, n in exclusions:
            self.session.add_all([
                RelatedPhenotypesExclusions(phen1=phen1, phen2=phen2,
                                            n_excluded=n)
            ])

        self.session.commit()

    def run_tasks(self):
        """Run the tasks registered for this experiment.

        This method takes care of the following:

        - Create a task-specific work directory.
        - Call the task's `done()` method to insure clean up code is executed.
        - Commit the database (after all tasks are executed).
        - Set the walltime for the experiment.
        - Write the experiment metadata to disk in the experiment folder when
          everything is over.

        """
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

        # Write the exclusions that were made based on related phenotypes to
        # the database.
        self._write_exclusions()

        # All tasks are done, set the walltime.
        self.info["walltime"] = (datetime.datetime.now() -
                                 self.info["start_time"])

        # Write the metadata to disk.
        with open(os.path.join(self.name, "experiment_info.pkl"), "wb") as f:
            pickle.dump(self.info, f)

        logger.info("Completed all tasks in {}.".format(
            format_time_delta(self.info["walltime"])
        ))
