# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Test for the implementation of the various abstract classes defined by forward.
"""

from __future__ import division

import random
import tempfile
import string
import shutil

import six
import numpy as np

from . import dummies
from ..phenotype.variables import (Variable, ContinuousVariable,
                                   DiscreteVariable)
from ..genotype import Variant, FrozenDatabaseError
from ..experiment import Experiment


class TestAbstractPhenDB(object):
    """Test an implementation of AbstractPhenotypeDatabase.

    This can be used to test compliance to the interface expected by forward
    when working with phenotypic information.

    To test a custom class, use the following pattern: ::

        import unittest
        from forward.tests.abstract_tests import TestAbstractPhenDB

        class TestMyClass(TestAbstractPhenDB, unittest.TestCase):
            def setUp(self):
                self.db = MyClass()
                self._variables = ["var1", "var2", ...]

    The two mandatory parameters are `db`, an instance of the class
    implementing the interface and `_variables` a list containing the expected
    phenotypes represented in the instance.

    """
    def setUp(self):
        pass

    def test_get_phenotypes(self):
        """Check if all the column names are returned."""
        self.assertEqual(
            set(self.db.get_phenotypes()),
            set(self._variables)
        )

    def test_get_phenotype_vector(self):
        """Check the type and length of the generated variables."""
        n_samples = len(self.db.get_sample_order())
        for var in self.db.get_phenotypes():
            vec = self.db.get_phenotype_vector(var)
            self.assertEqual(vec.shape[0], n_samples)
            self.assertTrue(type(vec) is np.ndarray)

    def test_get_phen_vector_na(self):
        """Check what happens when we ask for a nonexisting vector."""
        # you give love a
        bad_name = "".join(
            [random.choice(string.ascii_lowercase) for _ in range(100)]
        )
        self.assertRaises(ValueError, self.db.get_phenotype_vector, bad_name)

    def test_get_phen_vector_variable(self):
        """Test accession using a variable object."""
        var = Variable(name=random.choice(self.db.get_phenotypes()))
        vec = self.db.get_phenotype_vector(var)
        self.assertTrue(type(vec) is np.ndarray)
        self.assertTrue(vec.shape[0], len(self.db.get_sample_order()))

    def test_get_sample_order(self):
        samples = self.db.get_sample_order()
        # Check type.
        self.assertTrue(type(samples) is list)

        # We can't test if we have no samples.
        self.assertTrue(len(samples) > 3)

        # Check that we're using strings.
        self.assertTrue(isinstance(samples[0], six.string_types))

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
        self.assertEqual(samples_perm, self.db.get_sample_order())

        # Check that the data was also reordered.
        for var in self._variables:
            np.testing.assert_equal(
                temp[var][permutation], self.db.get_phenotype_vector(var)
            )

    def test_set_sample_order_subset_raises(self):
        """Check if exceptions are raised when subsetting without allow_subset.

        """
        samples = self.db.get_sample_order()
        new_samples = samples[:]
        random.shuffle(new_samples)
        # Exclude half of the individuals.
        new_samples = new_samples[:(len(new_samples) // 2)]

        # Some samples are missing.
        self.assertRaises(ValueError, self.db.set_sample_order, new_samples)

    def test_set_sample_order_extra(self):
        """Check if an exception is raised when extra values are in there."""
        samples = self.db.get_sample_order()
        new_samples = samples[:]
        random.shuffle(new_samples)
        new_samples.append("extra1")
        self.assertRaises(ValueError, self.db.set_sample_order, new_samples)

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
        self.assertEqual(mat.shape, (3, 3))

        mat = self.db.get_correlation_matrix(self.db.get_phenotypes())
        self.assertEqual(mat.shape, (len(cols), len(cols)))


class TestAbstractGenoDB(object):
    """Test an implementation of AbstractGenotypeDatabase.

    This can be used to test compliance to the interface expected by forward
    when working with genotypic information.

    To test a custom class, use the following pattern: ::

        import unittest
        from forward.tests.abstract_tests import TestAbstractGenoDB

        class TestMyClass(TestAbstractGenoDB, unittest.TestCase):
            def setUp(self):
                self.db = MyClass()
                self._variants = ["var1", "var2", ...]

    The two mandatory parameters are `db`, an instance of the class
    implementing the interface and `_variants` a list containing the expected
    genetic variants represented in the instance.

    """

    def setUp(self):
        """Provide an experiment object."""
        self.experiment = dummies.DummyExperiment(genotype_container=self)

    def tearDown(self):
        self.experiment.clean()

    def test_frozen_db_error(self):
        exception = FrozenDatabaseError()
        message = ("Once initialized, genotype databases are immutable. "
                   "Further filtering needs to be done at the Task level.")
        self.assertEqual(str(exception), message)

    def test_get_genotypes(self):
        self.db.experiment_init(self.experiment)
        n_samples = len(self.db.get_sample_order())

        for var in self._variants:
            geno = self.db.get_genotypes(var)
            self.assertEqual(geno.shape[0], n_samples)

        # Hopefully, people will not use _testz as a variant name.
        self.assertRaises(ValueError, self.db.get_genotypes, "_testz")

    def test_variant_obj(self):
        """Test the behaviour of the Variant object."""
        self.db.experiment_init(self.experiment)
        query = self.experiment.session.query
        for var in query(Variant):
            geno = self.db.get_genotypes(var.name)
            self.assertTrue(hasattr(var, "chrom"))
            self.assertTrue(hasattr(var, "pos"))

            self.assertEqual(var.mac, np.nansum(geno))
            self.assertEqual(var.n_missing, np.sum(np.isnan(geno)))
            self.assertEqual(var.n_non_missing, np.sum(~np.isnan(geno)))

            # Hybrids
            self.assertEqual(
                var.maf,
                np.nansum(geno) / (2 * np.sum(~np.isnan(geno)))
            )
            self.assertEqual(
                var.completion_rate,
                np.sum(~np.isnan(geno)) / geno.shape[0]
            )

    def test_load_samples(self):
        """Test loading samples from file."""
        samples = np.array(["sample1", "sample2", "sample3"], dtype=str)
        with tempfile.NamedTemporaryFile(mode="w") as f:
            for sample in samples:
                f.write(sample + "\n")
            f.seek(0)
            loaded_samples = self.db.load_samples(f.name)

        self.assertTrue(np.all(loaded_samples == samples))

    def test_query_variants(self):
        """Test querying variants from the genotype db object."""
        self.db.experiment_init(self.experiment)
        session = self.experiment.session
        for variant in self.db.query_variants(session):
            self.assertTrue(variant.name in self._variants)

    def test_query_variants_field(self):
        """Test querying variants from the genotype db using single field."""
        self.db.experiment_init(self.experiment)
        session = self.experiment.session
        for name in self.db.query_variants(session, "name"):
            self.assertTrue(name[0] in self._variants)

    def test_query_variants_fields(self):
        """Test querying variants from the genotype db using multiple field."""
        self.db.experiment_init(self.experiment)
        session = self.experiment.session
        for name, mac in self.db.query_variants(session, ["name", "mac"]):
            self.assertTrue(name in self._variants)
            geno = self.db.get_genotypes(name)
            self.assertEqual(mac, np.nansum(geno))

    def test_query_variants_bad_field(self):
        """Test querying variants using a bad (nonexistant) field."""
        self.db.experiment_init(self.experiment)
        session = self.experiment.session
        self.assertRaises(ValueError, self.db.query_variants, session, "test")

    def test_query_variants_bad_field_in_list(self):
        """Test querying variants using a bad (nonexistant) field among
        existing fields.

        """
        self.db.experiment_init(self.experiment)
        session = self.experiment.session
        self.assertRaises(ValueError, self.db.query_variants, session, ["name",
                          "test"])

    def test_filter_maf(self):
        should_be_removed = set()
        info = []
        for var in self._variants:
            geno = self.db.get_genotypes(var)
            maf = np.nansum(geno) / (2 * geno.shape[0])
            info.append((var, maf))

        info = sorted(info, key=lambda x: x[1])
        maf_thresh = info[len(info) // 2][1] - 0.01
        for var, maf in info:
            if maf < maf_thresh:
                should_be_removed.add(var)

        self.db.filter_maf(maf_thresh)

        # Apply the filtering and fill the DB.
        self.db.experiment_init(self.experiment)

        expected = set(self._variants) - should_be_removed
        self.compare_variant_db(expected)

    def test_filter_completion(self):
        should_be_removed = set()
        for var in self._variants:
            geno = self.db.get_genotypes(var)

            completion = np.sum(~np.isnan(geno)) / geno.shape[0]
            if completion < 0.98:
                should_be_removed.add(var)

        self.db.filter_completion(0.98)
        self.db.experiment_init(self.experiment)

        expected = set(self._variants) - should_be_removed
        self.compare_variant_db(expected)

    def test_filter_completion_strict(self):
        should_be_removed = set()
        for var in self._variants:
            geno = self.db.get_genotypes(var)

            completion = np.sum(~np.isnan(geno)) / geno.shape[0]
            if completion < 1:
                should_be_removed.add(var)

        self.db.filter_completion(1)
        self.db.experiment_init(self.experiment)

        expected = set(self._variants) - should_be_removed
        self.compare_variant_db(expected)

    def test_filter_name_list(self):
        # Randomly choose 2 to exclude.
        should_be_removed = set(
            [random.choice(self._variants) for _ in range(2)]
        )

        expected = set(self._variants) - should_be_removed
        self.db.filter_name(list(expected))
        self.db.experiment_init(self.experiment)

        self.compare_variant_db(expected)

    def test_filter_name_file(self):
        # Randomly choose 3 to exclude.
        should_be_removed = set(
            [random.choice(self._variants) for _ in range(3)]
        )
        expected = set(self._variants) - should_be_removed

        with tempfile.NamedTemporaryFile(mode="w") as f:
            for snp in expected:
                f.write("{}\n".format(snp))
            f.seek(0)
            self.db.filter_name(f.name)

        self.db.experiment_init(self.experiment)

        self.compare_variant_db(expected)

    def test_mixed_filters(self):
        maf_thresh = 0
        completion_thresh = 0
        names = []

        for var in self._variants:
            geno = self.db.get_genotypes(var)

            completion_thresh += np.sum(~np.isnan(geno)) / geno.shape[0]
            maf_thresh += np.nansum(geno) / (2 * geno.shape[0])
            if random.random() < 0.3:
                names.append(var)  # Exclude with p = 0.3

        maf_thresh /= len(self._variants)
        completion_thresh /= len(self._variants)

        should_be_removed = set()
        for var in self._variants:
            geno = self.db.get_genotypes(var)

            maf = np.nansum(geno) / (2 * geno.shape[0])
            completion = np.sum(~np.isnan(geno)) / geno.shape[0]

            remove_flag = (maf < maf_thresh or
                           completion < completion_thresh or
                           var in names)
            if remove_flag:
                should_be_removed.add(var)

        self.db.filter_maf(maf_thresh)
        self.db.filter_completion(completion_thresh)
        self.db.filter_name(list(set(self._variants) - set(names)))

        self.db.experiment_init(self.experiment)

        expected = set(self._variants) - should_be_removed
        self.compare_variant_db(expected)

    def compare_variant_db(self, expected):
        query = self.experiment.session.query
        db_names = set([i[0] for i in query(Variant.name).all()])
        self.assertEqual(db_names, expected)


class TestAbstractTask(object):
    """Test an implementation of AbstractTask.

    This can be used to test compliance to the interface expected by forward
    when defining new tasks.

    To test a custom class, use the following pattern: ::

        import unittest
        from forward.tests.abstract_tests import TestAbstractTask

        class TestMyClass(TestAbstractTask, unittest.TestCase):
            def setUp(self):
                self.task = MyClass()  # That subclasses AbstractTask

    You need to provide an instance of the task object you want to test.

    """
    def setUp(self):
        variables = [
            ContinuousVariable("var1"),
            ContinuousVariable("var2"),
            DiscreteVariable("var3"),
            DiscreteVariable("var4"),
            ContinuousVariable("var5", covariate=True),
            DiscreteVariable("var6", covariate=True),
        ]

        self.experiment = Experiment(
            name=".fwd_test_tasks",
            phenotype_container=dummies.DummyPhenDatabase(),
            genotype_container=dummies.DummyGenotypeDatabase(),
            variables=variables,
            tasks=[self.task],
            cpu=1
        )

    def tearDown(self):
        shutil.rmtree(".fwd_test_tasks")

    def test_constructor_outcomes(self):
        t2 = dummies.DummyTask(outcomes=["var3"])
        self.experiment.tasks.append(t2)
        self.experiment.run_tasks()

        self.assertTrue(len(t2.outcomes) == 1)
        self.assertTrue(t2.outcomes[0].name == "var3")

    def test_constructor_covariates(self):
        t2 = dummies.DummyTask(covariates=["var5"])
        self.experiment.tasks.append(t2)
        self.experiment.run_tasks()

        self.assertTrue(len(t2.covariates) == 1)
        self.assertTrue(t2.covariates[0].name == "var5")

    def test_meta(self):
        self.task.set_meta("test", "test")
        self.assertEqual(self.task.get_meta("test"), "test")
