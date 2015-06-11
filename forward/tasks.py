# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides actual implementations of the genetic tests.
"""

import multiprocessing
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
import numpy as np


try:
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


from .phenotype.variables import DiscreteVariable


__all__ = ["GLMTest", ]


try:
    _range = range
    range = xrange
except NameError:  # Python3
    pass


class Task(object):
    """Class representing a task (genetic test)."""
    def __init__(self, outcomes, covariates, variants):
        self.outcomes = outcomes
        self.covariates = covariates
        self.variants = variants

    def run_task(self, experiment, task_name):
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


class GLMTest(Task):
    """Generalized linear model genetic test."""
    def __init__(self, outcomes="all", covariates="all", variants="all"):
        if not STATSMODELS_AVAILABLE:
            raise ImportError("GLMTest class requires statsmodels. Install "
                              "the package first.")

        super(GLMTest, self).__init__(outcomes, covariates, variants)

    def run_task(self, experiment, task_name):
        """Run the GLM."""
        super(GLMTest, self).run_task(experiment, task_name)

        # Get a database session from the experiment.
        session = experiment.session

        logger.info("Running a GLM analysis.")

        # Get the list of variants to analyze.
        # No extra filtering for now (TODO).
        variants = experiment.genotypes.query_variants(session, "name").all()
        variants = [i[0] for i in variants]  # Keep only the names.

        # Setup the processes.
        lock = multiprocessing.Lock()
        job_queue = multiprocessing.Queue()
        results_queue = multiprocessing.Queue()
        pool = []
        for cpu in range(experiment.cpu):
            p = multiprocessing.Process(
                target=GLMTest._glm_process,
                args=(lock, job_queue, results_queue)
            )
            p.start()
            pool.append(p)

        num_tests = 0
        for variant in variants:
            # Get the genotype vector.
            x = experiment.genotypes.get_genotypes(variant)

            # Get the covariates and build the design matrix.
            # TODO.

            # Get the phenotypes and fill the job queue.
            for phenotype in self.outcomes:
                if not isinstance(phenotype, DiscreteVariable):
                    continue  # Only handle DiscreteVariables

                y = experiment.phenotypes.get_phenotype_vector(phenotype)
                missing = np.isnan(x) | np.isnan(y)

                job_queue.put((variant, phenotype, x[~missing], y[~missing]))
                num_tests += 1

        job_queue.put(None)
        job_queue.close()

        # We can start parsing the results.
        while num_tests > 0:
            results = results_queue.get()

            # Process the result.
            experiment.add_result("variant", task_name, *results)
            num_tests -= 1


    @staticmethod
    def _glm_process(lock, job_queue, results_queue):
        while True:
            with lock:
                data = job_queue.get()

                if data is None:
                    job_queue.put(data)  # Put the sentinel back.
                    break

            results = GLMTest._glm(*data)

            with lock:
                results_queue.put(results)

        return

    @staticmethod
    def _glm(variant, phenotype, x, y, outcome_column=0):
        """Run a GLM using the y ~ x model.
        
        Returns the p-value and odds ratio.

        """
        # TODO, we should report 95% CI.
        try:
            glm = sm.GLM(y, x, family=sm.families.Binomial())
            res = glm.fit()

            p = res.pvalues[outcome_column]
            beta = res.params[outcome_column]
            std_err = res.bse[outcome_column]

            conf_int = res.conf_int()
            if type(conf_int) is not np.ndarray:
                conf_int = conf_int.values
            ic95_min, ic95_max = conf_int[outcome_column, :]

        except Exception:
            logging.exception("")  # Log the exception and insert nulls in db.
            p = beta = std_err = ic95_min = ic95_max = None

        return (variant, phenotype, p, beta, std_err, ic95_min, ic95_max)
