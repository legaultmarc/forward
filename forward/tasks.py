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
        raise NotImplementedError()

class GLMTest(Task):
    """Generalized linear model genetic test."""
    def __init__(self, outcomes="all", covariates="all", variants="all"):
        super(GLMTest, self).__init__(outcomes, covariates, variants)

    def run_task(self, experiment):
        """Run the GLM.

        In forward, we will launch 1 variant, all phenotypes in parallel.
        The opposite approach, 1 phenotype all variants can easily be achieved
        using existing tools and a bit of bash scripting.

        """
        logger.info("Running a GLM analysis.")
        logger.info("Phens: {}".format(self.outcomes))
        if self.outcomes == "all":
            self.outcomes = [i for i in experiment.variables
                             if not i.is_covariate]

        if self.covariates == "all":
            self.covariates = [i for i in experiment.variables
                               if i.is_covariate]

        if self.variants != "all":
            raise NotImplementedError()

        for variant in experiment.genotypes:
            pass
