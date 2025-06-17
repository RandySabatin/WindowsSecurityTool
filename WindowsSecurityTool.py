import sys
import os
import logging
import multiprocessing
from multiprocessing import Process

parentdir = (os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parentdir)

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtWidgets import QDesktopWidget, QFileDialog
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QTextCursor

    from lib.UtilLog import UtilLog
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
        super().__init__(parent)
        super().setupUi(self)


    def setupUI(self):  # Entry point of the whole class
        self.setupPerimeter()
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