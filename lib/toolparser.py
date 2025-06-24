import os
import sys
import json

parentdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

from lib.UtilLog import UtilLog

logger = UtilLog.getLogger("Tool")

def parseConfigFile():
    providerDict = {}
    statusDict = {}
    try:
        localConfig = os.path.join(parentdir,  "info.json")
        
        if(os.path.exists(localConfig)):
            print(localConfig)

            strConf = ""
            with open(localConfig) as f:
                for line in f:
                    strConf = strConf + line
            data = json.loads(strConf)

            if "Protection Status" in data:
                statusDict = data["Protection Status"]
                print("Protection Status: ", statusDict)
            if "Module Version" in data:
                versionsDict = data["Module Version"]
                print("Protection Status: ", statusDict)
            if "Security Provider" in data:
                providerDict = data["Security Provider"]
                print("Security Provider: ", providerDict)

    except Exception as err:
        logger.exception(str(err))

    return (statusDict, versionsDict, providerDict)

# Run it
if __name__ == "__main__":
    print(parseConfigFile())