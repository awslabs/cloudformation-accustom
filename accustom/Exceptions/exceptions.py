""" Exceptions for the accustom library.

These are the exceptions that can be returned by accustom
"""

class NoPhysicalResourceIdException(Exception):
    """Indicates that there was no valid value to use for PhysicalResourceId"""
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class InvalidResponseStatusException(Exception):
    """Indicates that there response code was not SUCCESS or FAILED"""
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class DataIsNotDictException(Exception):
    """Indicates that a Dictionary was not passed as Data"""
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class FailedToSendResponseException(Exception):
    """Indicates there was a problem sending the response"""
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)
