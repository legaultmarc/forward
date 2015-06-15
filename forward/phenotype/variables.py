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

Variables are backed by the ORM using joined table inheritance. There is a main
class with basic information about the variable and subclasses with statistics
that are specific to discrete and continuous variables.
"""

from sqlalchemy import Column, Boolean, String, ForeignKey, Integer, Float, \
                       Enum
from sqlalchemy.ext.hybrid import hybrid_property

import numpy as np

from .. import SQLAlchemyBase


class Variable(SQLAlchemyBase):

    __tablename__ = "variables"

    name = Column(String(30), primary_key=True)
    is_covariate = Column(Boolean())
    n_missing = Column(Integer())
    variable_type = Column(Enum("discrete", "continuous"))

    __mapper_args__ = {
        "polymorphic_on": variable_type,
    }

    def compute_statistics(self, phenotypes_db):
        """Used by subclasses to initialize extra fields after filtering."""
        raise NotImplementedError()

    def __repr__(self):
        return "<{}: {}>".format(self.__class__.__name__, self.name)


class DiscreteVariable(Variable):
    __tablename__ = "discrete_variables"

    name = Column(String(30), ForeignKey("variables.name"), primary_key=True)
    n_cases = Column(Integer())
    n_controls = Column(Integer())

    __mapper_args__ = {
        "polymorphic_identity": "discrete"
    }

    def __init__(self, name, covariate=False):
        super(DiscreteVariable, self).__init__(
            name=name, is_covariate=covariate
        )

    def compute_statistics(self, phenotypes_db):
        """Compute some n values given the filtered phenotype database."""

        vect = phenotypes_db.get_phenotype_vector(self.name)
        self.n_cases = np.sum(vect == 1)
        self.n_controls = np.sum(vect == 0)
        self.n_missing = np.sum(np.isnan(vect))

    @hybrid_property
    def prevalence(self):
        return self.n_cases / (self.n_controls + self.n_cases)

class ContinuousVariable(Variable):
    __tablename__ = "continuous_variables"

    name = Column(String(30), ForeignKey("variables.name"), primary_key=True)
    mean = Column(Float())
    std = Column(Float())

    __mapper_args__ = {
        "polymorphic_identity": "continuous"
    }

    def __init__(self, name, covariate=False):
        super(ContinuousVariable, self).__init__(
            name=name, is_covariate=covariate
        )

    def compute_statistics(self, phenotypes_db):
        """Compute statistics with the filtered phenotype database."""

        vect = phenotypes_db.get_phenotype_vector(self.name)
        mask = ~np.isnan(vect)
        self.mean = vect[mask].mean()
        self.std = vect[mask].std()

        self.n_missing = np.sum(vect.shape[0] - np.sum(mask))

    def normality_check(self):
        raise NotImplementedError()
