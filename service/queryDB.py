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
from threading import Thread, Event, Lock
from multiprocessing import Process, Manager
import uuid
import os
import os.path

dbNames = ["EveDB"]
dbClasses = {}
dbInstances = {}
dbCommunicationCanals = {}

def createDBClasses(communicationCanals=None):
    global dbClasses

    def DB_init(self, comCanal):
        self.wInQueue = comCanal[0]
        self.wOutDict = comCanal[1]
        self.rInQueue = comCanal[2]
        self.rOutDict = comCanal[3]

    for name in dbNames:
        dbClasses[name] = type(
            name,
            (QueryDB,),
            {"__init__": DB_init}
        )
    createCommunicationCanals(communicationCanals)

def createCommunicationCanals(communicationCanals):
    global dbCommunicationCanals
    if communicationCanals is None:
        ioManager = Manager()
        for name in dbNames:
            # Communication canals are write input, write output, read input, read output
            comCanal = [ioManager.Queue(), ioManager.dict(), ioManager.Queue(), ioManager.dict()]
            dbCommunicationCanals[name] = comCanal
    else:
        dbCommunicationCanals = communicationCanals
    createDBInstances(dbCommunicationCanals)

def createDBInstances(communicationCanals):
    global dbInstances
    for name in dbNames:
        dbInstances[name] = dbClasses[name](communicationCanals[name])

def startDBThreads(*communicationCanals):
    from config import getDBPathes
    for name in dbNames:
        comCanal = communicationCanals[0][name]
        wInQueue = comCanal[0]
        wOutDict = comCanal[1]
        rInQueue = comCanal[2]
        rOutDict = comCanal[3]
        t = DBWorkerThread(getDBPathes()[name], wInQueue, wOutDict, "{}WriteThread".format(name))
        t.run()
        t = DBWorkerThread(getDBPathes()[name], rInQueue, rOutDict, "{}ReadThread".format(name))
        t.run()

def startDBProcess():
    createDBClasses()
    p = Process(target=startDBThreads, args=(dbCommunicationCanals,), name="DBProcess")
    p.start()


class DBWorkerThread():
    '''SQLite thread safe object.

    Inspired by https://github.com/dashawn888/sqlite3worker/blob/master/sqlite3worker.py
    and  https://stackoverflow.com/questions/10415028/how-can-i-recover-the-return-value-of-a-function-passed-to-multiprocessing-proce
    '''
    def __init__(self, DBPath, inQueue, outDict, name="MyThread"):
        self._DBPath = DBPath
        self._inQueue = inQueue
        self._outDict = outDict
        self._stopEvent = Event()
        self._thread = None
        self._name = name

    @staticmethod
    def _wrapper(DBPath, inQueue, outDict, stopEvent):
        connection = None
        cursor = None

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        def _open(path):
            nonlocal connection
            nonlocal cursor

            connection = sqlite3.connect(
                path,
                isolation_level=None,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            connection.row_factory = dict_factory
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA page_size = 4096")
            cursor = connection.cursor()
        
        _open(DBPath)

        def _runQuery(token, query, values, operation):
            if values:
                if operation == "many":
                    cursor.executemany(query, values)
                else:
                    cursor.execute(query, values)
            else:
                cursor.execute(query)
            if operation == "lastrowid":
                outDict[token] = cursor.lastrowid
            if operation == "fetchone":
                outDict[token] = cursor.fetchone()
            if operation == "fetchall":
                outDict[token] = cursor.fetchall()
            if operation == "rowcount":
                outDict[token] = cursor.rowcount
            if operation is None:
                outDict[token] = True

        for token, query, values, operation in iter(inQueue.get, None):
            if query:
                if connection is not None:
                    _runQuery(token, query, values, operation)
                    if inQueue.empty():
                        connection.commit()
            else:
                if operation == "remove":
                    os.remove(DBPath)
                if operation == "commit" and connection is not None:
                    connection.commit()
                if operation == "open":
                    _open(DBPath)
                if operation == "close" and connection is not None:
                    connection.close()
                    connection = None
                outDict[token] = True

    def run(self):
        self._thread = Thread(
            target=self._wrapper,
            args=(
                self._DBPath,
                self._inQueue,
                self._outDict,
                self._stopEvent
            ),
            name=self._name
        )
        self._thread.start()


class QueryDB():
    '''A class helper.

    Args:
        gameDB (str): A string representing the path of the DB to use."
    '''

    wInQueue = None
    wOutDict = {}
    rInQueue = None
    rOutDict = {}

    def __init__(self):
        pass

    def execute(self, query, values=None, operation=None):
        '''Execute a query

        Args:
            query (str): The SQL statement
            values (iterable - optionnal): An iterable of parameters
            operation (str): Representation of the returned value
        
        Notes:
            See [sqlite3.Cursor.execute](https://docs.python.org/3.7/library/sqlite3.html#sqlite3.Cursor.execute)
        '''
        cmd = query.split(" ", 1)[0]
        if cmd in ("open", "commit", "close"):
            self._execute(self.wInQueue, self.wOutDict, "", values, cmd)
            self._execute(self.rInQueue, self.rOutDict, "", values, cmd)
        elif cmd == "remove":
            self._execute(self.wInQueue, self.wOutDict, "", values, cmd)
        else:
            if cmd in ("CREATE", "INSERT", "UPDATE", "DELETE", "DROP", "VACUUM"):
                result = self._execute(self.wInQueue, self.wOutDict, query, values, operation)
            else:
                result = self._execute(self.rInQueue, self.rOutDict, query, values, operation)
            return result
    
    @staticmethod
    def _execute(inQueue, outDict, query, values, operation):
        token = str(uuid.uuid4())
        inQueue.put((token, query, values, operation), timeout=5)
        try:
            while True:
                if token in outDict:
                    return outDict[token]
        finally:
            del outDict[token]
        
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
    
    def insert(self, table, columns=None, values=None, operation="lastrowid"):
        '''Insert values in a table (simple insert)

        Args:
            table (str): The name of the table
            columns (iterable): An iterable of columns where values will be inserted
                or a dict {column: value} no values needed
            values (iterable - optionnal): An iterable of values (same number as columns)
                if columns is not a dict
            operation (str): Representation of the returned value

        Notes:
            If one column is provided, do not forget a comma at the end
            ("column",) otherwise it will be taken as a string.

        '''
        query = "INSERT INTO {} ({}) ".format(
            table,
            ", ".join(columns),
        )
        if type(columns) is dict:
            query += "VALUES ({})".format(", ".join([":" + x for x in columns]))
            return self.execute(query, columns, operation)
        else:
            query += "VALUES ({})".format(", ".join(("?",) * len(values)))
            return self.execute(query, values, operation)
    
    def insertmany(self, table, columns, values):
        '''Insert values in a table (insert iterable)

        Args:
            table (str): The name of the table
            columns (iterable): An iterable of columns where values will be inserted
            values (iterable): An iterable of iterables of values

        Notes:
            The iterable of values could be provided as list/tuple or dict.
            See [sqlite3.Cursor.executemany](https://docs.python.org/3.7/library/sqlite3.html#sqlite3.Cursor.executemany)

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
        self.execute(query , values, "many")

    def select(self, table, columns = "*", where=None, operation="fetchall"):
        '''Select values in a table

        Args:
            table (str): The name of the table
                if the name begin with ^ choose SELECT DISTINCT
            columns (iterable): An iterable of columns where values will be selected
            where (str or dict - optionnal): Str for complete search condition in
                the format of "column == 'value'"
                or dict {column: value} for multiple AND condition
                if the column begin with ! the condition change from == to !=
            operation (str): Representation of the returned value

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
        return self.execute(query, operation=operation)
    
    def selectone(self, table, columns="*", where=None):
        return self.select(table, columns, where, "fetchone")

    def selectall(self, table, columns="*", where=None):
        return self.select(table, columns, where, "fetchall")

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
        
        TODO: Remove, autocommit is done in the thread
        '''
        self.execute("commit")

    def close(self):
        '''Close the connection to the DB

        Notes:
            Commit automatically before closing.
        '''
        self.commit()
        self.execute("close")

    def update(self, tables, columns="*", where=None, operation=None):
        '''Update values in a table

        Args:
            table (str): The name of the table
            columns (iterable): An iterable of columns where values will be selected
            where (str or dict - optionnal): Str for complete search condition in
                the format of "column == 'value'"
                or dict {column: value} for multiple AND condition
            operation (str): Representation of the returned value

        Notes:
            If one column is provided, do not forget a comma at the end
            ("column",) otherwise it will be taken as a string.
        
        TODO: Like select if the column begin with ! the condition change from == to !=
        '''
        query = "UPDATE {} ".format(tables)
        query += "SET {} ".format(", ".join(["{} = '{}'".format(x, y) for x, y in columns.items()]))
        query += "WHERE {}".format(" AND ".join(["{} = '{}'".format(x, y) for x, y in where.items()]))
        return self.execute(query, operation=operation)
    
    def updatecount(self, tables, columns="*", where=None):
        '''Update values in a table and return rowcount
        '''
        return self.update(tables, columns, where, "rowcount")

    def vacuum(self):
        self.execute("VACUUM")

    def open(self):
        self.execute("open")

    def remove(self):
        self.close()
        self.execute("remove")
        self.open()


