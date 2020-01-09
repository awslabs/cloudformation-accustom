import logging
logging.getLogger().setLevel(logging.DEBUG)

from accustom import sdecorator as decorator
from time import sleep

logger = logging.getLogger(__name__)


@decorator(hideResourceDeleteFailure=True,
           decoratorHandleDelete=True,
           timeoutFunction=True,
           genUUID=True)
def handler(event,context):
    logger.info('Sleeping for 30 seconds')
    sleep(30)