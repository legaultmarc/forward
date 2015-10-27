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
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

from sqlalchemy import Column, Float, ForeignKey, Integer
from six.moves import cPickle as pickle
import numpy as np
import pandas as pd


try:  # pragma: no cover
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    STATSMODELS_AVAILABLE = False


from .phenotype.variables import DiscreteVariable, ContinuousVariable
from .genotype import MemoryImpute2Geno
from .utils import abstract, Parallel, check_rpy2
from .experiment import ExperimentResult, result_table


__all__ = ["LogisticTest", "LinearTest", "SKATTest"]


@abstract
class AbstractTask(object):
    """Abstract class for genetic tests.

    :param outcomes: (optional) List of Variable names to include as outcomes
                     for this task. Alternatively, "all" can be passed.
    :type outcomes: list or str

    :param covariates: (optional) List of Variable names to include as
                       covariates.
    :type covariates: list or str

    :param variants: List of variants. For now, we can't subset at the task
                     level, so this should either not be passed or be "all".
    :type variants: str

    :param correction: The multiple hypothesis testing correction. This will be
                       automatically serialized in the task metadata (if the
                       parent's method is called).
    :type correction: str

    :param alpha: Significance threshold (default: 0.05). This will be
                  automatically serialized it the parent's method is called.
    :type alpha: float

    Implementations of this class should either compute the statistics directly
    or manage the execution of external statistical programs and parse the
    results.

    The ``run_task`` method will be called by the experiment and should result
    in the statistical analysis.

    When the task is done, the experiment will call the ``done`` method which
    should take care of dumping metadata.

    """
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
        """Method that triggers statistical computation.

        :param experiment: The parent experiment which provides access to
                           the whole experimental context.
        :type experiment: :py:class:`forward.experiment.Experiment`

        :param task_name: The name of the task. This is useful to fill the
                          results table, because the task name is one of the
                          columns.
        :type task_name: str

        :param work_dir: Path to the Task's work directory that was created by
                         the experiment.
        :type work_dir: str

        For implementations of this abstract class, calling the parent method
        will set the outcomes and covariates to filtered lists of Variable
        objects. It will also make sure that the outcomes, covariates,
        variants, alpha and correction are included as task metadata.

        """
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
        """Set meta information about this task.

        This will be pickle serialzed to this Task's work directory. It can
        subsequently be used by the backend and the dynamic report.

        """
        self._info[key] = value

    def get_meta(self, key):
        """Get meta information about this task."""
        return self._info.get(key)

    def done(self):
        """Cleanup signal from the Experiment.

        The abstract method writes the content of the info attribute to disk.

        """
        self.task_meta_path = os.path.join(self.work_dir, "task_info.pkl")
        with open(self.task_meta_path, "wb") as f:
            pickle.dump(self._info, f)


class InvalidSNPSet(Exception):
    def __init__(self, value=None):
        self.value = value
        if self.value is None:
            self.value = ("The SNP Set file needs to have a header line with "
                          "a 'variant' and a 'set' column. These indicate the "
                          "variant IDs and their respective user-defined set "
                          "for the agregate analysis, repsectively. "
                          "The file needs to be *whitespace* delimited.")



class SKATTest(AbstractTask):
    """Binding to SKAT (using rpy2)."""
    def __init__(self, *args, **kwargs):

        # Task specific arguments.
        self.snp_set = kwargs.pop("snp_set_file", None)
        if self.snp_set:
            filename = self.snp_set
            self.snp_set = self._parse_snp_set(self.snp_set)

            m = ("Using SNP sets from '{}'. Found a total of {} variants in {}"
                 " different SNP sets.")
            m = m.format(filename, self.snp_set.shape[0],
                         self.snp_set["set"].nunique())
            logger.info(m)

        self.skat_o = kwargs.pop("SKAT-O", False)
        if self.skat_o:
            logger.info("Using the SKAT-O test.")

        # Task initalization using the abstract implementation.
        super(SKATTest, self).__init__(*args, **kwargs)

        # Check installation.
        SKATTest.check_skat()

        # Import rpy2.
        from rpy2.robjects import numpy2ri
        numpy2ri.activate()  # Support for numpy arrays.

        import rpy2.robjects
        self.robjects = rpy2.robjects
        self.r = rpy2.robjects.r

        from rpy2.robjects.packages import importr

        # Load the SKAT package.
        try:
            self.skat = importr("SKAT")
        except Exception:
            raise EnvironmentError(
                1,
                "SKAT needs to be installed in your R environment to use "
                "SKATTest."
            )

    def _parse_snp_set(self, filename):
        """Parse a SNP set file with a `variant` and a `set` column."""
        data = pd.read_csv(filename, delim_whitespace=True, header=0)
        data.columns = [i.lower() for i in data.columns]
        if {"variant", "set"} - set(data.columns):
            raise InvalidSNPSet()

        data = data[["variant", "set"]]
        if data.shape[1] != 2:
            raise InvalidSNPSet("Duplicate columns in SNP set file. Note that "
                                "columns names are case insensitive.")

        data["set"] = data["set"].astype("category")

        return data

    def run_task(self, experiment, task_name, work_dir):
        """Run the SKAT analysis."""
        super(SKATTest, self).run_task(experiment, task_name, work_dir)
        logger.info("Running the SKAT analysis.")

        # Check if the snp set was correctly initialized.
        if getattr(self, "snp_set") is None:
            raise InvalidSNPSet("You need to provide a snp set for SKAT "
                                "analyses. Use the `snp_set_file` command "
                                "in the SKATTest definition.")

        set_names = set(self.snp_set["set"].unique())

        # Check if we have dosage or genotypes.
        is_dosage = isinstance(experiment.genotypes, MemoryImpute2Geno)

        # Build the covariate matrix.
        covar_matrix = np.array([
            experiment.phenotypes.get_phenotype_vector(covar)
            for covar in self.covariates
        ]).T
        missing_covar = np.isnan(covar_matrix).any(axis=1)

        for phenotype in self.outcomes:
            y = experiment.phenotypes.get_phenotype_vector(phenotype)
            missing_outcome = np.isnan(y)

            outcome_type = ("D" if isinstance(phenotype, DiscreteVariable)
                            else "C")

            for set_name in set_names:
                # Get the variants in the current set.
                variants = self.snp_set.loc[
                    self.snp_set["set"] == set_name, "variant"
                ]

                # x is the genotype matrix
                x = np.array([
                    experiment.genotypes.get_genotypes(variant)
                    for variant
                    in variants
                ]).T
                missing_geno = np.isnan(x).any(axis=1)

                # Handle missing values on the Python side (to be safe).
                missing = (missing_covar | missing_outcome | missing_geno)
                not_missing = ~missing

                # Pass stuff to the R global environment.
                self.robjects.globalenv["y"] = y[not_missing]
                self.robjects.globalenv["covar"] = covar_matrix[not_missing, :]

                # For now, we build a null model for every set because we
                # might have to exclude extra samples (because of genotype
                # NAs).
                null_model = self.skat.SKAT_Null_Model(
                    self.robjects.Formula("y ~ covar"), out_type=outcome_type
                )

                db_results = {
                    "tested_entity": "snp-set",
                    "results_type": "GenericResults",
                    "entity_name": set_name,
                    "phenotype": phenotype.name,
                    "coefficient": None,
                    "task_name": task_name,
                }

                if not self.skat_o:
                    results = self.r.SKAT(
                        x[not_missing, :], null_model, is_dosage=is_dosage
                    )
                    db_results["test_statistic"] = results.rx("Q")[0][0]
                else:
                    results = self.r.SKAT(
                        x[not_missing, :], null_model, is_dosage=is_dosage,
                        method="optimal.adj"
                    )

                db_results["significance"] = results.rx("p.value")[0][0]

                experiment.add_result(**db_results)


    @staticmethod
    def check_skat():
        """Check if SKAT is installed."""
        if not check_rpy2:
            raise ImportError("rpy2 is required to run SKAT analyses.")

        from rpy2.robjects.packages import importr
        try:
            importr("SKAT")
        except Exception:
            raise EnvironmentError(1, "Couldn't find SKAT in R environment.")

        return True


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
        if self.covariates:
            covar_matrix = np.vstack(tuple([
                experiment.phenotypes.get_phenotype_vector(covar)
                for covar in self.covariates
            ]))

            # Add the intercept because statsmodels does not add it
            # automatically.
            covar_matrix = np.vstack(
                (np.ones(covar_matrix.shape[1]), covar_matrix)
            )
            covar_matrix = covar_matrix.T
            missing_covar = np.isnan(covar_matrix).any(axis=1)

        else:
            # If there are no covariates, we only add the intercept term.
            n = len(experiment.phenotypes.get_sample_order())
            covar_matrix = np.ones(n)
            missing_covar = ~covar_matrix.astype(bool)
            covar_matrix.shape = (n, 1)

        for phenotype in self.outcomes:
            y = experiment.phenotypes.get_phenotype_vector(phenotype)
            missing_outcome = np.isnan(y)

            # For GLMs where we want to compare the variance explained by a
            # null model of the covariates without the genetics effect to the
            # genetic model, we can hookup this function.
            # Note: This is used by the linear test.
            if hasattr(self, "_compute_null_model"):
                self._compute_null_model(phenotype.name, y, covar_matrix)

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

    +--------------------+------------------------------------------+---------+
    | Column             | Description                              | Type    |
    +====================+==========================================+=========+
    | pk                 | The primary key, the same as the         | Integer |
    |                    | :py:class:`experiment.ExperimentResult`  |         |
    +--------------------+------------------------------------------+---------+
    | adjusted_r_squared | The adjusted R squared as reported by    | Float   |
    |                    | statsmodels                              |         |
    +--------------------+------------------------------------------+---------+
    | std_beta           | The standardized effect size. This is    | Float   |
    |                    | for :math:`x, y \sim \mathcal{N}(0,1)`   |         |
    +--------------------+------------------------------------------+---------+
    | std_beta_min       | Lower bound of the 95% CI for the        | Float   |
    |                    | standardized Beta                        |         |
    +--------------------+------------------------------------------+---------+
    | std_beta_max       | Higher bound of the 95% CI               | Float   |
    +--------------------+------------------------------------------+---------+

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

        self.null_rsquared = {}

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

    def _compute_null_model(self, phenotype, y, covar_matrix):
        """Compute the regression for the null model of y ~ covariates."""
        missing = np.isnan(y) | np.isnan(covar_matrix).any(axis=1)
        ols = sm.OLS(y[~missing], covar_matrix[~missing, :])
        fit = ols.fit()
        self.null_rsquared[phenotype] = fit.rsquared_adj

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

    def done(self, *args):
        self.set_meta("null_model_rsquared", self.null_rsquared)
        super(LinearTest, self).done(*args)
