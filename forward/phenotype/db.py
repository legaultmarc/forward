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


__all__ = ["ExcelPhenotypeDatabase"]


class PhenotypeDatabaseInterface(object):
    """Abstract class representing a collection of phenotypes."""

    def __init__(self):
        raise NotImplementedError()

    def get_phenotype_vector(self, name):
        raise NotImplementedError()

    def set_order(self, sequence):
        """Set the order of the samples."""
        raise NotImplementedError()

    def get_order(self):
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
        self.data = self.data.set_index(self.data[sample_column])

    def set_order(self, sequence):
        # Make sure that all the elements are in the provided sequence.
        missing = set(self.data.index.values) - set(sequence)
        if missing:
            message = ("Can't set the sequence because some entries are "
                       "missing resulting in ambiguous order.")
            raise ValueError(message)

        self.data = self.data.loc[sequence, :]

    def get_order(self):
        return self.data.index.values

    def get_phenotype_vector(self, name):
        if name not in self.data.columns:
            raise Exception("'{}' is not in the database.".format(name))

        return self.data.loc[:, name].values
