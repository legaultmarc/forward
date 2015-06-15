# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module is for short utility functions.

"""

def format_time_delta(delta):
    """Format a timedelta object into a human readable representation."""

    s = delta.seconds
    hours = s // 3600
    s -= hours * 3600
    minutes = s // 60
    s -= minutes * 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, s)
