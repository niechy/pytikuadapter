
from loguru import logger
from time import strftime,localtime
def loginit(level):
    logger.add(strftime("%Y-%m-%d", localtime()) + ".log", rotation="10 MB", level=level)