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
import numpy as np
from ..statistics.utilities import inverse_normal_transformation
from ..utils import abstract, dispatch_methods
from .variables import ContinuousVariable

__all__ = ["ExcelPhenotypeDatabase"]


@abstract
class AbstractPhenotypeDatabase(object):
    """Abstract class representing a collection of phenotypes.

    It is the responsibility of the phenotype database to handle phenotype
    based exclusions and transformations.

    """

    def __init__(self, **kwargs):
        dispatch_methods(self, kwargs)

    def get_phenotypes(self):
        raise NotImplementedError()

    def get_phenotype_vector(self, name):
        """Returns a numpy array representing the selected outcome for all
        samples.

        :param name: The name of the phenotype to extract.
        :type name: str, unicode or
                    :py:class:`forward.phenotype.variables.Variable`

        :returns: A vector representing the outcome.
        :rtype: :py:class:`numpy.ndarray`

        """
        raise NotImplementedError()

    def set_sample_order(self, sequence, allow_subset=False):
        """Set the order of the samples."""
        raise NotImplementedError()

    def get_sample_order(self, allow_subset=False):
        """Get the order of the samples."""
        raise NotImplementedError()

    def exclude_correlated(self, threshold):
        """Exclude correlated samples from controls.

        In phenomic studies, it is common to exclude samples from controls if
        they are affected by a correlated phenotype.

        """
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

@abstract
class PandasPhenotypeDatabase(AbstractPhenotypeDatabase):
    def __init__(self, sample_column, **kwargs):
        # Set the sample column as the index.
        self.data[sample_column] = self.data[sample_column].astype(str)
        self.data = self.data.set_index(sample_column, verify_integrity=True)

        # User will be warned if the required sample order was not defined.
        self._order_is_set = False

        # Call parent to dispatch method calls.
        super(PandasPhenotypeDatabase, self).__init__(**kwargs)

        # Keep the correlation matrix for lazy loading.
        self._corr_mat = None

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
            raise ValueError("'{}' is not in the database.".format(name))

        vect =  self.data.loc[:, name].values
        if isinstance(name, ContinuousVariable) and name.transformation:
            vect = apply_transformation(name.transformation, vect)

        # Check if we need to exclude phenotypes.
        if hasattr(self, "_exclusion_mapper"):
            for phen in self._exclusion_mapper(name):
                corr_y = self.data.loc[:, name].values
                # Exclude samples that don't have the current phenotype but
                # that are affected with a correlated phenotype.
                vect[(corr_y == 1) & (vect == 0)] = np.nan

        return vect

    def exclude_correlated(self, threshold):
        """Define a private function that will be used for filtering based on
        phenotype correlation.

        """

        ys = self.get_phenotypes()
        m = self.get_correlation_matrix(ys) >= threshold

        def f(phenotype):
            x = ys.index(phenotype)
            exclusions = []
            for j in np.where(m[x, :])[0]:
                if j != x:
                    exclusions.append(ys[j])

            return exclusions

        self._exclusion_mapper = f

    def get_correlation_matrix(self, names):
        return self.data[names].corr().values


class CSVPhenotypeDatabase(PandasPhenotypeDatabase):
    """Collection of phenotypes based on a CSV file."""
    def __init__(self, filename, sample_column, **kwargs):
        self.filename = filename

        csv_allowed_kwargs = ["sep", "compression", "header", "skiprows",
                              "names", "na_values", "decimal"]
        csv_kwargs = {}
        for k in kwargs:
            if k in csv_allowed_kwargs:
                csv_kwargs[k] = kwargs.pop(k)

        self.data = pd.read_csv(filename, *csv_kwargs)

        # The arguments that are not feed to the pandas csv reader are assumed
        # to be method calls and will be dispatched by the parent.
        super(CSVPhenotypeDatabase, self).__init__(sample_column, **kwargs)


class ExcelPhenotypeDatabase(PandasPhenotypeDatabase):
    """Collection of phenotypes based on an Excel file.

    Only the first sheet is considered.

    """
    def __init__(self, filename, sample_column, missing_values=None, **kwargs):
        self.filename = filename
        self.data = pd.read_excel(filename, na_values=missing_values)
        super(ExcelPhenotypeDatabase, self).__init__(sample_column, **kwargs)


def apply_transformation(transformation, vector):
    """Apply a transformation to a continuous variable."""
    transformations = {
        "log": np.log,
        "inverse-normal-transform": inverse_normal_transformation,
    }

    if transformation not in transformations:
        return vector
    else:
        return transformations[transformation](vector)
