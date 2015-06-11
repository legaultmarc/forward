# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module is used to formalize the expected phenotype structure for forward.
It's role is to provide a reusable interface to feed phenotype (and covariate)
data to the statistical engine.

"""

import logging
logger = logging.getLogger(__name__)

import pandas as pd

from .variables import Variable


__all__ = ["ExcelPhenotypeDatabase"]


class PhenotypeDatabaseInterface(object):
    """Abstract class representing a collection of phenotypes."""

    def __init__(self):
        raise NotImplementedError()

    def get_phenotypes(self):
        raise NotImplementedError()

    def get_phenotype_vector(self, name):
        raise NotImplementedError()

    def set_sample_order(self, sequence):
        """Set the order of the samples."""
        raise NotImplementedError()

    def get_sample_order(self):
        """Get the order of the samples."""
        raise NotImplementedError()


class ExcelPhenotypeDatabase(PhenotypeDatabaseInterface):
    """Collection of phenotypes based on an Excel file.

    Only the first sheet is considered.

    """

    def __init__(self, filename, sample_column, missing_values=None):
        self.filename = filename

        self.data = pd.read_excel(filename, na_values=missing_values)

        # Set the sample column as the index.
        self.data = self.data.set_index(self.data[sample_column].astype(str))

        # User will be warned if the required sample order was not defined.
        self._order_is_set = False

    def get_phenotypes(self):
        return self.data.columns

    def set_sample_order(self, sequence, allow_subset=False):
        # Make sure that all the elements are in the provided sequence.
        set_phen = set(self.data.index.values)
        set_given = set(sequence)

        missing = set_phen - set_given
        extra = set_given - set_phen

        if not allow_subset and missing:
            message = ("Can't set the sequence because some entries are "
                       "missing resulting in ambiguous order.")
            raise ValueError(message)

        elif missing:
            message = ("Some samples were discarded when reordering "
                       "phenotype information ({} samples discarded). This "
                       "could be because no genotype information is "
                       "available for these samples.")
            message = message.format(len(missing))
            logger.warning(message)

        if extra:
            extra = ", ".join(extra)
            raise ValueError("Some of the given samples are not in the "
                             "phenotype database ({}).".format(extra))

        self.data = self.data.loc[sequence, :]
        self._order_is_set = True

    def get_sample_order(self):
        if not self._order_is_set:
            logger.warning("No sample order was given for the phenotype "
                           "database.")
        return self.data.index.values

    def get_phenotype_vector(self, name):
        if not self._order_is_set:
            logger.warning("The order of samples for the database has not "
                           "been set. Make sure that it is consistent with "
                           "the genetic database (consistent order).")

        # Potentially a Variable object.
        if hasattr(name, "name"):
            name = name.name

        if name not in self.data.columns:
            raise Exception("'{}' is not in the database.".format(name))

        return self.data.loc[:, name].values
