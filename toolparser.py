import os
import sys
import json


from lib.UtilLog import UtilLog

logger = UtilLog.getLogger("Tool")

def parseConfigFile():
    try:
        localConfig = os.path.join(os.getcwd(),  "info.json")
        
        if(os.path.exists(localConfig)):
            providerList = {}
            statusList = {}


            strConf = ""
            with open(localConfig) as f:
                for line in f:
                    strConf = strConf + line.lower()
            logger.info(strConf)
            data = json.loads(strConf)

            if "Status" in data:
                statusList = data["Status"]
            if "Providers" in data:
                providerList = data["Providers"]

        else:
            return False
        return (statusList, providerList)

    except Exception as err:
        logger.exception(str(err))
        return False
