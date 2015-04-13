# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides actual implementations of the genetic tests.
"""


__all__ = ["GLMTest", ]


class Task(object):
    """Class representing a task (genetic test)."""
    def __init__(self, outcomes, covariates, variants):
        self.outcomes = outcomes
        self.covariates = covariates
        self.variants = variants

    def run_test(self):
        raise NotImplementedError()

class GLMTest(Task):
    """Generalized linear model genetic test."""
    def __init__(self, outcomes="all", covariates="all", variants="all"):
        super(GLMTest, self).__init__(outcomes, covariates, variants)

    def run_test(self):
        print "Running a GLM"
