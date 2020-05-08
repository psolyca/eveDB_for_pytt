#!/usr/bin/env python
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

eveTables = [
        '''CREATE TABLE IF NOT EXISTS "metadata" (
                "field_name"	VARCHAR NOT NULL,
                "field_value"	VARCHAR,
                PRIMARY KEY("field_name")
        )''',
        '''CREATE TABLE IF NOT EXISTS "invTypes" (
                "typeID"	INTEGER NOT NULL,
                "typeName"	VARCHAR(100),
                "description"	TEXT,
                "volume"	FLOAT,
                PRIMARY KEY("typeID")
        )''',
        '''CREATE TABLE IF NOT EXISTS "mapJumps" (
                "fromRegionID"	INTEGER,
                "fromConstellationID"	INTEGER,
                "fromSolarSystemID"	INTEGER NOT NULL,
                "toSolarSystemID"	INTEGER NOT NULL,
                "toConstellationID"	INTEGER,
                "toRegionID"	INTEGER,
                PRIMARY KEY("fromSolarSystemID","toSolarSystemID")
        )''',
        '''CREATE TABLE IF NOT EXISTS "mapDenormalize" (
                "itemID"	INTEGER NOT NULL,
                "groupID"	INTEGER,
                "solarSystemID"	INTEGER,
                "constellationID"	INTEGER,
                "regionID"	INTEGER,
                "x"	FLOAT,
                "y"	FLOAT,
                "z"	FLOAT,
                "itemName"	VARCHAR(100),
                "security"	FLOAT,
                "factionID"	INTEGER,
                "corporationID"	INTEGER,
                PRIMARY KEY("itemID")
        )''',
        '''CREATE TABLE IF NOT EXISTS "invNames" (
                "itemID"	INTEGER NOT NULL,
                "itemName"	VARCHAR(200) NOT NULL,
                PRIMARY KEY("itemID")
        )''',
        '''CREATE TABLE IF NOT EXISTS "mapStargates" (
                "entranceID"	INTEGER NOT NULL,
                "exitID"	INTEGER,
                PRIMARY KEY("entranceID")
        )''',
        '''CREATE INDEX IF NOT EXISTS "ix_mapDenormalize_constellationID" ON "mapDenormalize" (
                "constellationID"
        )''',
        '''CREATE INDEX IF NOT EXISTS "ix_mapDenormalize_solarSystemID" ON "mapDenormalize" (
                "solarSystemID"
        )''',
        '''CREATE INDEX IF NOT EXISTS "mapDenormalize_IX_groupConstellation" ON "mapDenormalize" (
                "groupID",
                "constellationID"
        )''',
        '''CREATE INDEX IF NOT EXISTS "mapDenormalize_IX_groupRegion" ON "mapDenormalize" (
                "groupID",
                "regionID"
        )''',
        '''CREATE INDEX IF NOT EXISTS "mapDenormalize_IX_groupSystem" ON "mapDenormalize" (
                "groupID",
                "solarSystemID"
        )''',
        '''CREATE INDEX IF NOT EXISTS "ix_mapDenormalize_regionID" ON "mapDenormalize" (
                "regionID"
        )'''
]