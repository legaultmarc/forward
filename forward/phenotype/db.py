# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
To optimize performance, forward needs to build a local sqlite3 database
containing all the phenotype information. To do this, delimited text files are
currently parsed into the expected structure. An sqlite3 database is created
and the phenotypes are extracted from this database as needed.

In the configuration file, the "Database" statements are used to control this
behaviour. An example of this is as follows:

    Database:
        separator: "\t"
        missing_values: "-9,-99,-88,-77"
        sample_id: "SampleId"
        db_file: my_analysis.db
        files:
            - cardiovascular_diseases.txt
            - medical_history.txt

The first line of every file is understood as a header. It defines the names
that will be used by the application. As an example, if the file
_medical\_history.txt_ contains a "Cancer" column, _forward_ will associate the
string "Cancer" to this column.

"""

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)

import sqlite3
import os

import pandas as pd

from ..structures import DelimitedFile


__all__ = ["TextFilesDatabase", ]


class Database(object):
    """Abstract class representing a collection of phenotypes."""

    def __init__(self, filename, overwrite=False):
        if os.path.isfile(filename) and not overwrite:
            self.restore_mode = True
        else:
            self.restore_mode = False

        self.db_filename = filename
        self.con = sqlite3.connect(filename)
        self.cur = self.con.cursor()

        if not self.restore_mode:
            self.create_sample_table()

    def create_sample_table(self):
        """Create the table containing all the sample information."""
        self.cur.execute(
            "CREATE TABLE Sample ("
            "   sample TEXT PRIMARY KEY,"
            "   order_key INTEGER"
            ");"
        )

    def create_key_table(self):
        """Create the table for an optional key.
        
        Databases often have different keys that map two sets of sample
        identifiers.

        """
        self.cur.execute(
            "CREATE TABLE Key ("
            "   key1 TEXT,"
            "   key2 TEXT,"
            "   CONSTRAINT pk_key PRIMARY KEY (key1, key2)"
            ");"
        )

    def _query(self, query):
        """Execute an arbitrary SQL query on the database."""
        self.cur.execute(query)

    def get_variable(self):
        """Get an array of phenotypes for all the samples in database."""
        raise NotImplementedError()

    def set_sample_order(self, ordered_ids):
        """Define the order in which phenotype vectors are to be returned.
        
        This is useful because they need to be in the same order as the rows
        in the genotype file.
        """
        i = 0
        for sample in ordered_ids:
            self._query("UPDATE Sample SET order_key=? WHERE sample=?;",
                        (i, sample))
        self.commit()

    def get_sample_order(self):
        """Returns a list of samples in the currently recorded order."""
        self._query("SELECT sample FROM Sample "
                    "WHERE order_key IS NOT NULL "
                    "ORDER BY order_key ASC")
        return self.cur.fetchall()

    @property
    def order_is_set(self):
        self._query("SELECT MAX(order_key) FROM Sample")
        max_idx = self.fetchone()
        if max_idx:
            if max_idx[0] > 1:
                return True
        return False

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()


class TextFilesDatabase(Database):
    """Database constructed from delimited text files."""

    def __init__(self, db_filename, files, missing_values=None, key=None):
        super(TextFilesDatabase, self).__init__(db_filename)

        self.missing_values = missing_values
        if not self.restore_mode:
            if key:
                # Load the key into the database.
                pass

            columns = set()
            file_objects = []
            for file_document in files:
                # Make sure that essential fields are defined.
                fields = ["filename", "separator", "sample_col"]
                for field in fields:
                    if field not in file_document:
                        message = ("Field '{}' is mandatory to represent a "
                                   "delimited text file.".format(field))
                        raise ValueError(message)

                # Create a DelimitedFile object and check the column names.
                obj = DelimitedFile(file_document["filename"],
                                    file_document["separator"])
                obj.sample_col = obj.header.index(file_document["sample_col"])
                file_objects.append(obj)

                columns.update(obj.header)

                self.create_phenotype_table(columns)
