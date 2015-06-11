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
from sqlalchemy import Column, Enum, String, Float

from . import SQLAlchemySession, SQLAlchemyBase


class ExperimentResult(SQLAlchemyBase):
    __tablename__ = "results"

    # Test informatio
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
        self.results_init()

    def results_init(self):
        """Initialize the results table."""
        ExperimentResult.__table__.create(self.engine)

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

    def run_tasks(self):
        for i, task in enumerate(self.tasks):
            task_id = "task{}_{}".format(i, task.__class__.__name__)
            task.run_task(self, task_id)

        self.session.commit()
