# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides ways to manage experiments. The experiment objects can
be parsed from the CLI, a yaml configuration file or, eventually, a web
interface.

Overall goals for this module will be to provide:

    - Automated reports.
    - Good organization of experiments aiming at a better reproductibility.
    - Aggregating and writing results files.

"""

class Experiment(object):
    """Class representing an experiment."""
    def __init__(self, phenotype_container, genotype_container, variables,
                 tasks):
        self.phenotypes = phenotype_container
        self.genotypes = genotype_container
        self.variables = variables
        self.tasks = tasks
