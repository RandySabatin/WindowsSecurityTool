import sys
import os
import logging
import multiprocessing
from multiprocessing import Process
import time 

parentdir = (os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parentdir)

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtWidgets import QDesktopWidget, QFileDialog
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QTextCursor

    from lib.UtilLog import UtilLog
    from lib.UtilProcess import ProcessUtils
    from lib.mainFunctions import winSecurity
    import UI.mainWindow_ui as MAINWINDOW_UI

    safe_globals = {"__builtins__": None}
    safe_locals = {}

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
        super().__init__(parent)
        super().setupUi(self)

        self.resultQueue = multiprocessing.Queue()
        self.eventChildSentFinish = multiprocessing.Event()

        self.Timer = QTimer(self)
        self.Timer.timeout.connect(self.RTMonitor)

        self.isForceStop = False
        self.process = None
        self.isProcessOn = False
        self.time2Check = 0

    def setupUI(self):  # Entry point of the whole class
        self.setupPerimeter()

        self.cursor_av_textBrowser = QTextCursor(self.av_textBrowser.document())
        self.cursor_fw_textBrowser = QTextCursor(self.fw_textBrowser.document())
        self.cursor_wp_textBrowser = QTextCursor(self.wp_textBrowser.document())

        self.cursor_settings_textBrowser = QTextCursor(self.settings_textBrowser.document())
        self.cursor_update_textBrowser = QTextCursor(self.update_textBrowser.document())

        self.status_pushButton.clicked.connect(self.startStatusRun)

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

    def stopScanUI(self):
        try:

            self.path_lineEdit.setEnabled(False)
            self.path_pushButton.setEnabled(False)
            self.start_pushButton.setEnabled(True)
            self.stop_pushButton.setEnabled(False)

            self.QS_radioButton.setEnabled(True)
            self.FS_radioButton.setEnabled(True)
            self.CS_radioButton.setEnabled(True)

            self.path_lineEdit.setEnabled(True)
            self.path_pushButton.setEnabled(True)

            #UserPath = (self.path_lineEdit.text()).strip()
            #if len(UserPath):
                #self.start_pushButton.setEnabled(True)

        except Exception as err:
            logger.exception(str(err))


    def startScanUI(self):
        try:

            self.QS_radioButton.setEnabled(False)
            self.FS_radioButton.setEnabled(False)
            self.CS_radioButton.setEnabled(False)

            self.path_lineEdit.setEnabled(False)
            self.path_pushButton.setEnabled(False)
            self.start_pushButton.setEnabled(False)
            self.stop_pushButton.setEnabled(True)

        except Exception as err:
            logger.exception(str(err))

    def startStatusRun(self):
        try:
            self.isForceStop = False

            self.clearQueue(self.resultQueue)
            self.eventChildSentFinish.clear()

            self.Timer.start(1000)

            self.status_pushButton.setEnabled(False)
            self.settings_textBrowser.clear()
            self.update_textBrowser.clear()

            self.process = Process(target=executeScript, args=(self.resultQueue, \
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

    def RTMonitor(self):
        try:
            while not self.resultQueue.empty():
                result = self.resultQueue.get()

                print("RTMonitor - result: %s" % result)
                if "SendToSettingDisplay" in result["function"]:
                    res = result["message"]
                    self.append_TextBrowser("setting", res)

                elif "SendToProtectionDisplay" in result["function"]:
                    res = result["message"]
                    self.append_TextBrowser("av", res)

                elif "SendToVersionDisplay" in result["function"]:
                    res = result["message"]
                    self.append_TextBrowser("update", res)

                else:
                    res = result["message"]
                    self.append_TextBrowser("setting", res)


            #check every 6 seconds if the spawned process to run the scenario was terminated by others
            if (self.time2Check) and (time.time() - self.time2Check > 5):
                self.time2Check = time.time()
                current_PIDs = ProcessUtils.getAllProcessesToValues()

                if (self.isProcessOn) and (not self.eventChildSentFinish.is_set()) and (self.process.pid not in current_PIDs) and (self.resultQueue.empty()):
                    self.append_ExecutionStatus("<font color=%s>%s</font>" % ('red', "Scenario execution was terminated. Please verify if your anti-virus is set to monitor-only mode."))
                    self.eventChildSentFinish.set()

            if (self.eventChildSentFinish.is_set()) and (self.resultQueue.empty()):
                self.eventChildSentFinish.clear()
                if self.isForceStop:
                    logger.info("Execution is forced stopped.")
                else:
                    logger.info("Finished Execution")
                
                self.process.join()
                self.isProcessOn = False
                self.Timer.stop()
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
            elif "update" in window_name:
                text_browser_attr = "update_textBrowser"
                cursor_attr = "cursor_update_textBrowser"
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

def executeScript(resultQueue, \
                 eventChildSentFinish):
    try:
        Scenario = winSecurity(resultQueue)
        logger.info("Starts Executing ")

        Scenario.get_defender_status(timeout=30)
        
        logger.info("Done Executing. ")
        del Scenario

        eventChildSentFinish.set()
        return            
    except Exception as err:
        logger.exception(str(err))