from accustom import sdecorator as decorator
from time import sleep


@decorator(hideResourceDeleteFailure=True,
           decoratorHandleDelete=True,
           timeoutFunction=True,
           genUUID=True)
def handler():
    sleep(30)