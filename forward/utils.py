# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module is for short utility functions.

"""


class AbstractClassException(Exception):
    def __str__(self):
        return "Can't initialize an abstract class."


def format_time_delta(delta):
    """Format a timedelta object into a human readable representation."""

    s = delta.seconds
    hours = s // 3600
    s -= hours * 3600
    minutes = s // 60
    s -= minutes * 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, s)


def abstract(cls):
    """Decorator to be used to mark abstract classes.

    This is used because sometimes it is useful to have a parent class that
    is initializable (that does not raise NotImplementedError) but that you
    don't want to actually be used (even though it would not procude
    immediate exceptions. For this reason, you can decorate such classes with
    the @abstract decorator.

    This will make it possible for subclasses to call any parent function
    (_e.g._ the __init__ function) while making sure that the parent never
    get initialized.

    """
    init = cls.__init__

    def safe_init(self, *args, **kwargs):
        if self.__class__ is cls:
            raise AbstractClassException()
        return init(self, *args, **kwargs)

    cls.__init__ = safe_init
    return cls


def dispatch_methods(self, kwargs):
    """Call methods with the parameters as specified in kwargs.

    This assumes that self is an instance of an unknown object and that kwargs
    is an arbitrary dictionary.

    """
    called_methods = []
    for key, value in kwargs.items():
        if hasattr(self, key):
            getattr(self, key)(value)
            called_methods.append(key)

    for method in called_methods:
        del kwargs[method]

    if kwargs:
        message = "Unrecognized argument or method call: '{}'.".format(
            kwargs
        )
        raise ValueError(message)
