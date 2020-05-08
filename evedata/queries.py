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

from service.queryDB import EveDB

eveDB = EveDB.getInstance()

def getMapIdFromName(itemName, whichID="itemID" ):
    return eveDB.selectone(
            "mapDenormalize",
            where={"itemName": itemName}
            )[whichID]

def getMapIdsFromSystemId(solarSystemID):
    return eveDB.selectall(
            "mapDenormalize",
            ("itemId",),
            {"solarSystemID": solarSystemID, "GroupID": 15}
            )

def getMapIdsFromConstellationId(constellationID):
    return eveDB.selectall(
            "mapDenormalize",
            ("itemId",),
            {"constellationID": constellationID, "GroupID": 15}
            )

def getSystemIdFromName(itemName):
    return getMapIdFromName(itemName, "solarSystemID")

def getConstellationIdFromName(itemName):
    return getMapIdFromName(itemName, "constellationID")

def getStationsFromSystemId(solarSystemID):
    return [x[0] for x in getMapIdsFromSystemId(solarSystemID)]

def getStationsFromConstellationId(constellationID):
    return [x[0] for x in getMapIdsFromConstellationId(constellationID)]

def getRegionsAround(regionID):
    regionsAround = eveDB.select(
                        "^mapJumps",
                        ("toRegionID",),
                        {"fromRegionID": regionID, "!toRegionID": regionID}
                    )
    return [x[0] for x in regionsAround]

def getMapNameFromId(itemID):
    return eveDB.selectone(
            "mapDenormalize",
            where={"itemID": itemID}
            )["itemName"]