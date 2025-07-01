import subprocess
import json
import os
import time
import psutil
from lib.UtilLog import UtilLog
from lib import toolparser
import win32event
import win32api

logger = UtilLog.getLogger("Tool")

def decode_product_state(state):
    print('state: ', state)
    print(hex(state))
    sig_status = state & 0xFF
    print('sig_status: ', sig_status)
    print(hex(sig_status))
    realtime_stat = (state >> 8) & 0xFF
    print('realtime_stat ', realtime_stat)
    print(hex(realtime_stat))
    product_stat = (state >> 16) & 0xFF
    print('product_stat: ', product_stat)
    print(hex(product_stat))

    product_status_lookup = {
        0x00: "Not installed / inactive",
        0x01: "Installed but disabled",
        0x06: "Installed and enabled",
        0x10: "Fully active / registered",
        0x30: "Enabled (some vendors)",
        0x40: "Enabled (some vendors)",
        0x61: "Vendor-specific custom value",
    }

    realtime_status_lookup = {
        0x00: "Real-time protection OFF",
        0x01: "Real-time protection ON (vendor-specific)",
        0x10: "Real-time protection ON",
        0x11: "Real-time protection ON",
    }

    signature_status_lookup = {
        0x00: "Signatures outdated or unknown",
        0x10: "Signatures up-to-date",
        0x11: "Signatures up-to-date",
    }

    return {
        "Raw productState": f"0x{state:06X}",
        "Product Status": product_status_lookup.get(product_stat, f"Unknown (0x{product_stat:02X})"),
        "Real-time Protection": realtime_status_lookup.get(realtime_stat, f"Unknown (0x{realtime_stat:02X})"),
        "Signature Status": signature_status_lookup.get(sig_status, f"Unknown (0x{sig_status:02X})")
    }

class securityStat():
    def __init__(self, resultQueue):
        try:
            self.result__Queue = resultQueue
            self.resultStatusDict = {}
            self.resultVersionDict = {}
            self.statusDict, self.versionDict, self.providerDict = toolparser.parseConfigFile()
        except Exception as e:
            logger.error(str(e))

    def run_powershell_command(self, command, timeout=10):
        proc = subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise TimeoutError(f"Command timed out and was forcefully terminated: {command}")

        if proc.returncode != 0:
            raise RuntimeError(f"PowerShell error: {stderr.strip()}")

        return stdout

    def get_defender_status(self, timeout=10):
        try:
            if (not self.statusDict) or (not self.versionDict):
                logger.error("Error: Status dictionary is empty. Please check the configuration file.")
        
            # Step 1: Initialize Defender context
            self.run_powershell_command("Get-MpPreference | Out-Null", timeout)
        
            # Step 2: Get plain-text output instead of ConvertTo-Json
            output = self.run_powershell_command("Get-MpComputerStatus | Out-String", timeout)
            lines = output.strip().splitlines()
        
            # Step 3: Parse key-value pairs from the plain-text output
            flat_data = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    flat_data[key.strip().lower()] = value.strip()
        
            # Step 4: Map data to result dictionaries
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

    def get_antivirus_info(self):
        try:
            ps_script = (
                "Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | "
                "Select-Object displayName, pathToSignedProductExe, productState | ConvertTo-Json"
            )
            result = self.run_powershell_command(ps_script)
            av_list = json.loads(result)

            if isinstance(av_list, dict):
                av_list = [av_list]

            flattened = []
            for av in av_list:
                state_info = decode_product_state(av.get("productState", 0))
                flattened.append({
                    "Name": av.get("displayName", "Unknown"),
                    "ProductStatus": state_info.get("Product Status", ""),
                    "RealTimeProtection": state_info.get("Real-time Protection", "")
                })

            self.SendToProtectionDisplay({"Antivirus": flattened})

        except Exception as e:
            logger.error(f"Error getting antivirus info: {e}")
            self.SendToProtectionDisplay({"Error": str(e)})

    def get_firewall_status(self):
        try:
            # Get firewall profile info
            fw_command = (
                "Get-NetFirewallProfile | "
                "Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction | ConvertTo-Json"
            )

            # Get network connection profile info
            net_command = (
                "Get-NetConnectionProfile | "
                "Select-Object Name, InterfaceAlias, @{Name='NetworkCategory';Expression={ \"$($_.NetworkCategory)\" }} | ConvertTo-Json"
            )

            fw_result = self.run_powershell_command(fw_command)
            net_result = self.run_powershell_command(net_command)

            fw_profiles = json.loads(fw_result)
            net_profiles = json.loads(net_result)

            if isinstance(fw_profiles, dict):
                fw_profiles = [fw_profiles]
            if isinstance(net_profiles, dict):
                net_profiles = [net_profiles]

            firewall_info = [
                {
                    "Profile": prof["Name"],
                    "Firewall Enabled": "Yes" if prof["Enabled"] else "No",
                    "Inbound Default": prof["DefaultInboundAction"],
                    "Outbound Default": prof["DefaultOutboundAction"]
                }
                for prof in fw_profiles
            ]

            network_info = [
                {
                    "Name": profile.get("Name", "Unknown"),
                    "Interface": profile.get("InterfaceAlias", "Unknown"),
                    "Network Category": profile.get("NetworkCategory", "Unknown")
                }
                for profile in net_profiles
            ]

            combined_info = {
                "FirewallProfiles": firewall_info,
                "NetworkConnections": network_info
            }

            self.SendToProtectionDisplay(combined_info)

        except Exception as e:
            logger.error(f"Error getting firewall/network info: {e}")
            self.SendToProtectionDisplay({"Error": str(e)})

    def SendToProtectionDisplay(self, message):
        try:
            self.result__Queue.put({
                "function": "SendToProtectionDisplay",
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


class securityScan():

    def __init__(self):
        try:

            # Defender scanner-related
            self.mpcmdrun_path = self.find_mpcmdrun_via_msmpeng()
            self.scan_process = None

            event_scan_stop = 'Global\\__scan_stop'

            # Open the named event with permissions to set it
            self.hStopEvent = win32event.OpenEvent(
                win32event.SYNCHRONIZE | win32event.EVENT_MODIFY_STATE,
                False,
                event_scan_stop)
           
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

    def start_manual_scan(self, scan_type='QuickScan', scanPath=None):
        """
        Start a Windows Defender scan.
        scan_type: 'QuickScan' or 'FullScan'
        """

        if not self.mpcmdrun_path or not os.path.exists(self.mpcmdrun_path):
            logger.error("MpCmdRun.exe path is invalid.")
            return

        scan_args = {
            'QuickScan': ['-Scan', '-ScanType', '1'],
            'FullScan': ['-Scan', '-ScanType', '2'],
            'CustomScan': ['-Scan', '-ScanType', '3', '-File', scanPath]
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

            # Open process handle for waiting
            hProcess = win32api.OpenProcess( win32event.SYNCHRONIZE, False, self.scan_process.pid)
            
            print("Waiting for either child process to exit or event to be signaled...")
            result = win32event.WaitForMultipleObjects([hProcess, self.hStopEvent], False, win32event.INFINITE)
            
            if result == win32event.WAIT_OBJECT_0:
                print("Child process exited normally.")
            elif result == win32event.WAIT_OBJECT_0 + 1:
                win32event.ResetEvent(self.hStopEvent)
                print("Event was signaled! Child still running - terminating...")
                self.stop_scan()
            else:
                print("Unexpected wait result:", result)
            
            win32api.CloseHandle(self.hStopEvent)
            win32api.CloseHandle(hProcess)

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

class securityUpdate():

    def __init__(self):
        try:

            # Defender scanner-related
            self.mpcmdrun_path = self.find_mpcmdrun_via_msmpeng()
            self.update_process = None

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

    def start_update(self):
        """
        Start a Windows Defender update.
        #MpCmdRun.exe -SignaturesUpdateService -ScheduleJob -UnmanagedUpdate
        """

        if not self.mpcmdrun_path or not os.path.exists(self.mpcmdrun_path):
            logger.error("MpCmdRun.exe path is invalid.")
            return

        try:
            logger.info(f"Starting update using {self.mpcmdrun_path}...")
            self.update_process = subprocess.Popen(
                [self.mpcmdrun_path, '-SignaturesUpdateService', '-ScheduleJob', '-UnmanagedUpdate'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Update started with PID: {self.update_process.pid}")
            print([self.mpcmdrun_path, '-SignaturesUpdateService', '-ScheduleJob', '-UnmanagedUpdate'])

            # Open process handle for waiting
            hProcess = win32api.OpenProcess( win32event.SYNCHRONIZE, False, self.update_process.pid)
            
            print("Waiting for either child process to exit or event to be signaled...")
            result = win32event.WaitForSingleObject(hProcess, win32event.INFINITE)
            
            if result == win32event.WAIT_OBJECT_0:
                print("Update child process exited normally.")
            else:
                print("Unexpected wait result:", result)
            
            win32api.CloseHandle(hProcess)

        except Exception as e:
            logger.error(f"Error launching update: {e}")
            self.update_process = None

# Example usage (for testing/debug)
if __name__ == "__main__":
    from queue import Queue
    q = Queue()
    security = securityStat(resultQueue=q)
    security.get_defender_status()
    time.sleep(10)