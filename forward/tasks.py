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
import multiprocessing
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

from six.moves import cPickle as pickle
from six.moves import range
import numpy as np


try:  # pragma: no cover
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    STATSMODELS_AVAILABLE = False


from .phenotype.variables import DiscreteVariable, ContinuousVariable
from .utils import abstract, Parallel


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
        logger.info("Running a logistic regression analysis.")
        if not STATSMODELS_AVAILABLE:  # pragma: no cover
            raise ImportError("LogisticTest class requires statsmodels. "
                              "Install the package first (and patsy).")
        super(LogisticTest, self).__init__(*args, **kwargs)

    def filter_variables(self):
        # Filter outcomes to remove non discrete variables.
        self.outcomes = [i for i in self.outcomes if
                         isinstance(i, DiscreteVariable)]


    def run_task(self, experiment, task_name, work_dir):
        """Run the logistic regression."""
        super(LogisticTest, self).run_task(experiment, task_name, work_dir)

        self.filter_variables()

        # Get a database session from the experiment.
        session = experiment.session

        # Get the list of variants to analyze.
        # No extra filtering for now (TODO).
        variants = experiment.genotypes.query_variants(session, "name").all()
        variants = [i[0] for i in variants]  # Keep only the names.

        self.parallel = Parallel(experiment.cpu, self._work)

        num_tests = 0
        for variant in variants:
            # Get the genotype vector.
            x = experiment.genotypes.get_genotypes(variant)

            # Statsmodel does not automatically add an intercept term, so we
            # need to do it manually here.
            x = np.vstack((np.ones(x.shape[0]), x))

            # Get the covariates and build the design matrix.
            # We assume a design matrix with ones as a first column, and the
            # outcome as the second column, with covariates after.
            for covar in self.covariates:
                covar = experiment.phenotypes.get_phenotype_vector(covar)
                x = np.vstack((x, covar))

            x = x.T  # Transpose to have variables as columns.

            # Get the phenotypes and fill the job queue.
            for phenotype in self.outcomes:
                y = experiment.phenotypes.get_phenotype_vector(phenotype)
                missing = np.isnan(x).any(axis=1) | np.isnan(y)

                self.parallel.push_work(
                    (variant, phenotype, x[~missing, :], y[~missing])
                )
                num_tests += 1

        self.parallel.done_pushing()

        # We can start parsing the results.
        while num_tests > 0:
            results = self.parallel.get_result()
            # Process the result.
            experiment.add_result("variant", task_name, *results)
            num_tests -= 1

    def handle_sm_results(self, res, outcome_column):
        p = res.pvalues[outcome_column]
        beta = res.params[outcome_column]
        std_err = res.bse[outcome_column]

        conf_int = res.conf_int()
        if type(conf_int) is not np.ndarray:
            conf_int = conf_int.values
        ic95_min, ic95_max = conf_int[outcome_column, :]

        return [p, beta, std_err, ic95_min, ic95_max]

    def _work(self, variant, phenotype, x, y, outcome_column=1):
        """Run a logistic test using the y ~ x model."""
        try:
            glm = sm.GLM(y, x, family=sm.families.Binomial())
            res = glm.fit()
            res = self.handle_sm_results(res, outcome_column)
            res = tuple([variant, phenotype] + res)
        except Exception:
            logging.exception("")  # Log the exception and insert nulls in db.
            res = tuple([None for _ in range(7)])

        return res


class LinearTest(LogisticTest):
    """Linear regression genetic test."""
    logger.info("Running a linear regression analysis.")
    def __init__(self, *args, **kwargs):
        if not STATSMODELS_AVAILABLE:  # pragma: no cover
            raise ImportError("LinearTest class requires statsmodels. "
                              "Install the package first (and patsy).")
        super(LinearTest, self).__init__(*args, **kwargs)

    def filter_variables(self):
        # Filter outcomes to remove non discrete variables.
        self.outcomes = [i for i in self.outcomes if
                         isinstance(i, ContinuousVariable)]

    def _work(self, variant, phenotype, x, y, outcome_column=1):
        try:
            ols = sm.OLS(y, x)
            res = ols.fit()
            res = self.handle_sm_results(res, outcome_column)
            res = tuple([variant, phenotype] + res)
        except Exception:
            logging.exception("")  # Log the exception and insert nulls in db.
            res = tuple([None for _ in range(7)])

        return res
