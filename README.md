# Introduction

`Forward` is a python package that provides tools and utilities for _foward
genetics_ studies. It is currently under the very early stages of development.

# Architecture

The important concept and modules are as follows:

- genotype: Those are wrappers over sources of genetic data (_e.g._ IMPUTE2
            files or VCFs). They will implement some data cleanup functionality
            like filtering based on the MAF, Hardy Weinberg equilibrium,
            completion rate, region, etc.
            When asked for it, they should create a numpy array of genetic
            variants encoding using the additive (0, 1, 2) model. The order
            should be consistent with the samples defined for the phenotypes.

- phenotype databases: These objects wrap around different source of phenotypic
                       information like CSV files, Excel files or SQL
                       databases. They will contain both covariates and the
                       main outcomes. Eventually, they will allow the reports
                       to include data on trait distribution and disease
                       incidence in the database. The order can be modified
                       and should be consistent with the genotype database.

- variables: Variables are small objects corresponding to entries in the
             phenotype database. They will eventually support different
             transforms. For now, they are useful for specifying the outcomes
             of interest and their data type (discrete vs. continuous).

- tasks: Tasks implement the actual statistical testing or genetic analysis.

- experiment: An experiment wraps all the different components of forward. It
              is used to make sure that everything is clean and will be
              extended to to experiment-based stuff like creating reports and
              aggregating result files. All of the different ways of
              interacting with `foward` (_e.g._ a CLI, a web based interface,
              or the YAML configuration files) should all converge into
              `Experiment` objects.

# Installation

This package will go on pypy following the first official release. In the
meantime, user's interested in the package should clone it and install it
from the source. Because it's still changing very fast and some critical
aspects are not fully implemented and tested, this package should not be used
for real studies (yet).
Note that the first official release is expected to be around the end of
October 2015.
