# -*- coding: UTF-8 -*-

import os
import platform
import ConfigParser
import logging.handlers

__config = None
configFile = './config.ini'

defaultLogName = 'python_log'


def _getConfig():
    global __config
    global configFile
    if not __config:
        __config = ConfigParser.RawConfigParser()
        if not __config.read(os.path.abspath(configFile)):
            print ("Configuration file for logging not found: %s" % os.path.abspath(configFile))
            exit(1)
    return __config


def getLogger(logName=None):
    if not logName:
        logName = defaultLogName
    logger = logging.getLogger('ru.caa.%s' % logName)
    if logger.getEffectiveLevel() != logging.INFO:
        logger = configureLogger(logger, logName)
    return logger


def configureLogger(logger, logName):
    parentDir = _getConfig().get('LOG', 'directoryWin') if platform.system() == "Windows" else _getConfig().get('LOG', 'directory')
    logOnConsole = _getConfig().getboolean('LOG', 'log_on_console')
    if not os.path.exists(parentDir):
        os.makedirs(parentDir)
    handler = logging.handlers.RotatingFileHandler('%s/%s.log' % (parentDir, logName), maxBytes=50000000, backupCount=15, delay=False)
    formater = logging.Formatter('%(asctime)s %(levelname)-3s %(message)s %(module)5s(%(lineno)s)')
    handler.setFormatter(formater)
    logger.addHandler(handler)
    if logOnConsole:
        handler = logging.StreamHandler()
        handler.setFormatter(formater)
        logger.addHandler(handler)

    logger.setLevel(logging._levelNames[_getConfig().get('LOG', 'log_level')])
    return logger
