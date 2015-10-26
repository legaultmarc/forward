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
from ..utils import abstract, dispatch_methods, expand

__all__ = ["ExcelPhenotypeDatabase"]


@abstract
class AbstractPhenotypeDatabase(object):
    """Abstract class representing a collection of phenotypes.

    This class parses the phenotype information source (e.g. flat files, excel
    files, relational database or anything else).

    It is the responsibility of the phenotype database to handle phenotype
    based exclusions and transformations.

    """

    def __init__(self, **kwargs):
        dispatch_methods(self, kwargs)

    def get_phenotypes(self):
        """Returns a list of phenotypes available in this database.

        :returns: List of available phenotype names.
        :rtype: str

        """
        raise NotImplementedError()

    def get_phenotype_vector(self, name):
        """Returns a numpy array representing the selected outcome for all
        samples.

        :param name: The Variable object representing the phenotype to extract.
        :type name: :py:class:`forward.phenotype.variables.Variable`

        :returns: A vector representing the outcome.
        :rtype: :py:class:`numpy.ndarray`

        This is one of the most important methods as it is Forward's way of
        accessing all phenotypic information (it should be as efficient as
        possible). Missing values should be represented using Numpy NaNs.

        .. note::

            Experiment objects will call :py:func:`set_sample_order` with
            the results from the genotype container's
            :py:func:`get_sample_order` to ensure consistency. This means that
            the order of the samples in this vector should be the same as the
            sample order for the genotype container.

        """
        raise NotImplementedError()

    def set_experiment_variables(self, variables):
        """Signal by the experiment describing the subset of variables that
        will be analyzed.

        :param variables: List of
                          :py:class:`forward.phenotype.variables.Variable`
        :type variables: list

        This method can be used to compute the exclusions for discrete
        variables based on correlation.

        """
        raise NotImplementedError()

    def set_sample_order(self, sequence, allow_subset=False):
        """Set the order of the samples.

        :param sequence: List of sample IDs.
        :type sequence: list

        :param allow_subset: If true, the provided sequence is allowed to
                             contain only some of the IDs from the initial
                             list.
        :type allow_subset: bool

        """
        raise NotImplementedError()

    def get_sample_order(self):
        """Get the order of the samples.

        :returns: A list of samples in the same order as the phenotype vector.
        :rtype: list

        """
        raise NotImplementedError()

    def get_phenotype_relation_threshold(self):
        """Get the threshold set by exclude_correlated."""
        raise NotImplementedError()

    def exclude_correlated(self, threshold):
        """Exclude correlated samples from controls.

        :param threshold: A correlation coefficien threshold for exclusions.
        :type threshold: float

        In phenomic studies, it is common to exclude samples from controls if
        they are affected by a correlated phenotype. This is often described
        through the concept of "disease groups".

        A threshold of 0.8 means that if two discrete phenotypes A and B have
        a correlation coefficient >= 0.8, samples that are cases for A will
        be excluded from the control group of B and vice versa.

        """
        raise NotImplementedError()

    @staticmethod
    def validate_sample_sequences(old_seq, new_seq, allow_subset):
        """Compares sample sequences to validate the new sequence order.

        :param old_seq: The initial order of samples.
        :type old_seq: iterable

        :param new_seq: The new order of samples.
        :type new_seq: iterable

        :param allow_subset: If False, this method will raise ValueErrors if
                             the new sequence is a subset of the old sequence.
        :type allow_subset: bool

        This can optionally be used by subclasses when writing the
        `set_sample_order` method. We recommend using this method to properly
        log relevant information.

        If samples are missing from the new seq, a warning will be displayed.
        If new samples are added, a ValueError will be raised.

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

        self.variables = None

        # Call parent to dispatch method calls.
        super(PandasPhenotypeDatabase, self).__init__(**kwargs)

    def get_phenotypes(self):
        return list(self.data.columns)

    def set_experiment_variables(self, variables):
        self.variables = variables
        # Check if the user asked for exclusions.
        if not hasattr(self, "_exclusions_were_initialized"):
            return

        # Check if the exclusions were already initialized.
        if self._exclusions_were_initialized:
            raise Exception("Can't set the experiment variables after "
                            "exclusions were initialized.")

        # Compute the exclusions.
        names = [v.name for v in variables]
        mat = self.get_correlation_matrix(names)
        for var in variables:
            # Exclusions are irrelevant for quantitative traits.
            if var.variable_type != "discrete":
                continue
            if var.is_covariate:
                continue

            y = self.get_phenotype_vector(var)

            # Check for correlated variables.
            i = names.index(var.name)
            for j in np.where(abs(mat[i, :]) >= self._exclusion_threshold)[0]:
                if j != i:
                    # j is a candidate related outcome.
                    valid = (variables[j].variable_type == "discrete" and
                             not variables[j].is_covariate)
                    if valid:
                        # Exclude and write down.
                        related_phenotype_y = self.get_phenotype_vector(
                            variables[j]
                        )
                        mask = (y == 0) & (related_phenotype_y == 1)
                        self.data.loc[mask, var.name] = np.nan
                        n = np.sum(mask)
                        self._exclusion_mappings.add(
                            (var.name, names[j], mat[i, j], n)
                        )

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

    def get_phenotype_vector(self, variable, warn=True):
        if not self._order_is_set and warn:
            logger.warning("The order of samples for the database has not "
                           "been set. Make sure that it is consistent with "
                           "the genetic database (consistent order).")

        if not variable.is_variable():
            raise ValueError(
                "'{}' is not a Variable instance (type: {}).".format(
                    variable, type(variable)
                )
            )

        name = variable.name

        if name not in self.data.columns:
            raise ValueError("'{}' is not in the database.".format(name))

        vect = self.data.loc[:, name].values
        if variable.variable_type == "continuous" and variable.transformation:
            vect = apply_transformation(variable.transformation, vect)

        return vect

    def exclude_correlated(self, threshold):
        """This is called if the user specified it in the configuration.

        Because we need the Variables to properly compute the exclusions, we
        will just remember that the user wants exclusions and wait for the
        experiment to pass the variables to define the exclusion mappings.

        """
        self._exclusion_threshold = threshold
        self._exclusion_mappings = set()
        self._exclusions_were_initialized = False

    def get_phenotype_relation_threshold(self):
        return getattr(self, "_exclusion_threshold", None)

    def get_correlation_matrix(self, names):
        return self.data[names].corr().values


class CSVPhenotypeDatabase(PandasPhenotypeDatabase):
    """Collection of phenotypes based on a CSV file."""
    def __init__(self, filename, sample_column, **kwargs):
        self.filename = expand(filename)

        csv_allowed_kwargs = ["sep", "compression", "header", "skiprows",
                              "names", "na_values", "decimal"]
        csv_kwargs = {}
        for k in kwargs:
            if k in csv_allowed_kwargs:
                csv_kwargs[k] = kwargs.pop(k)

        self.data = pd.read_csv(self.filename, *csv_kwargs)

        # The arguments that are not feed to the pandas csv reader are assumed
        # to be method calls and will be dispatched by the parent.
        super(CSVPhenotypeDatabase, self).__init__(sample_column, **kwargs)


class ExcelPhenotypeDatabase(PandasPhenotypeDatabase):
    """Collection of phenotypes based on an Excel file.

    Only the first sheet is considered.

    """
    def __init__(self, filename, sample_column, missing_values=None, **kwargs):
        self.filename = expand(filename)
        self.data = pd.read_excel(self.filename, na_values=missing_values)
        super(ExcelPhenotypeDatabase, self).__init__(sample_column, **kwargs)


def apply_transformation(transformation, vector):
    """Apply a transformation to a continuous variable."""
    transformations = {
        "log": np.log,
        "inverse-normal-transform": inverse_normal_transformation,
    }

    if transformation not in transformations:
        raise ValueError("Invalid transformation '{}'.".format(transformation))
    else:
        return transformations[transformation](vector)
