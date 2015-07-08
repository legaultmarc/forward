# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

from __future__ import division

import random
import os
import shutil

import numpy as np

from ..phenotype.db import PhenotypeDatabaseInterface
from ..genotype import GenotypeDatabaseInterface, Variant
from ..experiment import Experiment
from .. import SQLAlchemySession


class DummyPhenDatabase(PhenotypeDatabaseInterface):
    """Implementation of the PhenotypeDatabaseInterface.

    This 'dummy' implementation is used for testing, but it is also a good
    example for people who want to write their own phenotype database parser.

    This specific class should be used to test components of the forward tool
    that need to interact with a phenotype database object.

    """
    def __init__(self, n=100):
        # Create some samples.
        self.samples = ["sample{}".format(i + 1) for i in range(n)]
        random.shuffle(self.samples)

        # Generate some data.
        np.random.seed(3)
        self.data = {
            "var1": 2 * np.random.rand(n),  # continous
            "var2": np.random.chisquare(2, n),  # continous
            "var3": np.random.binomial(1, 0.1, n),  # discrete
            "var4": np.random.binomial(1, 0.3, n),  # discrete
            "var5": np.random.gamma(2, 2, n),  # continous
            "var6": np.random.binomial(1, 0.8, n),  # discrete
        }

        # Insert some missings.
        for k in self.data.keys():
            mask = np.random.binomial(1, 0.01, n).astype(bool)
            # Can't put NaN in int vector.
            self.data[k] = self.data[k].astype(float)
            self.data[k][mask] = np.nan

    def get_phenotypes(self):
        return self.data.keys()

    def get_phenotype_vector(self, name):
        if hasattr(name, "name"):
            name = name.name  # Potentially a variable object.

        if name not in self.get_phenotypes():
            raise ValueError("{} not in database.".format(name))

        return self.data[name]

    def set_sample_order(self, sequence, allow_subset=False):
        self.validate_sample_sequences(
            self.get_sample_order(),
            sequence,
            allow_subset
        )

        # We need to change the order of the actual data.
        new_idx = [self.samples.index(i) for i in sequence]
        for k in self.data.keys():
            self.data[k] = self.data[k][new_idx]

        self.samples = sequence

    def get_sample_order(self):
        return self.samples

    def get_correlation_matrix(self, names):
        v = None
        for name in names:
            if v is None:
                v = self.get_phenotype_vector(name)
                continue

            v = np.vstack((v, self.get_phenotype_vector(name)))

        return np.corrcoef(v)


class DummyGenotypeDatabase(GenotypeDatabaseInterface):
    """Implementation of the GenotypeDatabaseInterface.

    This 'dummy' implementation is used for testing, but it is also a good
    example for people who want to write their own genotype file parser.

    This specific class should be used to test components of the forward tool
    that need to interact with a genotype database object.

    """
    def __init__(self, n=100):
        self.samples = [
            "sample{}".format(i + 1) for i in range(n)
        ]

        # Initialize filters.
        self.include_names = []
        self.maf_filter = 0
        self.completion_filter = 0

        # Create genotypes for 5 fictional markers.
        self.mafs = [0.05, 0.10, 0.15, 0.20, 0.25]
        self.genotypes = {}
        for snp in range(5):
            maf = self.mafs[snp]
            snp = "snp{}".format(snp + 1)

            # Select the samples that will have the reference homo. genotype
            mutation_prob = maf ** 2 + 2 * maf * (1 - maf)
            self.genotypes[snp] = np.random.binomial(
                1, mutation_prob, n
            ).astype(float)

            # Draw the heterozygotes and homo minors
            # Use the probability of being homo minor given that the sample
            # carries the mutation.
            p = maf ** 2
            p /= p + 2 * maf * (1 - maf)
            mutants = self.genotypes[snp] == 1
            n_mutants = np.sum(mutants)

            self.genotypes[snp][mutants] += np.random.binomial(
                1, p, n_mutants
            )

            # Add some no calls.
            missings = np.random.binomial(1, 0.02, n).astype(bool)
            self.genotypes[snp][missings] = np.nan

    def experiment_init(self, experiment):

        # Initialize the database.
        super(DummyGenotypeDatabase, self).experiment_init(experiment)

        # Filtering
        excludes = set()
        for snp in self.genotypes.keys():
            # maf filtering
            maf = np.nansum(self.genotypes[snp])
            maf /= (2 * self.genotypes[snp].shape[0])
            if maf < self.maf_filter:
                excludes.add(snp)
                continue

            # completion filtering
            completion = (np.sum(~np.isnan(self.genotypes[snp])) /
                          self.genotypes[snp].shape[0])
            if completion < self.completion_filter:
                excludes.add(snp)
                continue

        # name based filtering
        if self.include_names:
            excludes |= set(self.genotypes.keys()) - set(self.include_names)

        for snp in excludes:
            if snp in self.genotypes:  # pragma: no cover
                del self.genotypes[snp]

        chroms = [str(i + 1) for i in range(23)] + ["X", "Y"]
        variants = []
        for snp in self.genotypes:
            var = Variant(
                name=snp,
                chrom=random.choice(chroms),
                pos=random.randint(100, 9999999),
                mac=np.nansum(self.genotypes[snp]),
                n_missing=np.sum(np.isnan(self.genotypes[snp])),
                n_non_missing=np.sum(~np.isnan(self.genotypes[snp]))
            )
            variants.append(var)

        experiment.session.add_all(variants)
        experiment.session.commit()

    def get_genotypes(self, variant_name):
        try:
            return self.genotypes[variant_name]
        except KeyError:
            raise ValueError("Can't find variant '{}'.".format(variant_name))

    def filter_name(self, variant_list):
        if type(variant_list) in (tuple, list):
            self.include_names = variant_list

        else:
            with open(variant_list, "r") as f:
                self.include_names = set(f.read().splitlines())

    def filter_maf(self, maf):
        self.maf_filter = maf

    def filter_completion(self, rate):
        self.completion_filter = rate


class DummyExperiment(Experiment):
    """Dummy experiment to use for testing.
    
    This is used when testing the Genotype database interface to make sure
    that the database gets filled.

    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        self.name = ".fwd_test_experiment"

        # Create a directory for the experiment.
        try:
            os.makedirs(self.name)
        except OSError as e:  # pragma: no cover
            self.clean()

        # Create a sqlalchemy engine and bind it to the session.
        self.engine = self.get_engine(self.name, "sqlite")
        SQLAlchemySession.configure(bind=self.engine)
        self.session = SQLAlchemySession()

        self.results_init()

    def clean(self):
        shutil.rmtree(self.name)
