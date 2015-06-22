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

import unittest
import random
import logging
logging.basicConfig()

import numpy as np

from . import dummies

class TestDummyPhenDB(unittest.TestCase):
    """Test the DummyPhenDB class."""

    def setUp(self):
        self.db = dummies.DummyPhenDB()
        self.variables = ["var1", "var2", "var3", "var4", "var5"]

    def test_get_phenotypes(self):
        """Check if all the column names are returned."""
        self.assertEquals(
            set(self.db.get_phenotypes()),
            set(self.variables)
        )

    def test_get_phenotype_vector(self):
        """Check the type and length of the generated variables."""
        for var in self.variables:
            vec = self.db.get_phenotype_vector(var)
            self.assertEquals(vec.shape[0], 100)
            self.assertTrue(type(vec) is np.ndarray)

    def test_set_sample_order(self):
        """Try changing the sample order (permutation)."""
        # Save the initial data.
        temp = {}
        for var in self.variables:
            temp[var] = self.db.get_phenotype_vector(var)

        samples = self.db.get_sample_order()
        permutation = np.random.permutation(len(samples))
        samples_perm = [samples[i] for i in permutation]

        # Check sample labels.
        self.db.set_sample_order(samples_perm)
        self.assertEquals(samples_perm, self.db.get_sample_order())

        # Check that the data was also reordered.
        for var in self.variables:
            np.testing.assert_equal(
                temp[var][permutation], self.db.get_phenotype_vector(var)
            )

    def test_set_sample_order_subset_raises(self):
        """Check if exceptions are raised when subsetting without allow_subset.

        """
        samples = self.db.get_sample_order()
        random.shuffle(samples)
        samples = samples[:50]  # Exclude 50 individuals.

        # Some samples are missing.
        self.assertRaises(ValueError, self.db.set_sample_order, samples)

    def test_set_sample_order_subset_allowed(self):
        """Test sample subset."""
        samples = self.db.get_sample_order()
        random.shuffle(samples)
        samples = samples[:50]
        self.db.set_sample_order(samples, allow_subset=True)

    def test_get_sample_order(self):
        """Test the getter for sample order."""
        self.assertEquals(self.db.samples, self.db.get_sample_order())

    def test_get_correlation_matrix(self):
        """Test the shape for the correlation matrix."""
        # Test different subsets of phenotypes.
        mat = self.db.get_correlation_matrix(["var1", "var2"])
        self.assertEquals(mat.shape, (2, 2))

        mat = self.db.get_correlation_matrix(self.db.get_phenotypes())
        self.assertEquals(mat.shape, (5, 5))
