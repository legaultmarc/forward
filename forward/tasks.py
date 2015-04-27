# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides actual implementations of the genetic tests.
"""

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


__all__ = ["GLMTest", ]


class Task(object):
    """Class representing a task (genetic test)."""
    def __init__(self, outcomes, covariates, variants):
        self.outcomes = outcomes
        self.covariates = covariates
        self.variants = variants

    def run_task(self, experiment):
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
        super(GLMTest, self).__init__(outcomes, covariates, variants)

    def run_task(self, experiment):
        """Run the GLM."""
        super(GLMTest, self).run_task(experiment)

        # Get a database session from the experiment.
        session = experiment.session

        logger.info("Running a GLM analysis.")

        # Get the list of variants to analyze.
        # No extra filtering for now (TODO).
        variants = experiment.genotypes.query_variants(session).all()

        # if experiment.cpu != 1:
        #     self.pool = multiprocessing.Pool(experiment.cpu)
        #     _map = self.pool.map
        # else:
        #     _map = map

        # results = map()
