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
import random

from ..tasks import GLMTest, STATSMODELS_AVAILABLE, AbstractTask
from ..experiment import Experiment, ExperimentResult
from ..phenotype.variables import ContinuousVariable, DiscreteVariable
from ..genotype import Variant
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

    def test_results(self):
        # Generate an outcome that is associated with one of the variants.
        query = self.experiment.session.query
        variants = [i[0] for i in query(Variant.name).all()]

        causal = random.choice(variants)
        geno = self.experiment.genotypes.get_genotypes(causal)

        # Simulate outcomes.
        # TODO Use plink to simulate the genotypes for the causal variant.
        # Test if the simulated OR and the GLM exp(beta) are similar.
        # Also test wrt to R.

@unittest.skipIf(not STATSMODELS_AVAILABLE, "statsmodels needs to be installed"
                                            " to test the GLM task.")
class TestGLMTaskMultiprocessing(TestGLMTask):
    def setUp(self):
        super(TestGLMTaskMultiprocessing, self).setUp(3)
