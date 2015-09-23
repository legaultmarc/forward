# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides actual implementations of the genetic tests.
"""

import os
import collections
import multiprocessing
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

from sqlalchemy import Column, Float, ForeignKey, String, Integer
from six.moves import cPickle as pickle
from six.moves import range
import numpy as np


try:  # pragma: no cover
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    STATSMODELS_AVAILABLE = False


from . import SQLAlchemySession, SQLAlchemyBase
from .phenotype.variables import DiscreteVariable, ContinuousVariable
from .utils import abstract, Parallel
from .experiment import ExperimentResult, result_table


__all__ = ["LogisticTest", ]


@abstract
class AbstractTask(object):
    """Class representing a task (genetic test)."""
    def __init__(self, outcomes="all", covariates="all", variants="all",
                 correction=None, alpha=0.05):
        self.outcomes = outcomes
        self.covariates = covariates
        self.variants = variants
        self.correction = correction
        self.alpha = alpha

        # This will be automatically serialized when the task finishes.
        self._info = {}
        self.task_meta_path = None

    def run_task(self, experiment, task_name, work_dir):
        self.work_dir = work_dir

        # Select the variables and covariates to analyse.
        if self.outcomes == "all":
            self.outcomes = [i for i in experiment.variables
                             if not i.is_covariate]
        else:
            self.outcomes = [i for i in experiment.variables
                             if i.name in self.outcomes]

        if self.covariates == "all":
            self.covariates = [i for i in experiment.variables
                               if i.is_covariate]
        else:
            self.covariates = [i for i in experiment.variables
                               if i.name in self.covariates]

        if self.variants != "all":
            raise NotImplementedError()

        # Set meta information for serialization.
        for meta_key in ("outcomes", "covariates", "variants"):
            value = getattr(self, meta_key)
            # List of variables.
            if type(value) is list:
                self.set_meta(
                    meta_key,
                    [i.name for i in getattr(self, meta_key)]
                )
            else:
                self.set_meta(meta_key, value)

        for meta_key in ("correction", "alpha"):
            self.set_meta(meta_key, getattr(self, meta_key))

    def set_meta(self, key, value):
        """Set meta information about this task."""
        self._info[key] = value

    def get_meta(self, key):
        """Get meta information about this task."""
        return self._info.get(key)

    def done(self):
        """By default, this writes the content of the info attribute to disk.

        This can be used to communicate with the report module or to store
        meta information about this task's execution.

        The pattern for storing task associated information is to use the
        `set_meta` and `get_meta` methods.

        """
        self.task_meta_path = os.path.join(self.work_dir, "task_info.pkl")
        with open(self.task_meta_path, "wb") as f:
            pickle.dump(self._info, f)


class LogisticTest(AbstractTask):
    """Logistic regression genetic test."""
    def __init__(self, *args, **kwargs):
        if not STATSMODELS_AVAILABLE:  # pragma: no cover
            raise ImportError("LogisticTest class requires statsmodels. "
                              "Install the package first (and patsy).")
        super(LogisticTest, self).__init__(*args, **kwargs)

    def filter_variables(self):
        # Filter outcomes to remove non discrete variables.
        self.outcomes = [i for i in self.outcomes if
                         isinstance(i, DiscreteVariable)]

    def prep_task(self, experiment, *args):
        self._add_result = experiment.add_result
        logger.info("Running a logistic regression analysis.")

    def run_task(self, experiment, task_name, work_dir):
        """Run the logistic regression."""
        super(LogisticTest, self).run_task(experiment, task_name, work_dir)
        self.prep_task(experiment, task_name, work_dir)

        # Keep only discrete or continuous variables.
        self.filter_variables()

        # Get a database session from the experiment.
        session = experiment.session

        # Get the list of variants to analyze.
        # No extra filtering for now (TODO).
        variants = experiment.genotypes.query_variants(session, "name").all()
        variants = [i[0] for i in variants]  # Keep only the names.

        self.parallel = Parallel(experiment.cpu, self._work)

        num_tests = 0

        # Build the covariate matrix.
        covar_matrix = np.vstack(tuple([
            experiment.phenotypes.get_phenotype_vector(covar)
            for covar in self.covariates
        ]))

        # Add the intercept because statsmodels does not add it automatically.
        covar_matrix = np.vstack(
            (np.ones(covar_matrix.shape[1]), covar_matrix)
        )
        covar_matrix = covar_matrix.T
        missing_covar = np.isnan(covar_matrix).any(axis=1)

        for phenotype in self.outcomes:
            y = experiment.phenotypes.get_phenotype_vector(phenotype)
            missing_outcome = np.isnan(y)

            for variant in variants:
                # Get the genotype vector.
                x = experiment.genotypes.get_genotypes(variant)
                missing_genotypes = np.isnan(x)

                x.shape = (x.shape[0], 1)
                x = np.hstack((x, covar_matrix))

                missing = (missing_covar | missing_genotypes | missing_outcome)

                self.parallel.push_work(
                    (variant, phenotype, x[~missing, :], y[~missing], 0)
                )
                num_tests += 1

        self.parallel.done_pushing()

        # We can start parsing the results.
        while num_tests > 0:
            results = self.parallel.get_result()
            # Process the result.
            self._add_result(
                tested_entity="variant",
                task_name=task_name,
                **results
            )

            num_tests -= 1

    def handle_sm_results(self, res, genetic_col):
        conf_int = res.conf_int()
        if type(conf_int) is not np.ndarray:
            conf_int = conf_int.values
        ic95_min, ic95_max = conf_int[genetic_col, :]

        return {
            "results_type": "GenericResults",
            "significance": res.pvalues[genetic_col],
            "coefficient": res.params[genetic_col],
            "standard_error": res.bse[genetic_col],
            "confidence_interval_min": ic95_min,
            "confidence_interval_max": ic95_max,
            "test_statistic": res.tvalues[genetic_col]
        }

    def _work(self, variant, phenotype, x, y, genetic_col):
        """Run a logistic test using the y ~ x model."""
        try:
            glm = sm.GLM(y, x, family=sm.families.Binomial())
            res = glm.fit()
            res = self.handle_sm_results(res, genetic_col)
            res["entity_name"] = variant
            res["phenotype"] = phenotype.name

        except Exception:
            # Log the exception and insert nulls in db.
            logging.exception("")
            res = collections.defaultdict(lambda: None)

        return res


@result_table
class LinearTestResults(ExperimentResult):
    """Table for extra statistical reporting for linear regression.

    It is interesting to report the standardized beta to easily compare the
    effect size between different outcomes (that have different units). We
    will also report the coefficient of determination (R^2) that reports the
    fraction of explained variance.

    """
    __tablename__ = "linreg_results"

    pk = Column(Integer(), ForeignKey("results.pk"), primary_key=True)

    adjusted_r_squared = Column(Float())
    std_beta = Column(Float())
    std_beta_min = Column(Float())
    std_beta_max = Column(Float())

    __mapper_args__ = {
        "polymorphic_identity": "LinearTest",
    }


class LinearTest(LogisticTest):
    """Linear regression genetic test."""
    def __init__(self, *args, **kwargs):
        if not STATSMODELS_AVAILABLE:  # pragma: no cover
            raise ImportError("LinearTest class requires statsmodels. "
                              "Install the package first (and patsy).")
        super(LinearTest, self).__init__(*args, **kwargs)

        # Check if we need to report the standardized beta.
        self._compute_std_beta = kwargs.get(
            "compute_standardized_beta", True
        )


    def prep_task(self, experiment, task_name, work_dir):
        logger.info("Running a linear regression analysis.")
        def _f(**params):
            result = LinearTestResults(**params)
            experiment.session.add(result)

        self._add_result = _f

    def filter_variables(self):
        # Filter outcomes to remove non discrete variables.
        self.outcomes = [i for i in self.outcomes if
                         isinstance(i, ContinuousVariable)]

    def _work(self, variant, phenotype, x, y, genetic_col):
        try:
            ols = sm.OLS(y, x)
            res = ols.fit()

            result = self.handle_sm_results(res, genetic_col)
            result["results_type"] = "LinearTest"
            result["entity_name"] = variant
            result["phenotype"] = phenotype.name

            # Linear specific.
            result["adjusted_r_squared"] = res.rsquared_adj

            if self._compute_std_beta:
                # Recompute to get standardized coefficient.
                std_x = (x - np.mean(x, axis=0)) / np.std(x, axis=0)
                # Restore the intercept term.
                # Be careful what column you use here if you change the
                # design matrix.
                std_x[:, 1] = 1

                ols = sm.OLS((y - np.mean(y)) / np.std(y), std_x)
                res = ols.fit()
                result["std_beta"] = res.params[genetic_col]
                conf_int = res.conf_int()
                if type(conf_int) is not np.ndarray:
                    conf_int = conf_int.values

                result["std_beta_min"] = conf_int[genetic_col, 0]
                result["std_beta_max"] = conf_int[genetic_col, 1]

        except Exception:
            logging.exception("")
            result = collections.defaultdict(lambda: None)

        return result
