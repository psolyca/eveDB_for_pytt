#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# ==============================================================================
# Copyright (C) 2020 Damien Psolyca Gaignon
#
# This file is part of pytt.
#
# pytt is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pytt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pytt.  If not, see <http://www.gnu.org/licenses/>.
# ==============================================================================

import sqlite3


class QueryDB():
    '''A class helper.

    Args:
        gameDB (str): A string representing the path of the DB to use."
    '''

    DBPath = None

    def __init__(self):
        self.connection = sqlite3.connect(self.DBPath)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def execute(self, query, values = None):
        '''Execute a query

        Args:
            query (str): The SQL statement
            values (iterable - optionnal): An iterable of parameters
        
        Notes:
            See [sqlite3.Cursor.execute](https://docs.python.org/3.7/library/sqlite3.html#sqlite3.Cursor.execute)
        '''
        if values:
            return self.cursor.execute(query, values)
        return self.cursor.execute(query)
    
    def executemany(self, query, values):
        '''Execute a query

        Args:
            query (str): The SQL statement
            values (iterable): An iterable of iterables of parameters
        
        Notes:
            See [sqlite3.Cursor.executemany](https://docs.python.org/3.7/library/sqlite3.html#sqlite3.Cursor.executemany)
        '''
        self.cursor.executemany(query, values)
        
    def create(self, query):
        '''Create tables in the DB

        Args:
            query (str or iterable): The SQL statement
        '''
        if type(query) is list:
            for row in query:
                self.execute(row)
        else:
            self.execute(query)
    
    def insert(self, table, columns, values):
        '''Insert values in a table (simple insert)

        Args:
            table (str): The name of the table
            columns (iterable): An iterable of columns where values will be inserted
            values (iterable): An iterable of values (same number as columns)

        Notes:
            If one column is provided, do not forget a comma at the end
            ("column",) otherwise it will be taken as a string.

        '''
        query = "INSERT INTO {} ({}) ".format(
            table,
            ", ".join(columns),
        )
        if type(values) is dict:
            keys = values.keys()
            query += "VALUES ({})".format(", ".join([":" + x for x in keys]))
        else:
            query += "VALUES ({})".format(", ".join(("?",) * len(values)))
        self.execute(query, values)
    
    def insertmany(self, table, columns, values):
        '''Insert values in a table (insert iterable)

        Args:
            table (str): The name of the table
            columns (iterable): An iterable of columns where values will be inserted
            values (iterable): An iterable of iterables of values

        Notes:
            The iterable of values could be provided as list/tuple or dict.

        '''
        query = "INSERT INTO {} ({}) ".format(
            table,
            ", ".join(columns),
        )
        if type(values[0]) is dict:
            keys = values[0].keys()
            query += "VALUES ({})".format(", ".join([":" + x for x in keys]))
        else:
            query += "VALUES ({})".format(", ".join(("?",) * len(columns)))
        self.executemany(query , values)

    def select(self, table, columns = "*", where = None):
        '''Select values in a table

        Args:
            table (str): The name of the table
                if the name begin with ^ choose SELECT DISTINCT
            columns (iterable): An iterable of columns where values will be selected
            where (str or dict - optionnal): Str for complete search condition in
                the format of "column == 'value'"
                or dict {column: value} for multiple AND condition
                if the column begin with ! the condition change from == to !=

        Notes:
            If one column is provided, do not forget a comma at the end
            ("column",) otherwise it will be taken as a string.
        '''
        query = "SELECT "
        if "^" in table:
            query = "SELECT DISTINCT "
            table = table[1:]
        if where:
            if type(where) is str:
                # Can not use ? in first WHERE statement, so using Python format
                query += "{} FROM {} WHERE {}".format(
                    ", ".join(columns),
                    table,
                    where
                )
            elif type(where) is dict:
                query += "{} FROM {} WHERE ".format(
                    ", ".join(columns),
                    table
                )
                for column, value in where.items():
                    sign = "=="
                    if "!" in column:
                        sign = "!="
                        column = column[1:]
                    query += "{} {} '{}' AND ".format(column, sign, value)
                query = query[:-5]
        else:
            query += "{} FROM {}".format(
                ", ".join(columns),
                table)
        return self.execute(query)
    
    def selectone(self, table, columns = "*", where = None):
        return self.select(table, columns, where).fetchone()

    def selectall(self, table, columns = "*", where = None):
        return self.select(table, columns, where).fetchall()

    def drop(self, table):
        '''Drop a table

        Args:
            table (str): Name of the table to drop
        '''
        query = "DROP TABLE {}".format(table)
        self.execute(query)

    def commit(self):
        '''Commit all transfered data

        Notes:
            Must be donebefore closing otherwise data will be lost.
        '''
        self.connection.commit()

    def close(self):
        '''Close the connection to the DB

        Notes:
            Do not forget to commit before closing.
        '''
        self.connection.close()

class EveDB(QueryDB):

    __instance = None

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = EveDB()
        return cls.__instance
    
    @classmethod
    def reset(cls):
        cls.__instance = None

    def __init__(self):
        from config import getGameDB
        self.DBPath = getGameDB()
        super().__init__()
    
    def close(self):
        super().close()
        # When closing reset instance to avoid Error
        self.reset()
