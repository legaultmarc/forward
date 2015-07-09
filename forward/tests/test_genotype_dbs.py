# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Test for the Genotype databases implementations.
"""

from pkg_resources import resource_filename
import unittest
import tempfile
import random
import os

import numpy as np

from ..genotype import (FrozenDatabaseError, MemoryImpute2Geno,
                        PlinkGenotypeDatabase)
from .abstract_tests import TestAbstractGenoDB
from . import dummies


class TestDummyGenotypeDatabase(TestAbstractGenoDB, unittest.TestCase):
    """Tests for DummyGenotypeDatabase."""
    def setUp(self):
        super(TestDummyGenotypeDatabase, self).setUp()
        self.db = dummies.DummyGenotypeDatabase()
        self._variants = ["snp{}".format(i + 1) for i in range(5)]


class TestMemoryImpute2Geno(TestAbstractGenoDB, unittest.TestCase):
    """Tests for MemoryImpute2Geno."""
    def setUp(self):
        super(TestMemoryImpute2Geno, self).setUp()
        with tempfile.NamedTemporaryFile("w") as f:
            # Write sample companion file.
            samples = ["sample1", "sample2", "sample3"]
            for sample in samples:
                f.write(sample + "\n")
            f.seek(0)

            self.db = MemoryImpute2Geno(
                resource_filename(__name__, "data/test_impute2_db.impute2"),
                samples=f.name,
            )

        self._variants = ["rs12345", "rs23456", "rs23457", "rs92134"]

    def test_get_samples(self):
        expected = np.array(["sample1", "sample2", "sample3"])
        self.assertTrue(np.all(self.db.samples == expected))

    def test_frozens(self):
        """Test the FrozenDatabaseError.

        This specific implementation of the AbstractGenoDB `freezes` the
        database after initialization with an experiment object. This is
        made to be sure that additional filtering is not attempted after
        the database is already populated. It is not a requirement of the
        interface (for now), but it makes for some safer code, especially
        during developpement.

        """
        self.db.experiment_init(self.experiment)
        self.assertRaises(FrozenDatabaseError, self.db.filter_completion, 0)
        self.assertRaises(FrozenDatabaseError, self.db.filter_maf, 0)
        self.assertRaises(FrozenDatabaseError, self.db.filter_name, 0)
        self.assertRaises(FrozenDatabaseError, self.db.exclude_samples, [])

    def test_init_method_call(self):
        """Test method calls specified during initialization.

        This is a mechanism used by the configuration parser. This module, when
        creating the instance for the genotype db, will pass around any
        additional field specified in the yaml configuration file. The db then
        interprets this as a method call and executes it.

        """
        with tempfile.NamedTemporaryFile("w") as f:
            # Write sample companion file.
            samples = ["sample1", "sample2", "sample3"]
            for sample in samples:
                f.write(sample + "\n")
            f.seek(0)

            self.db = MemoryImpute2Geno(
                resource_filename(__name__, "data/test_impute2_db.impute2"),
                samples=f.name,
                filter_maf=0.05
            )

    def test_init_bad_method_call(self):
        """Test a nonexisting method call specified during initialization."""
        with tempfile.NamedTemporaryFile("w") as f:
            # Write sample companion file.
            samples = ["sample1", "sample2", "sample3"]
            for sample in samples:
                f.write(sample + "\n")
            f.seek(0)

            self.assertRaises(
                ValueError,
                MemoryImpute2Geno,
                resource_filename(__name__, "data/test_impute2_db.impute2"),
                samples=f.name,
                test=0.05
            )

    def test_probability_filter(self):
        """Test impute2 probability filter."""
        self.db = self.get_probability_filtered_db()
        self.test_filter_completion()

    def test_probability_filter_strict(self):
        self.db = self.get_probability_filtered_db()
        self.test_filter_completion_strict()

    def test_probability_filter_mixed(self):
        self.db = self.get_probability_filtered_db()
        self.test_mixed_filters()

    def test_exclude_samples(self):
        samples_initial = self.db.get_sample_order()

        chosen = random.choice(samples_initial)
        self.db.exclude_samples([chosen])
        self.db.experiment_init(self.experiment)

        self.assertTrue(chosen in samples_initial)
        self.assertFalse(chosen in self.db.get_sample_order())

        # Get genotypes to see if size matches.
        geno = self.db.get_genotypes(self._variants[0])
        self.assertTrue(geno.shape[0] == (len(samples_initial) - 1))

    def test_exclude_bad_sample(self):
        self.assertRaises(ValueError, self.db.exclude_samples, ["testzzzz"])

    def test_exclude_sample_multiple(self):
        with tempfile.NamedTemporaryFile("w") as f:
            # Write sample companion file.
            samples = ["sample1", "sample1", "sample3"]
            for sample in samples:
                f.write(sample + "\n")
            f.seek(0)

            self.db = MemoryImpute2Geno(
                resource_filename(__name__, "data/test_impute2_db.impute2"),
                samples=f.name,
            )
        self.assertRaises(ValueError, self.db.exclude_samples, ["sample1"])

    def test_bulk_inserts(self):
        self.db.experiment_init(self.experiment, batch_insert_n=2)

        session = self.experiment.session
        db_vars = self.db.query_variants(session).all()
        db_vars = [i.name for i in db_vars]

        for variant in self._variants:
            self.assertTrue(variant in db_vars)

    def get_probability_filtered_db(self, p=0.89):
        """Utility function to get a memory impute2 db with a probability
        filter.

        """
        with tempfile.NamedTemporaryFile("w") as f:
            # Write sample companion file.
            samples = ["sample1", "sample2", "sample3"]
            for sample in samples:
                f.write(sample + "\n")
            f.seek(0)

            db = MemoryImpute2Geno(
                resource_filename(__name__, "data/test_impute2_db.impute2"),
                samples=f.name,
                filter_probability=p
            )

        return db

class TestPlinkGenoDB(TestAbstractGenoDB, unittest.TestCase):
    """Tests for PlinkGenotypeDatabase."""
    def setUp(self):
        super(TestPlinkGenoDB, self).setUp()
        filename = resource_filename(__name__, "data/simulated/sim.bim")
        base = os.path.abspath(filename)[:-4]

        self.db = PlinkGenotypeDatabase(base)

        self._variants = []
        with open(filename, "r") as f:
            for line in f:
                self._variants.append(line.rstrip().split()[1])
