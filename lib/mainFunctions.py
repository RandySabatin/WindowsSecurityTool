import subprocess
import json
import os
import time
import psutil
from lib.UtilLog import UtilLog
from lib import toolparser

logger = UtilLog.getLogger("Tool")

class winSecurity():

    def __init__(self, resultQueue):
        try:
            self.result__Queue = resultQueue
            self.resultStatusDict = {}
            self.resultVersionDict = {}
            self.statusDict, self.versionDict, self.providerDict = toolparser.parseConfigFile()  # Load the config file to get initial data

            # Defender scanner-related
            self.mpcmdrun_path = self.find_mpcmdrun_via_msmpeng()
            self.scan_process = None

        except Exception as e:
            logger.error(str(e))
            return

    def find_mpcmdrun_via_msmpeng(self):
        """
        Locates MpCmdRun.exe by finding the path of the running MsMpEng.exe process.
        """
        try:
            for proc in psutil.process_iter(['name', 'exe']):
                if proc.info['name'] and proc.info['name'].lower() == 'msmpeng.exe':
                    msmpeng_path = proc.info['exe']
                    if msmpeng_path and os.path.exists(msmpeng_path):
                        platform_dir = os.path.dirname(msmpeng_path)
                        mpcmdrun_path = os.path.join(platform_dir, "MpCmdRun.exe")
                        if os.path.exists(mpcmdrun_path):
                            return mpcmdrun_path
            raise FileNotFoundError("Could not locate MpCmdRun.exe via MsMpEng.exe process.")
        except Exception as e:
            logger.error(f"Failed to find MpCmdRun.exe: {e}")
            return None

    def start_manual_scan(self, scan_type='QuickScan'):
        """
        Start a Windows Defender scan.
        scan_type: 'QuickScan' or 'FullScan'
        """
        if not self.mpcmdrun_path or not os.path.exists(self.mpcmdrun_path):
            logger.error("MpCmdRun.exe path is invalid.")
            return

        scan_args = {
            'QuickScan': ['-Scan', '-ScanType', '1'],
            'FullScan': ['-Scan', '-ScanType', '2']
        }

        if scan_type not in scan_args:
            logger.error("Invalid scan_type. Must be 'QuickScan' or 'FullScan'.")
            return

        try:
            logger.info(f"Starting {scan_type} using {self.mpcmdrun_path}...")
            self.scan_process = subprocess.Popen(
                [self.mpcmdrun_path] + scan_args[scan_type],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Scan started with PID: {self.scan_process.pid}")
        except Exception as e:
            logger.error(f"Error launching scan: {e}")
            self.scan_process = None

    def stop_scan(self):
        """
        Stop the running scan by terminating the process we started.
        """
        if self.scan_process and self.scan_process.poll() is None:
            try:
                logger.info(f"Terminating scan process (PID: {self.scan_process.pid})...")
                self.scan_process.terminate()
                self.scan_process.wait(timeout=5)
                logger.info("Scan process terminated.")
            except Exception as e:
                logger.error(f"Failed to terminate scan process: {e}")
        else:
            logger.info("No running scan process to terminate.")

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
                    display_key = self.statusDict[key].get('Display', key)
                    self.resultStatusDict[display_key] = flat_data[key.lower()]

            self.SendToSettingDisplay(self.resultStatusDict)

            for key in self.versionDict:
                if key.lower() in flat_data:
                    display_key = self.versionDict[key].get('Display', key)
                    self.resultVersionDict[display_key] = flat_data[key.lower()]

            self.SendToVersionDisplay(self.resultVersionDict)

        except Exception as e:
            logger.error(f"Error: {e}")

    def SendToProtectionDisplay(self, message):
        try:
            self.result__Queue.put({
                "function": "SendToProtectiondisplay",
                "message": message
            })
        except Exception as e:
            logger.error(str(e))

    def SendToSettingDisplay(self, message):
        try:
            self.result__Queue.put({
                "function": "SendToSettingDisplay",
                "message": message
            })
        except Exception as e:
            logger.error(str(e))

    def SendToVersionDisplay(self, message):
        try:
            self.result__Queue.put({
                "function": "SendToVersionDisplay",
                "message": message
            })
        except Exception as e:
            logger.error(str(e))


# Example usage (for testing/debug)
if __name__ == "__main__":
    from queue import Queue
    q = Queue()
    security = winSecurity(resultQueue=q)
    security.get_defender_status()
    security.start_manual_scan('QuickScan')
    time.sleep(10)
    security.stop_scan()