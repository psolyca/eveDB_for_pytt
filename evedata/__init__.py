#!/usr/bin/env python3
#======================================================================
# Copyright (C) 2020 Damien Psolyca Gaignon
#
# This file is part of pytt.
#
# pytt is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# pytt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with pytt.  If not, see <http://www.gnu.org/licenses/>.
#======================================================================


import os
import os.path
import sys
import requests
from io import BytesIO

from dateutil.parser import parse

from config import getGameDB
from service.queryDB import EveDB
from evedata.tables import eveTables

SDE_LINK = "https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip"
language = "en"
sdeVersion = None
gameDB = None

def check_db():
    global sdeVersion
    global gameDB

    gameDB = getGameDB()

    if not os.path.exists(gameDB):
        create_db()
        return
    print("Checking last version of SDE...")
    r = requests.head(SDE_LINK)
    resourcesStamp = int(parse(r.headers["Last-Modified"]).timestamp())
    eveDB = EveDB.getInstance()
    sdeVersion = eveDB.selectone("metadata", where={"field_name": "dump_time"})
    if not sdeVersion:
        print("Problem in DB... Rebuilding the DB")
        create_db()
        return
    if (resourcesStamp != int(sdeVersion["field_value"])):
        print("Not last version... Rebuilding the DB")
        create_db()
        return
    print("Last version.")


def create_db():
    from zipfile import ZipFile

    import yaml
    try:
        from yaml import CLoader as Loader
        print('Using CLoader')
    except ImportError:
        from yaml import Loader
        print('Using Python Loader')

    resourcesZip = None
    eveDB = EveDB.getInstance()

    def _readYaml(file):
        nonlocal resourcesZip
        return yaml.load(resourcesZip.read(file), Loader = Loader)

    def _getFileList(path, zone):
        nonlocal resourcesZip
        return [x for x in resourcesZip.namelist() if path in x and zone in x]

    def getResourcesFile():
        nonlocal resourcesZip
        global sdeVersion
        print("Downloading resources file from EVE")
        resourcesFile = requests.get(SDE_LINK)
        if resourcesFile.ok:
            resourcesZip = ZipFile(BytesIO(resourcesFile.content))
            sdeVersion = int(parse(resourcesFile.headers["Last-Modified"]).timestamp())
            return True
        else:
            print("Not able to download resources file from EVE")
            return False
        resourcesZip = ZipFile("J:\Téléchargements\eve\sde.zip")
        sdeVersion = int(os.path.getmtime("J:\Téléchargements\eve\sde.zip"))
        return True

    def populate():
        nonlocal eveDB
        global sdeVersion

        print("Populating invNames")
        eveDB.insertmany("invNames",
            ("itemID", "itemName"),
            (_readYaml('sde/bsd/invNames.yaml'))
        )

        print("Populating invTypes")
        for typeID, typeData in _readYaml('sde/fsd/typeIDs.yaml').items():
            if (typeData.get("marketGroupID")):
                description = typeData.get('description', {}).get(language, '')
                description.replace('"', r'\"')
                eveDB.insert("invTypes",
                    ("typeID", "typeName", "description", "volume"),
                    (typeID, typeData.get('name', {}).get(language, ''),
                        description,
                        typeData.get('volume', 0)
                    )
                )
        
        print("Populating mapDenormalize")
        for regionFile in _getFileList('/eve', 'region'):
            popRegion(regionFile)
        
        print("Populating metadata")
        eveDB.insert("metadata",
            ("field_name", "field_value"),
            ("dump_time", sdeVersion)
        )

        popMapJumps()

        eveDB.commit()

    def popRegion(regionFile):
        nonlocal eveDB
        head, tail = os.path.split(regionFile)
        region = _readYaml(regionFile)
        regionName = eveDB.selectone("invNames",
            where={"itemID": region['regionID']}
        )["itemName"]
        print("    Importing Region {}".format(regionName))
        eveDB.insert("mapDenormalize",
            ("itemID", "groupID", "x", "y", "z", "itemName", "factionID"),
            (region['regionID'], 3, region['center'][0], region['center'][1],
                region['center'][2], regionName, region.get('factionID', None)
            )
        )
        for constellationFile in _getFileList(head, 'constellation'):
            popConstellation(constellationFile, region)

    def popConstellation(constellationFile, region):
        nonlocal eveDB
        head, tail = os.path.split(constellationFile)
        constellation = _readYaml(constellationFile)

        constellationName = eveDB.selectone("invNames",
            where={"itemID": constellation["constellationID"]}
        )["itemName"]
        print("        Importing constellation {}".format(constellationName))
        eveDB.insert("mapDenormalize",
            ("itemID", "groupID", "regionID", "x", "y", "z", "itemName", "factionID"),
            (constellation["constellationID"], 4, region['regionID'], 
                constellation['center'][0], constellation['center'][1],
                constellation['center'][2], constellationName,
                constellation.get('factionID', region.get('factionID', None))
            )
        )
        for systemFile in _getFileList(head, 'solarsystem'):
            popSolarSystem(systemFile, constellation, region)

    def popSolarSystem(systemFile, constellation, region):
        nonlocal eveDB
        system = _readYaml(systemFile)
        systemName = eveDB.selectone("invNames",
            where={"itemID": system['solarSystemID']}
        )["itemName"]
        print("            Importing solar system {}".format(systemName))
        eveDB.insert("mapDenormalize",
            ("itemID", "groupID", "constellationID", "regionID", "x", "y", "z",
                "itemName", "factionID"),
            (system['solarSystemID'], 5, constellation["constellationID"], 
                region['regionID'], system['center'][0], system['center'][1],
                system['center'][2], systemName,
                system.get('factionID', constellation.get('factionID', region.get('factionID', None)))
            )
        )
        popStargates(system['stargates'], system, constellation, region)

        for planetID, planetData in system['planets'].items():
            if 'npcStations' in planetData:
                popStation(planetData['npcStations'], system, constellation, region)
            if 'moons' in planetData:
                for moonID, moonData in planetData['moons'].items():
                    if 'npcStations' in moonData:
                        popStation(moonData['npcStations'], system, constellation, region)

    def popStargates(stargates, system, constellation, region):
        nonlocal eveDB
        print("                Populating mapStargates and mapDenormalize")
        for stargateID, stargateInfo in stargates.items():
            eveDB.insert("mapStargates",
                ("entranceID", "exitID"),
                (stargateID, stargateInfo.get('destination'))
            )
            eveDB.insert("mapDenormalize",
                ("itemID", "groupID", "solarSystemID", "constellationID", "regionID"),
                (stargateID, 10, system["solarSystemID"],
                    constellation["constellationID"], region["regionID"]
                )
            )

    def popStation(stationData, system, constellation, region):
        nonlocal eveDB
        for stationID, stationInfo in stationData.items():
            stationName = eveDB.selectone("invNames",
            where={"itemID": stationID}
            )["itemName"]
            print("                Importing station {}".format(stationName))
            eveDB.insert("mapDenormalize",
                ("itemID", "groupID", "solarSystemID", "constellationID", "regionID",
                    "x", "y", "z", "itemName", "security", "factionID", "corporationID"),
                (stationID, 15, system['solarSystemID'], constellation["constellationID"],
                    region['regionID'], stationInfo['position'][0],
                    stationInfo['position'][1], stationInfo['position'][2],
                    stationName, system['security'],
                    system.get('factionID', constellation.get('factionID', region.get('factionID', None))),
                    stationInfo.get('ownerID', None)
                )
            )

    def popMapJumps():
        nonlocal eveDB
        print("Populating mapJumps")
        stargateJumps = eveDB.selectall("mapStargates")
        for jump in stargateJumps:
            stargateEntrance = eveDB.selectone("mapDenormalize",
                where={"itemID":jump["entranceID"]}
            )
            stargateExit = eveDB.selectone("mapDenormalize",
                where={"itemID": jump["exitID"]}
            )
            eveDB.insert("mapJumps",
                ("fromRegionID", "fromConstellationID", "fromSolarSystemID", 
                "toSolarSystemID", "toConstellationID", "toRegionID"),
                (stargateEntrance["regionID"], stargateEntrance["constellationID"],
                    stargateEntrance["solarSystemID"], stargateExit["solarSystemID"],
                    stargateExit["constellationID"], stargateExit["regionID"]
                )
            )

    if os.path.isfile(gameDB):
        eveDB.close()
        os.remove(gameDB)
    if getResourcesFile():    
        print("Creating game DB")
        eveDB = EveDB.getInstance()
        eveDB.execute("PRAGMA page_size = 4096")
        eveDB.create(eveTables)

        populate()

        print("Cleaning game DB")
        eveDB.drop("invNames")
        eveDB.drop("mapStargates")

        eveDB.execute("VACUUM")
        resourcesZip.close()


if __name__ == '__main__':
    create_db()
