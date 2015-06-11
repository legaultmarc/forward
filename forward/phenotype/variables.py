# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

from __future__ import division

"""
Variables are used to choose what phenotypes are considered in a given
experiment.
"""

import numpy as np


class Variable(object):
    def __init__(self, name, phenotypes_db, covariate=False):
        self.is_covariate = covariate
        self.name = name
        self.phenotypes = phenotypes_db

    def __repr__(self):
        return "<{}: {}>".format(self.__class__.__name__, self.name)


class DiscreteVariable(Variable):
    def __init__(self, name, phenotypes_db, covariate=False):
        super(DiscreteVariable, self).__init__(name, phenotypes_db, covariate)

    def prevalence(self):
        """Computes the prevalence of a phenotype.

        This assumes that only 0, 1 and np.nan are in the vector.
        """
        vect = self.phenotype.get_phenotype_vector(self.name)
        return np.sum(vect == 1) / vect.shape[0]


class ContinuousVariable(Variable):
    def __init__(self, name, phenotypes_db, covariate=False):
        super(ContinuousVariable, self).__init__(name, phenotypes_db,
                                                 covariate)

    def normality_check(self):
        raise NotImplementedError()
