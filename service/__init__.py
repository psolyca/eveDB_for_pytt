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

from multiprocessing import Process, Queue


class ProcWarpper():

    def __init__(self, func, *args, **kwargs):
        self.processes = None
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @staticmethod
    def _wrapper(init, func, args, kwargs):
        import importlib
        import service.queryDB as SQ
        import evedata
        # Rebuild eveDB in the forked process to use the same queue as the parent
        dbCommunicationCanals = init[0]
        SQ.createDBClasses(dbCommunicationCanals)
        importlib.reload(evedata.queries)
        func(*args, **kwargs)

    def start(self):
        # Get DB input queues and output dictionnaries to send to child process
        from service.queryDB import dbCommunicationCanals
        init = [dbCommunicationCanals]
        args2 = (init, self.func, self.args, self.kwargs)
        self.processes = Process(target=self._wrapper, args=args2, name="ProcWarpper")
        self.processes.start()

    def close(self):
        self.processes.join()