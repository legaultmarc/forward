# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides some simple utility functions for diverse statistical
tasks.
"""

from __future__ import division

import scipy.stats

def inverse_normal_transformation(x, c=3/8):
    """Transform a data vector x using the inverse normal transformation.

    """
    r = scipy.stats.rankdata(x, "average")
    return scipy.stats.norm.ppf((r - c) / (len(x) - 2 * c + 1))
