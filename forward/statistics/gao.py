# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module implements a modified version of the algorithm described in:

Gao, X. (2011), Multiple testing corrections for imputed SNPs. Genet.
Epidemiol., 34: 154-158. doi: 10.1002/gepi.20563

It uses the number of effective tests to correct for multiple hypothesis
testing. The threshold becomes alpha / (SNP_eff + Phenotype_eff) where 
alpha is a nominal p-value threshold (e.g. 5%), SNP_eff is the effective
number of variant when taking LD into account and Phenotype_eff is the
effective number of tested phenotypes when taking correlation into account.

The effective numbers are derived from principal component analysis. We take
the number of principal components required to retain a certain fraction of
the variance (e.g. 99.5%).

"""

import bisect
import logging
logger = logging.getLogger(__name__)

import numpy as np
import sklearn.decomposition

def effective_number(x, variance_t = 0.995):
    """Given a design matrix, this computes the effective number of variables.
    
    :param x: A genotype matrix with rows representing samples and columns
              representing variables.
    :type x: np.ndarray

    :returns: A tuple of the real number of variables and the effective number
              retaining the specified amount of variability.
    :rtype: tuple

    In the original (Gao) implementation, the analysis is made by block. Here,
    we will do it in a single block, but it is conveivable to implement a
    similar approach if this one becomes too slow on larger datasets.

    """

    logger.info("Design matrix has {} variables for {} samples.".format(
        x.shape[1], x.shape[0], 
    ))

    # Compute the correlation.
    corr_mat = np.corrcoef(x)

    # Compute the PCA on this matrix.
    pca = sklearn.decomposition.PCA()
    fit = pca.fit(corr_mat)

    variance_sum = np.cumsum(fit.explained_variance_ratio_)
    n_vars = bisect.bisect_right(variance_sum, variance_t) + 1

    logger.info("{} effective variables.".format(n_vars))

    return (x.shape[1], n_vars)
