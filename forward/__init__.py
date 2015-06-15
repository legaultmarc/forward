# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

import datetime
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.orm

SQLAlchemyBase = declarative_base()
SQLAlchemySession = sqlalchemy.orm.sessionmaker()

FORWARD_INIT_TIME = datetime.datetime.now()
