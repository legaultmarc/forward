# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.


import random

import numpy as np

from ..phenotype.db import PhenotypeDatabaseInterface

class DummyPhenDB(PhenotypeDatabaseInterface):

    def __init__(self):
        # Create some samples.
        self.samples = []
        for i in range(100):
            self.samples.append("sample{}".format(i + 1))
        random.shuffle(self.samples)

        # Generate some data.
        np.random.seed(3)
        self.data = {
            "var1": 2 * np.random.rand(100),  # continous
            "var2": np.random.chisquare(2, 100),  # continous
            "var3": np.random.binomial(1, 0.1, 100),  # discrete
            "var4": np.random.binomial(1, 0.3, 100),  # discrete
            "var5": np.random.gamma(2, 2, 100),  # continous
        }

        # Insert some missings.
        for k in self.data.keys():
            mask = np.random.binomial(1, 0.01, 100).astype(bool)
            # Can't put NaN in int vector.
            self.data[k] = self.data[k].astype(float)
            self.data[k][mask] = np.nan

    def get_phenotypes(self):
        return self.data.keys()

    def get_phenotype_vector(self, name):
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
