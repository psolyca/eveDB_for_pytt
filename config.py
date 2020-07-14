import os
import sys
import yaml

pyttPath = None
eveDBPath = None

def getpyttRoot():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    base = __file__
    return os.path.dirname(os.path.realpath(os.path.abspath(base)))

def getEveDBPath():
    return eveDBPath

def getDBPathes():
    return {
        "EveDB": eveDBPath
    }

def defPaths():
    global pyttPath
    global eveDBPath

    print("Configuring pytt")

    # The main pytt directory which contains run.py
    # Python 2.X uses ANSI by default, so we need to convert the character encoding
    if pyttPath is None:
        pyttPath = getpyttRoot()

    # The database where the static EVE data from the datadump is kept.
    # This is not the standard sqlite datadump but a modified version created by
    # yamlloader maintenance script
    if eveDBPath is None:
        eveDBPath = os.path.join(pyttPath, "resources", "eve.db")
        try:
            os.mkdir(os.path.join(pyttPath, "resources"))
        except FileExistsError:
            pass
