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
import io

from dateutil.parser import parse

from config import getEveDBPath, getpyttRoot
from service.queryDB import dbInstances
from evedata.tables import eveTables

SDE_LINK = "https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip"
language = "en"
sdeVersion = None
eveDBPath = None


def create_db():
    global eveDBPath

    from zipfile import ZipFile

    import yaml
    try:
        from yaml import CLoader as Loader
        print('Using CLoader')
    except ImportError:
        from yaml import Loader
        print('Using Python Loader')

    eveDBPath = getEveDBPath()
    resourcesZip = None
    eveDB = dbInstances["EveDB"]

    def _readYaml(file):
        yamlfile = resourcesZip.read(file)
        test = yaml.load(yamlfile, Loader = Loader)
        return test

    def _getFileList(path, zone):
        return [x for x in resourcesZip.namelist() if path in x and zone in x]

    def getResourcesFile():
        nonlocal resourcesZip
        global sdeVersion
        sdeFile = os.path.join(getpyttRoot(), "sde.zip")
        if os.path.isfile(sdeFile):
            resourcesZip = ZipFile(sdeFile)
            resourcesHeader = requests.head(SDE_LINK)
            sdeVersion = int(parse(resourcesHeader.headers["Last-Modified"]).timestamp())
            print("sdeVersion : {}".format(sdeVersion))
            return True
        else:
            print("Downloading resources file from EVE")
            resourcesFile = requests.get(SDE_LINK)
            if resourcesFile.ok:
                resourcesZip = ZipFile(io.BytesIO(resourcesFile.content))
                sdeVersion = int(parse(resourcesFile.headers["Last-Modified"]).timestamp())
                print("sdeVersion : {}".format(sdeVersion))
                return True
            else:
                print("Not able to download resources file from EVE")
                return False

    def populate():

        print("Populating invNames")
        # TODO : Add consistencies with ESI data
        # Check if all names are in the SDE (should not be !)
        # Get only 
        # 10,000,000	11,000,000	New Eden regions
        # 20,000,000	21,000,000	New Eden constellations
        # 30,000,000	31,000,000	New Eden solar systems
        # 50,000,000	60,000,000	Stargates
        # 60,000,000	61,000,000	Stations created by CCP
        # eveDB.insertmany("invNames",
        #     ("itemID", "itemName"),
        #     (_readYaml('sde/bsd/invNames.yaml'))
        # )
        for item in _readYaml('sde/bsd/invNames.yaml'):
            print(item)

        print("Populating invTypes")
        # TODO : Add consistencies with ESI type
        # Check if all types are in the SDE (should not be !)
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
        print("sdeVersion : {}".format(sdeVersion))
        eveDB.insert("metadata",
            ("field_name", "field_value"),
            ("dump_time", sdeVersion)
        )

        popMapJumps()

        eveDB.commit()

    def popRegion(regionFile):
        head, _ = os.path.split(regionFile)
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
        head, _ = os.path.split(constellationFile)
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

        for _, planetData in system['planets'].items():
            if 'npcStations' in planetData:
                popStation(planetData['npcStations'], system, constellation, region)
            if 'moons' in planetData:
                for _, moonData in planetData['moons'].items():
                    if 'npcStations' in moonData:
                        popStation(moonData['npcStations'], system, constellation, region)

    def popStargates(stargates, system, constellation, region):
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

    if os.path.isfile(eveDBPath):
        eveDB.close()
        os.remove(eveDBPath)
    if getResourcesFile():
        print("Creating game DB")
        eveDB.open()
        eveDB.create(eveTables)

        populate()

        print("Cleaning game DB")
        eveDB.drop("invNames")
        eveDB.drop("mapStargates")

        eveDB.vacuum()
        resourcesZip.close()


if __name__ == '__main__':
    create_db()
