# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Test for the dummy classes. These classes imitate the forward API for testing
purposes.
"""

from __future__ import division

from pkg_resources import resource_filename
import unittest
import random
import logging
logging.basicConfig()

import numpy as np

from . import dummies
from ..phenotype.db import ExcelPhenotypeDatabase


class TestPhenDBInterface(object):
    """Test the DummyPhenDB class."""

    def test_get_phenotypes(self):
        """Check if all the column names are returned."""
        self.assertEquals(
            set(self.db.get_phenotypes()),
            set(self._variables)
        )

    def test_get_phenotype_vector(self):
        """Check the type and length of the generated variables."""
        n_samples = len(self.db.get_sample_order())
        for var in self.db.get_phenotypes():
            vec = self.db.get_phenotype_vector(var)
            self.assertEquals(vec.shape[0], n_samples)
            self.assertTrue(type(vec) is np.ndarray)

    def test_set_sample_order(self):
        """Try changing the sample order (permutation).

        This also acts as a test for db.get_sample_order(). There is no direct
        way of testing this method without making assumptions about the
        underlying structure.

        """
        # Save the initial data.
        temp = {}
        for var in self.db.get_phenotypes():
            temp[var] = self.db.get_phenotype_vector(var)

        samples = self.db.get_sample_order()
        permutation = np.random.permutation(len(samples))
        samples_perm = [samples[i] for i in permutation]

        # Check sample labels.
        self.db.set_sample_order(samples_perm)
        self.assertEquals(samples_perm, self.db.get_sample_order())

        # Check that the data was also reordered.
        for var in self._variables:
            np.testing.assert_equal(
                temp[var][permutation], self.db.get_phenotype_vector(var)
            )

    def test_set_sample_order_subset_raises(self):
        """Check if exceptions are raised when subsetting without allow_subset.

        """
        samples = self.db.get_sample_order()
        random.shuffle(samples)
        # Exclude half of the individuals.
        samples = samples[:(len(samples) // 2)]

        # Some samples are missing.
        self.assertRaises(ValueError, self.db.set_sample_order, samples)

    def test_set_sample_order_subset_allowed(self):
        """Test sample subset."""
        samples = self.db.get_sample_order()
        random.shuffle(samples)
        samples = samples[:50]
        self.db.set_sample_order(samples, allow_subset=True)

    def test_get_correlation_matrix(self):
        """Test the shape for the correlation matrix."""
        # Test different subsets of phenotypes.
        # Select 3 columns.
        cols = self.db.get_phenotypes()
        random.shuffle(cols)
        mat = self.db.get_correlation_matrix(cols[:3])
        self.assertEquals(mat.shape, (3, 3))

        mat = self.db.get_correlation_matrix(self.db.get_phenotypes())
        self.assertEquals(mat.shape, (len(cols), len(cols)))


class TestExcelPhenotypeDatabase(TestPhenDBInterface, unittest.TestCase):
    def setUp(self):
        self.db = ExcelPhenotypeDatabase(
            resource_filename(__name__, "data/test_excel_db.xlsx"),
            "sample", missing_values="-9"
        )
        self._variables = ["qte1", "discrete1", "qte2", "discrete2", "covar"]


class TestDummyPhenotypeDatabase(TestPhenDBInterface, unittest.TestCase):
    def setUp(self):
        self.db = dummies.DummyPhenDB()
        self._variables = ["var1", "var2", "var3", "var4", "var5"]


class TestDummyGenotypeDB(unittest.TestCase):
    """Test the dummy genotype database."""

    def setUp(self):
        self.variants = ["snp{}".format(i + 1) for i in range(5)]
        self.db = dummies.DummyGenotypeDatabase()

    def test_get_genotypes(self):
        self.db.experiment_init(None)
        for var in self.variants:
            geno = self.db.get_genotypes(var)
            self.assertEquals(geno.shape[0], 100)

        self.assertRaises(ValueError, self.db.get_genotypes, "test")

    def test_filters(self):
        self.db.experiment_init(None)
        # Compute statistics before.
        should_be_removed = set()
        for var in self.variants:
            geno = self.db.get_genotypes(var)

            maf = np.nansum(geno)
            maf /= 2 * geno.shape[0]
            if maf < 0.12:
                should_be_removed.add(var)

            completion = np.sum(~np.isnan(geno)) / geno.shape[0]
            if completion < 0.98:
                should_be_removed.add(var)

        self.db.filter_maf(0.12)
        self.db.filter_completion(0.98)
        self.db.experiment_init(None)  # Redo this for filtering.

        self.assertEquals(
            set(self.db.genotypes.keys()),
            (set(self.variants) - should_be_removed)
        )
