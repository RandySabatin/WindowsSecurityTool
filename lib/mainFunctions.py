
import subprocess
import json
from lib.UtilLog import UtilLog
from lib import toolparser

logger = UtilLog.getLogger("Tool")

class winSecurity():

    def __init__(self, resultQueue):
        try:
            self.result__Queue =  resultQueue
            self.resultStatusDict = {}
            self.resultVersionDict = {}
            self.statusDict, self.versionDict, self.providerDict = toolparser.parseConfigFile()  # Load the config file to get initial data

        except Exception as e:
            logger.error(str(e))
            return
    
    def run_powershell_command(self, command, timeout=10):
        """
        Runs a PowerShell command with timeout. Kills process if it hangs.
        Returns stdout text.
        """
        proc = subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()  #Force kill
            stdout, stderr = proc.communicate()
            raise TimeoutError(f"Command timed out and was forcefully terminated: {command}")
    
        if proc.returncode != 0:
            raise RuntimeError(f"PowerShell error: {stderr.strip()}")
    
        return stdout
    
    def get_defender_status(self, timeout=10):
        try:
            if (not self.statusDict) or (not self.versionDict):
                logger.error("Error: Status dictionary is empty. Please check the configuration file.")

            # Step 1: Force-initialize the Defender context
            self.run_powershell_command("Get-MpPreference | Out-Null", timeout)
    
            # Step 2: Get Defender status as JSON
            json_text = self.run_powershell_command("Get-MpComputerStatus | ConvertTo-Json -Depth 4", timeout)
    
            data = json.loads(json_text)
    
            # Keep only flat (non-nested) properties
            flat_data = {k.lower(): v for k, v in data.items() if not isinstance(v, (dict, list))}

            for key in self.statusDict:
                if key.lower() in flat_data:
                    if 'Display' in self.statusDict[key]:
                        self.resultStatusDict[self.statusDict[key]['Display']] = flat_data[key.lower()]
                    else:
                        self.resultStatusDict[key] = str(flat_data[key.lower()])

            self.SendToSettingDisplay(self.resultStatusDict)

            for key in self.versionDict:
                if key.lower() in flat_data:
                    if 'Display' in self.versionDict[key]:
                        self.resultVersionDict[self.versionDict[key]['Display']] = flat_data[key.lower()]
                    else:
                        self.resultVersionDict[key] = str(flat_data[key.lower()])

            self.SendToVersionDisplay(self.resultVersionDict)
    
        except Exception as e:
            logger.error(f"Error: {e}")

    def SendToProtectionDisplay(self, message):
        try:
            Str2Dict = {}
            Str2Dict["function"] = "SendToProtectiondisplay"
            Str2Dict["message"] = message.strip()

            self.result__Queue.put(Str2Dict)
        except Exception as e:
            logger.error(str(e))
            return

    def SendToSettingDisplay(self, message):
        try:
            Str2Dict = {}
            Str2Dict["function"] = "SendToSettingDisplay"
            Str2Dict["message"] = message

            self.result__Queue.put(Str2Dict)
        except Exception as e:
            logger.error(str(e))
            return

    def SendToVersionDisplay(self, message):
        try:
            Str2Dict = {}
            Str2Dict["function"] = "SendToVersionDisplay"
            Str2Dict["message"] = message

            self.result__Queue.put(Str2Dict)
        except Exception as e:
            logger.error(str(e))
            return
        
# Run it
if __name__ == "__main__":
    print(winSecurity.get_defender_status(timeout=10))

