# This file is part of forward.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
This module provides diverse utility classes.
"""


class DelimitedFile(object):
    """Representation of a delimited text file.

    :param filename: The filename.
    :type filename: str

    :param separator: The delimiter for the columns.
    :type separator: str

    :param header: If this is True (it is by default), then the first line
                   will be interpreted as a header and dicts will be returned
                   upon iteration. If it is not, lists will be returned.
    :type header: bool

    By default, this assumes that the first line is a header. You can pass the
    `header=False` argument to avoid this.

    """
    def __init__(self, filename, separator, header=True):
        self.filename = filename
        self.separator = separator

        self._f = open(filename, "r")

        if header:
            self.header = self._f.readline().rstrip().split(self.separator)
        else:
            self.header = None

    def __next__(self, sql_safe=True):
        line = next(self._f).rstrip()
        if sql_safe:
            line = line.replace("\"", "")
        line = line.split(self.separator)
        line = [i if i != "" else None for i in line]  # Replace missings.

        if not self.header:
            return line
        else:
            return dict(zip(self.header, line))

    next = __next__

    def readline(self, sql_safe=True):
        try:
            line = self.__next__(sql_safe)
            return line
        except StopIteration:
            return ""

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self._f.close()
        except Exception:
            pass

    def reset(self):
        self._f.seek(0)
        if self.header:
            self._f.readline()  # Skip the header

    def close(self):
        return self._f.close()

    def infer_dtypes(self):
        """Infer the dtype for every column and return a list."""
        if hasattr(self, "dtypes"):
            return self.dtypes

        inital_position = self._f.tell()

        dtypes = (int, float, str, unicode)

        line = self.readline()
        ncols = len(line)

        # This dictionary will map column index to inferred datatype.
        header = self.header if self.header else range(ncols)
        inferred_dtypes = dict.fromkeys(header)

        while None in inferred_dtypes.values() and line:
            for field in header:
                col = line[field]
                if col is None:
                    continue

                if inferred_dtypes[field] is not None:
                    # Make sure the inferred type is valid.
                    try:
                        inferred_dtypes[field](col)
                    except Exception:
                        inferred_dtypes[field] = None

                for dtype in dtypes:
                    try:
                        dtype(col)
                        inferred_dtypes[field] = dtype
                        break
                    except Exception:
                        pass

            line = self.readline()

        # By default, we will set fields to str.
        for col in inferred_dtypes:
            if inferred_dtypes[col] is None:
                inferred_dtypes[col] = str

        self._f.seek(inital_position)
        self.dtypes = inferred_dtypes

        return inferred_dtypes
