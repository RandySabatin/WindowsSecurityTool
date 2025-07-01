import sys
import os
import logging
import multiprocessing
from multiprocessing import Process
import time 
import win32event
import win32api

parentdir = (os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parentdir)

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtWidgets import QDesktopWidget, QFileDialog
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QTextCursor

    from lib.UtilLog import UtilLog
    from lib.UtilProcess import ProcessUtils
    from lib.mainFunctions import securityStat, securityScan, securityUpdate
    import UI.mainWindow_ui as MAINWINDOW_UI

    if (os.path.exists(os.getcwd() + r'/log')) == False:
        os.makedirs('log')
    formatter="%(asctime)s [%(levelname)s]\t [%(process)x:%(thread)x][%(funcName)s]   - %(message)s - [%(filename)s(%(lineno)d)]"
    UtilLog.setup_logger('Tool', "log/Tool.log", logging.INFO, formatter = formatter)
    logger = UtilLog.getLogger("Tool")
    logger.info("-------------------------------------Start-------------------------------------")
    
except Exception as err:
    print(str(err))


class MainWindow(MAINWINDOW_UI.Ui_MainWindow, QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            super().setupUi(self)
            
            self.resultQueue = multiprocessing.Queue()
            self.eventChildSentFinish = multiprocessing.Event()
            self.eventUpdateFinish = multiprocessing.Event()
            
            self.statusTimer = QTimer(self)
            self.statusTimer.timeout.connect(self.statusMonitor)

            self.scanTimer = QTimer(self)
            self.scanTimer.timeout.connect(self.scanMonitor)

            self.updateTimer = QTimer(self)
            self.updateTimer.timeout.connect(self.updateMonitor)
            
            self.isForceStop = False
            self.process = None
            self.isProcessOn = False
            self.time2Check = 0
            
            event_scan_stop = 'Global\\__scan_stop'
            event_scan_end = 'Global\\__scan_end'
            # Create a named, manual-reset, initially non-signaled event
            self.hEventScanStop = win32event.CreateEvent(None, True, False, event_scan_stop)
            self.hEventScanEnd = win32event.CreateEvent(None, True, False, event_scan_end)

        except Exception as err:
            logger.exception(str(err))

    def setupUI(self):  # Entry point of the whole class
        self.setupPerimeter()

        self.cursor_av_textBrowser = QTextCursor(self.av_textBrowser.document())
        self.cursor_fw_textBrowser = QTextCursor(self.fw_textBrowser.document())
        self.cursor_wp_textBrowser = QTextCursor(self.wp_textBrowser.document())

        self.cursor_settings_textBrowser = QTextCursor(self.settings_textBrowser.document())
        self.cursor_version_textBrowser = QTextCursor(self.version_textBrowser.document())

        #get status of Windows Security
        self.status_pushButton.clicked.connect(self.startStatusRun)

        #perform scan
        self.path_pushButton.setEnabled(False)
        self.QS_radioButton.clicked.connect(self.setScanUI)
        self.FS_radioButton.clicked.connect(self.setScanUI)
        self.CS_radioButton.clicked.connect(self.setScanUI)
        self.start_pushButton.clicked.connect(self.startScanRun)
        self.stop_pushButton.clicked.connect(lambda: self.stopScanRun(True))
        self.path_pushButton.clicked.connect(self.scanSetPath)

        #perform update
        self.update_pushButton.clicked.connect(self.startUpdateRun)

        print('UI is up')

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2)
    
    def setupPerimeter(self):
        perimeter_width = 980
        perimeter_height = 720
        self.setObjectName("Demo")
        self.setGeometry(QtCore.QRect(200, 200, perimeter_width, perimeter_height))
        self.center()

    def closeEvent(self, QCloseEvent):
        if self.process:
            self.process.terminate()
        QCloseEvent.accept()
        sys.exit(0)

    # end def

    def startUpdateRun(self):
        try:
            self.eventUpdateFinish.clear()

            self.updateTimer.start(1000)

            self.update_pushButton.setEnabled(False)

            process = Process(target=executeUpdate, args=(self.eventUpdateFinish,))

            process.start()

        except Exception as e:
            logger.error("startUpdate - " + str(e))
    # end def

    def updateMonitor(self):
        try:

            if (self.eventUpdateFinish.is_set()):
                self.eventUpdateFinish.clear()
                
                self.updateTimer.stop()
                self.update_pushButton.setEnabled(True)
        except Exception as err:
            logger.exception(str(err))

    def setScanUI(self):
        try:

            self.path_pushButton.setEnabled(False)
            self.stop_pushButton.setEnabled(False)

            self.start_pushButton.setEnabled(True)
            self.QS_radioButton.setEnabled(True)
            self.FS_radioButton.setEnabled(True)
            self.CS_radioButton.setEnabled(True)

            if self.CS_radioButton.isChecked():
                self.path_pushButton.setEnabled(True)

                scanPath = (self.path_lineEdit.text()).strip()
                if len(scanPath):
                    self.start_pushButton.setEnabled(True)
                else:
                    self.start_pushButton.setEnabled(False)

        except Exception as err:
            logger.exception(str(err))


    def startScanRun(self):
        try:
            scanPath = None
            self.QS_radioButton.setEnabled(False)
            self.FS_radioButton.setEnabled(False)
            self.CS_radioButton.setEnabled(False)

            self.path_pushButton.setEnabled(False)
            self.start_pushButton.setEnabled(False)

            if self.FS_radioButton.isChecked():
                scan_type = "FullScan"
            elif self.CS_radioButton.isChecked():
                scanPath = (self.path_lineEdit.text()).strip()
                scan_type = "CustomScan"
            else:
                scan_type = "QuickScan"
            
            process = Process(target=executeScan, args=(scan_type, \
                                                               scanPath))
            process.start()
            self.stop_pushButton.setEnabled(True)
            self.scanTimer.start(1000)

        except Exception as err:
            logger.exception(str(err))

    def stopScanRun(self,force=False):
        try:
            if force:
                win32event.SetEvent(self.hEventScanStop)
            self.setScanUI()

        except Exception as err:
            logger.exception(str(err))

    def scanSetPath(self):
        try:
            dir_str = QFileDialog.getExistingDirectory(None, "Select the path to scan", None, QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            if len(dir_str):
                dir_str = dir_str.replace('/', '\\')
                self.path_lineEdit.setText(dir_str)
                self.start_pushButton.setEnabled(True)

        except Exception as err:
            logger.exception(str(err))
    def scanMonitor(self):
        try:
            response = win32event.WaitForSingleObject(self.hEventScanEnd, 0)  # non-blocking check
            if response == win32event.WAIT_OBJECT_0:
                logger.info("EventScanEnd is signalled")
                win32event.ResetEvent(self.hEventScanEnd)
                self.scanTimer.stop()
                self.stopScanRun(False)

        except Exception as err:
            logger.exception(str(err))

    def startStatusRun(self):
        try:
            self.isForceStop = False

            self.clearQueue(self.resultQueue)
            self.eventChildSentFinish.clear()

            self.statusTimer.start(1000)

            self.status_pushButton.setEnabled(False)
            self.settings_textBrowser.clear()
            self.version_textBrowser.clear()

            self.process = Process(target=executeStatus, args=(self.resultQueue, \
                                                               self.eventChildSentFinish))

            self.process.start()
            self.isProcessOn = True
            self.time2Check = time.time()
        except Exception as e:
            logger.error("startStatusRun - " + str(e))
    # end def

    def clearQueue(self, mpQueue):
        try:
            while not mpQueue.empty():
                mpQueue.get()
        except Exception as e:
            logger.error("clearQueue - " + str(e))
    #end def

    def StopStatusRun(self):
        try:
            if (self.eventChildSentFinish.is_set()):
                return

            self.process.terminate()
            self.eventChildSentFinish.set()

            self.isForceStop = True

            return
        except Exception as e:
            logger.error("StopStatusRun - " + str(e))
            return
    # end def

    def statusMonitor(self):
        try:
            while not self.resultQueue.empty():
                result = self.resultQueue.get()

                print("RTMonitor - result: %s" % result)
                if "SendToSettingDisplay" in result["function"]:
                    res = result["message"]
                    self.append_TextBrowser("setting", res)

                elif "SendToProtectionDisplay" in result["function"]:
                    res = result["message"]["Antivirus"][0]
                    self.append_TextBrowser("av", res)

                elif "SendToVersionDisplay" in result["function"]:
                    res = result["message"]
                    self.append_TextBrowser("version", res)

                else:
                    res = result["message"]
                    self.append_TextBrowser("setting", res)


            #check every 6 seconds if the spawned process to run the scenario was terminated by others
            if (self.time2Check) and (time.time() - self.time2Check > 5):
                self.time2Check = time.time()
                current_PIDs = ProcessUtils.getAllProcessesToValues()

                if (self.isProcessOn) and (not self.eventChildSentFinish.is_set()) and (self.process.pid not in current_PIDs) and (self.resultQueue.empty()):
                    self.eventChildSentFinish.set()

            if (self.eventChildSentFinish.is_set()) and (self.resultQueue.empty()):
                self.eventChildSentFinish.clear()
                if self.isForceStop:
                    logger.info("Execution is forced stopped.")
                else:
                    logger.info("Finished Execution")
                
                self.process.join()
                self.isProcessOn = False
                self.statusTimer.stop()
                self.time2Check = 0
                self.status_pushButton.setEnabled(True)


        except Exception as err:
            logger.exception(str(err))

    def append_TextBrowser(self, window_name, receivedText):
        try:
            print("window name: ", window_name, " text", receivedText)
            # Determine which set of objects to use
            if "av" in window_name:
                text_browser_attr = "av_textBrowser"
                cursor_attr = "cursor_av_textBrowser"
            elif "setting" in window_name:
                text_browser_attr = "settings_textBrowser"
                cursor_attr = "cursor_settings_textBrowser"
            elif "version" in window_name:
                text_browser_attr = "version_textBrowser"
                cursor_attr = "cursor_version_textBrowser"
            else:
                return
            
            text_browser = getattr(self, text_browser_attr)
            cursor = getattr(self, cursor_attr)
            
            # Evaluate the expression with restricted environment
            #result = eval(receivedText, safe_globals, safe_locals)

            # Check if it's a dictionary
            if isinstance(receivedText, dict):
                for key, value in receivedText.items():
                    # Insert key-value pairs into the text browser
                    text_browser.moveCursor(QTextCursor.End)
                    cursor.insertHtml(f"<b>{key}: </b> {value}<br>")
            else:
                # Convert to string
                string_result = str(receivedText)
                text_browser.moveCursor(QTextCursor.End)
                cursor.insertHtml(string_result)
                cursor.insertHtml("<br>")

        except Exception as e:
            logger.error("append_TextBrowser - " + str(e))
    #end def

def executeStatus(resultQueue, \
                 eventChildSentFinish):
    try:
        Scenario = securityStat(resultQueue)
        logger.info("Starts Executing ")

        Scenario.get_defender_status(timeout=30)
        Scenario.get_antivirus_info()
        
        logger.info("Done Executing. ")
        del Scenario

        eventChildSentFinish.set()
        return            
    except Exception as err:
        logger.exception(str(err))

def executeScan(scanType, scanPath=None):
    try:
        event_scan_end = 'Global\\__scan_end'
        # Open the named event with permissions to set it
        hEvent = win32event.OpenEvent(
            win32event.SYNCHRONIZE | win32event.EVENT_MODIFY_STATE,
            False,
            event_scan_end)

        Scenario = securityScan()
        logger.info("Starts Executing ")

        Scenario.start_manual_scan(scanType, scanPath)
        
        logger.info("Done Executing. ")
        del Scenario

        win32event.SetEvent(hEvent)
        win32api.CloseHandle(hEvent)

        return            
    except Exception as err:
        logger.exception(str(err))

def executeUpdate(eventUpdateFinish):
    try:
        Scenario = securityUpdate()
        logger.info("Starts Executing Update")

        Scenario.start_update()
        
        logger.info("Done Executing Update")
        del Scenario

        eventUpdateFinish.set()
        return            
    except Exception as err:
        logger.exception(str(err))