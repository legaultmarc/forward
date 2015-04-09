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
        self._query(
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
        self._query(
            "CREATE TABLE Key ("
            "   key1 TEXT,"
            "   key2 TEXT,"
            "   CONSTRAINT pk_key PRIMARY KEY (key1, key2)"
            ");"
        )

    def _query(self, query, tu=None):
        """Execute an arbitrary SQL query on the database."""
        if tu:
            self.cur.execute(query, tu)
        else:
            self.cur.execute(query)

    def get_variable(self, phenotype):
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

    def add_sample(self, sample):
        # Check if sample already exists.
        self._query("SELECT * from Sample WHERE sample=?", (sample, ))
        if self.cur.fetchone():
            return

        # Add the sample
        self._query("INSERT INTO Sample (sample) VALUES (?)", (sample, ))

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

            self.fill_sample_table(file_objects)
            self.create_phenotype_table(columns, file_objects)
            self.fill_phenotype_table(file_objects)

            self.commit()

    def fill_sample_table(self, file_objects):
        for file_object in file_objects:
            for line in file_object:
                header_key = file_object.header[file_object.sample_col]
                sample = line[header_key]
                self.add_sample(sample)
            file_object.reset()

    def create_phenotype_table(self, columns, file_objects):
        dtype_map = {
            int: "INTEGER",
            float: "REAL",
            str: "TEXT",
            unicode: "TEXT"
        }

        sql = ("CREATE TABLE Phenotype (\n"
               "    sample TEXT PRIMARY KEY,\n")

        for file_object in file_objects:
            # Get the dtypes.
            dtypes = file_object.infer_dtypes()

            # Get the columns that are in this file.
            fields = columns & set(file_object.header)
            for field in fields:
                # Skip the sample column.
                if field == file_object.header[file_object.sample_col]:
                    continue

                sql += "    `{}` {},\n".format(
                    field, dtype_map[dtypes[field]] 
                )

        sql = sql.rstrip(",\n")
        sql += "\n)"

        self._query(sql)

    def fill_phenotype_table(self, file_objects):
        for file_object in file_objects:
            # Get the dtypes
            dtypes = file_object.infer_dtypes()

            file_object.reset()

            for line in file_object:
                sample_col = file_object.header[file_object.sample_col]
                sample = line[sample_col]

                # Check if phenotypes for this sample are already in db.
                # If it is, we update information instead of creating a new
                # row.
                self._query(
                    "SELECT * FROM Phenotype WHERE sample=?",
                    (sample, )
                )
                if self.cur.fetchone():
                    set_stmt = ""
                    for field, value in line.items():
                        if field != sample_col and value is not None:
                            set_stmt += "`{}`=".format(field)
                            if dtypes[field] in (int, float):
                                try:
                                    dtypes[field](value)
                                    set_stmt += str(value)
                                except ValueError:
                                    dtypes[field] = str
                                    set_stmt += "\"{}\"".format(value)
                            else:
                                set_stmt += "\"{}\"".format(value)
                            set_stmt += ","

                    set_stmt = set_stmt.rstrip(",")

                    sql = ("UPDATE Phenotype \n"
                           "    SET {}\n"
                           "    WHERE sample=?".format(set_stmt))

                    try:
                        self._query(sql, (sample, ))
                    except Exception as e:
                        logger.critical("Failed SQL command: " + sql)
                        raise e

                # Add this sample to the db.
                else:
                    sql = "INSERT INTO Phenotype (`sample`,"

                    for field in line.keys():
                        value = line[field]
                        if field != sample_col and value is not None:
                            sql += "`{}`,".format(field)
                    sql = sql.rstrip(",") + ") VALUES ("

                    sql += "\"{}\",".format(line[sample_col])

                    for field in line.keys():
                        value = line[field]
                        if field != sample_col and value is not None:
                            if dtypes[field] in (int, float):
                                try:
                                    dtypes[field](value)
                                    sql += str(value)
                                except ValueError:
                                    dtypes[field] = str
                                    sql += "\"{}\"".format(line[field])
                            else:
                                sql += "\"{}\"".format(line[field])
                            sql += ","

                    sql = sql.rstrip(",") + ")"

                    try:
                        self._query(sql)
                    except Exception:
                        logger.critical("Failed SQL command: " + sql)
                        raise e

# import forward.configuration; forward.configuration.parse_configuration("sample_experiment/experiment.yaml")
