# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Test for the different Task classes.
"""

from __future__ import division

import unittest
import shutil

from ..tasks import GLMTest, STATSMODELS_AVAILABLE, AbstractTask
from ..experiment import Experiment, ExperimentResult
from ..phenotype.variables import ContinuousVariable, DiscreteVariable
from .dummies import DummyPhenDatabase, DummyGenotypeDatabase
from .abstract_tests import TestAbstractTask


class TestTask(TestAbstractTask, unittest.TestCase):
    def setUp(self):
        self.task = AbstractTask()
        super(TestTask, self).setUp()


@unittest.skipIf(not STATSMODELS_AVAILABLE, "statsmodels needs to be installed"
                                            " to test the GLM task.")
class TestGLMTask(TestAbstractTask, unittest.TestCase):
    def setUp(self, cpu=1):
        self.variables = [
            ContinuousVariable("var1"),
            ContinuousVariable("var2"),
            DiscreteVariable("var3"),
            DiscreteVariable("var4"),
            ContinuousVariable("var5", True),  # Covariate.
            DiscreteVariable("var6", True),  # Covariate.
        ]
        self.task = GLMTest()

        self.experiment = Experiment(
            name=".fwd_test_tasks",
            phenotype_container=DummyPhenDatabase(),
            genotype_container=DummyGenotypeDatabase(),
            variables=self.variables,
            tasks=[self.task],
            cpu=cpu
        )

    def tearDown(self):
        shutil.rmtree(".fwd_test_tasks")

    def test_exec(self):
        """Check if errors occur during normal execution."""
        self.experiment.run_tasks()

    def test_variable_filtering(self):
        """Make sure continuous variables were excluded even though we used the
           "all" flag.

        """
        self.experiment.run_tasks()

        query = self.experiment.session.query
        results_variables = query(ExperimentResult.phenotype).distinct().all()
        results_variables = [i[0] for i in results_variables]

        for var in self.variables:
            if var.is_covariate:
                continue

            if isinstance(var, DiscreteVariable):
                self.assertTrue(var.name in results_variables)

            elif isinstance(var, ContinuousVariable):
                self.assertTrue(var.name not in results_variables)


@unittest.skipIf(not STATSMODELS_AVAILABLE, "statsmodels needs to be installed"
                                            " to test the GLM task.")
class TestGLMTaskMultiprocessing(TestGLMTask):
    def setUp(self):
        super(TestGLMTaskMultiprocessing, self).setUp(3)
