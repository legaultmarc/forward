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

from pkg_resources import resource_filename
import unittest
import shutil
import random
import os

import pandas as pd
import numpy as np

from ..tasks import LogisticTest, STATSMODELS_AVAILABLE, AbstractTask
from ..experiment import Experiment, ExperimentResult
from ..phenotype.variables import ContinuousVariable, DiscreteVariable
from ..genotype import Variant, PlinkGenotypeDatabase
from .dummies import DummyPhenDatabase, DummyGenotypeDatabase
from .abstract_tests import TestAbstractTask


class TestTask(TestAbstractTask, unittest.TestCase):
    def setUp(self):
        self.task = AbstractTask()
        super(TestTask, self).setUp()


@unittest.skipIf(not STATSMODELS_AVAILABLE, "statsmodels needs to be installed"
                                            " to test the logistic task.")
class TestLogisticTask(TestAbstractTask, unittest.TestCase):
    def setUp(self, cpu=1):
        self.cpu = cpu
        self.variables = [
            ContinuousVariable("var1"),
            ContinuousVariable("var2"),
            DiscreteVariable("var3"),
            DiscreteVariable("var4"),
            ContinuousVariable("var5", True),  # Covariate.
            DiscreteVariable("var6", True),  # Covariate.
        ]
        self.task = LogisticTest()

        self.experiment = Experiment(
            name=".fwd_test_tasks",
            phenotype_container=DummyPhenDatabase(),
            genotype_container=DummyGenotypeDatabase(),
            variables=self.variables,
            tasks=[self.task],
            cpu=self.cpu
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
        self.tearDown()  # We need another custom experiment.

        # Covariates are not included in this test.
        self.variables = [
            ContinuousVariable("var1"),
            ContinuousVariable("var2"),
            DiscreteVariable("var3"),
            DiscreteVariable("var4"),
            DiscreteVariable("var_assoc")
        ]

        # Use the (plink) simulated SNPs.
        filename = os.path.abspath(
            resource_filename(__name__, "data/simulated/sim.fam")
        )
        base = filename[:-4]
        geno = PlinkGenotypeDatabase(base)

        # Add the associated phenotype.
        samples = geno.get_sample_order()
        pheno = DummyPhenDatabase(n=len(samples))
        pheno.samples = samples

        pheno.data["var_assoc"] = geno.fam["status"].values - 1

        self.experiment = Experiment(
            name=".fwd_test_tasks",
            phenotype_container=pheno,
            genotype_container=geno,
            variables=self.variables,
            tasks=[self.task],
            cpu=self.cpu
        )
        self.experiment.run_tasks()

        # Compare the results to plink.
        query = self.experiment.session.query

        plink_results = pd.read_csv(
            resource_filename(__name__, "data/simulated/plink.assoc.logistic"),
            header=0,
            delim_whitespace=True,
        )
        for i, row in plink_results.iterrows():
            result = query(ExperimentResult).\
                     filter(ExperimentResult.entity_name == row["SNP"]).\
                     filter(ExperimentResult.phenotype == "var_assoc").one()

            # Plink gives only three decimals.
            self.assertAlmostEqual(row["P"], result.significance, 3)


        # for result in query(ExperimentResult):


@unittest.skipIf(not STATSMODELS_AVAILABLE, "statsmodels needs to be installed"
                                            " to test the logistic task.")
class TestLogisticTaskMultiprocessing(TestLogisticTask):
    def setUp(self):
        super(TestLogisticTaskMultiprocessing, self).setUp(3)
