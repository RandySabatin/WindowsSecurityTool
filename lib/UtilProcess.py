import psutil
from lib.UtilLog import UtilLog

logger = UtilLog.getLogger("Tool")

class ProcessUtils(object):
    @staticmethod
    def getAllProcesses():
        pIdDict={}
        pIds = psutil.pids()
        for pId in pIds:
            try:
                p = psutil.Process(pId)
            except psutil.NoSuchProcess as e:
                logger.error(str(e))
                continue
            pIdDict[p.name().lower()] = pId
        return pIdDict

    @staticmethod
    def getAllProcessesToValues():
        pIdDict={}
        pIds = psutil.pids()
        for pId in pIds:
            try:
                p = psutil.Process(pId)
                pIdDict[pId] = str(p.name()).lower()
            except:
                continue
        return pIdDict

    @staticmethod
    def getProcessState(pId):
        try:
            p = psutil.Process(int(pId))
            return p.status()
        except Exception as err:
            print(str(err))
            return ""

    @staticmethod
    def processExits(processName, pIdDict):
        return processName.lower() in pIdDict

    @staticmethod
    def getProcessExePath(processName, pIdDict):
        if processName.lower() in pIdDict:
            p = psutil.Process(pIdDict[processName.lower()])
            try:
                return p.exe()
            except psutil.AccessDenied:
                logger.error("AccessDenied for getProcessExePath {}".format(processName))
                return ""
