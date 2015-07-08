# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Test for the Experiment class.
"""

from __future__ import division

import datetime
import unittest
import shutil

from ..experiment import Experiment, ExperimentResult
from ..phenotype.variables import (DiscreteVariable, ContinuousVariable,
                                   Variable)
from ..genotype import Variant
from ..tasks import Task
from .dummies import DummyPhenDatabase, DummyGenotypeDatabase

from six.moves import cPickle as pickle
import numpy as np


class TestExperiment(unittest.TestCase):

    def setUp(self):
        phen_db = DummyPhenDatabase()
        geno_db = DummyGenotypeDatabase()
        variables = [
            ContinuousVariable("var1"),
            ContinuousVariable("var2"),
            DiscreteVariable("var3"),
            DiscreteVariable("var4"),
            ContinuousVariable("var5", True),  # Covariate.
        ]
        tasks = []

        self.experiment = Experiment(".fwd_test_experiment", phen_db,
                                     geno_db, variables, tasks, 1)

        # Convenience methods to play with the database.
        self.add = self.experiment.session.add
        self.query = self.experiment.session.query
        self.commit = self.experiment.session.commit

    def tearDown(self):
        shutil.rmtree(self.experiment.name)

    def test_dir_exists(self):
        """Check if an OSError is raised when the directory already exists."""
        args = [".fwd_test_experiment", DummyPhenDatabase(),
                DummyGenotypeDatabase(), [], [], 1]
        self.assertRaises(OSError, Experiment, *args)

    def test_query_variants(self):
        """Check if the variant database was correctly created.

        Knowing the behaviour of the dummy genotype class, we know what should
        be in the database if no filtering is applied.
        """
        expected_variants = ["snp{}".format(i + 1) for i in range(5)]
        for i, var in enumerate(self.query(Variant).all()):
            self.assertTrue(var.name in expected_variants)
            self.assertTrue(var.mac / (2 * var.n_non_missing) == var.maf)
            self.assertTrue(var.maf <= 0.5)

        self.assertEquals(i + 1, len(expected_variants))

    def test_query_results(self):
        """Add and then query back some results."""
        result = ExperimentResult(
            tested_entity="variant", task_name="test1", entity_name="snp1",
            phenotype="var1", significance=1e-5, coefficient=3,
            standard_error=0.1, confidence_interval_min=2.9,
            confidence_interval_max=3.1
        )
        self.add(result)
        self.commit()

        result2 = self.query(ExperimentResult).one()
        self.assertTrue(result is result2)

    def test_add_result(self):
        """Add results using the experiment method."""
        self.experiment.add_result("variant", "test1", "snp1", "var1", 1e-7, 3,
                                   0.1, 2.9, 3.1)
        self.commit()

        result = self.query(ExperimentResult).one()
        self.assertEquals(result.tested_entity, "variant")
        self.assertEquals(result.task_name, "test1")
        self.assertEquals(result.entity_name, "snp1")
        self.assertEquals(result.phenotype, "var1")
        self.assertEquals(result.significance, 1e-7)
        self.assertEquals(result.coefficient, 3)
        self.assertEquals(result.standard_error, 0.1)
        self.assertEquals(result.confidence_interval_min, 2.9)
        self.assertEquals(result.confidence_interval_max, 3.1)

    def test_add_result_variable(self):
        """Add results using using a variable object."""
        var = DiscreteVariable("var1")
        self.experiment.add_result("variant", "test1", "snp1", var, 1e-7, 3,
                                   0.1, 2.9, 3.1)
        self.commit()

        result = self.query(ExperimentResult.phenotype).one()[0]
        self.assertEquals(var.name, result)

    def test_experiment_info_init(self):
        info = self.experiment.info
        self.assertEquals(info["name"], ".fwd_test_experiment")
        self.assertEquals(
            info["engine_url"],
            Experiment.get_engine(info["name"], "sqlite").url
        )
        self.assertTrue(type(info["start_time"]) is datetime.datetime)

    def test_get_engine(self):
        """Checks that get_engine returns a properly behaved engine."""
        info = self.experiment.info
        engine = Experiment.get_engine(info["name"], "sqlite")

        self.assertTrue(hasattr(engine, "connect"))
        self.assertTrue(hasattr(engine, "url"))

    def test_run_tasks(self):
        """Test the execution of tasks."""
        task = Task()
        task.set_meta("executed", "")
        self.experiment.tasks.append(task)

        self.experiment.run_tasks()

        # Check if we can get the meta information back from disk (shows that
        # done() was called.
        self.assertTrue(task.task_meta_path)
        with open(task.task_meta_path, "rb") as f:
            meta = pickle.load(f)
        self.assertTrue("executed" in meta)

    def test_variables(self):
        """Check that the variables database is populated."""
        # Known from the dummy database.
        expected_variables = ["var{}".format(i + 1) for i in range(5)]
        for i, var in enumerate(self.query(Variable)):
            self.assertTrue(var.name in expected_variables)
            self.assertTrue(hasattr(var, "is_covariate"))
            self.assertTrue(hasattr(var, "n_missing"))
            self.assertTrue(hasattr(var, "variable_type"))

        self.assertTrue(i + 1, len(expected_variables))

    def test_variable_hybrids(self):
        """Test the hybrid properties of variables."""
        for var in self.experiment.variables:
            # Get the phenotypes.
            if type(var) is DiscreteVariable:
                y = self.experiment.phenotypes.get_phenotype_vector(var.name)
                prevalence = np.sum(y == 1) / np.sum(~np.isnan(y))
                self.assertEquals(var.prevalence, prevalence)
