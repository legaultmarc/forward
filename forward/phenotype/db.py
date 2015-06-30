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


# TODO refactor the ExcelPhenotypeDatabase to use a parent that is something
# like PandasBackedPhenotypeDatabase. This will allow us to easily extend to
# pandas compatible data types.


__all__ = ["ExcelPhenotypeDatabase"]


class PhenotypeDatabaseInterface(object):
    """Abstract class representing a collection of phenotypes."""

    def __init__(self):
        raise NotImplementedError()

    def get_phenotypes(self):
        raise NotImplementedError()

    def get_phenotype_vector(self, name):
        raise NotImplementedError()

    def set_sample_order(self, sequence, allow_subset=False):
        """Set the order of the samples."""
        raise NotImplementedError()

    def get_sample_order(self, allow_subset=False):
        """Get the order of the samples."""
        raise NotImplementedError()

    @staticmethod
    def validate_sample_sequences(old_seq, new_seq, allow_subset):
        """Compares sample sequences to validate the new sequence order.

        This can optionally be used by subclasses when writing the
        `set_sample_order` method. We recommend using to properly log relevant
        information.

        """
        # Make sure that all the elements are in the provided sequence.
        old_seq = set(old_seq)
        new_seq = set(new_seq)

        missing = old_seq - new_seq
        extra = new_seq - old_seq

        if (not allow_subset) and missing:
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

    def get_correlation_matrix(self, names):
        """Get a correlation matrix for the specified names.
        
        :param names: A list of variable names.
        :type names: list

        :returns: A correlation matrix.
        :rtype: numpy.ndarray

        This is useful to exclude correlated phenotypes as controls.
        """
        raise NotImplementedError()


class ExcelPhenotypeDatabase(PhenotypeDatabaseInterface):
    """Collection of phenotypes based on an Excel file.

    Only the first sheet is considered.

    """

    def __init__(self, filename, sample_column, missing_values=None):
        self.filename = filename

        self.data = pd.read_excel(filename, na_values=missing_values)

        # Set the sample column as the index.
        self.data = self.data.set_index(sample_column)

        # User will be warned if the required sample order was not defined.
        self._order_is_set = False

    def get_phenotypes(self):
        return list(self.data.columns)

    def set_sample_order(self, sequence, allow_subset=False):
        ExcelPhenotypeDatabase.validate_sample_sequences(
            self.get_sample_order(warn=False),
            sequence,
            allow_subset
        )

        self.data = self.data.loc[sequence, :]
        self._order_is_set = True

    def get_sample_order(self, warn=True):
        if not self._order_is_set and warn:
            logger.warning("No sample order was given for the phenotype "
                           "database.")
        return list(self.data.index.values)

    def get_phenotype_vector(self, name, warn=True):
        if not self._order_is_set and warn:
            logger.warning("The order of samples for the database has not "
                           "been set. Make sure that it is consistent with "
                           "the genetic database (consistent order).")

        # Potentially a Variable object.
        if hasattr(name, "name"):
            name = name.name

        if name not in self.data.columns:
            raise Exception("'{}' is not in the database.".format(name))

        return self.data.loc[:, name].values

    def get_correlation_matrix(self, names):
        return self.data[names].corr().values
