# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

import logging
import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, class_mapper

SQLAlchemyBase = declarative_base()

# We extend this class to add json serialization.
def _to_json(self):
    columns = [c.key for c in class_mapper(self.__class__).columns]
    return {c: getattr(self, c) for c in columns}
SQLAlchemyBase.to_json = _to_json
del _to_json


SQLAlchemySession = sessionmaker()

FORWARD_INIT_TIME = datetime.datetime.now()

FORWARD_REPORT_ROOT = "/forward"
STATIC_ROOT = "/static"

logging.basicConfig()

try:
    from .version import forward_version as __version__
except ImportError:
    __version__ = None


def test(verbosity=1):
    import unittest
    from .tests import test_suite

    unittest.TextTestRunner(verbosity=verbosity).run(test_suite)
