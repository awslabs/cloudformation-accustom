""" Decorators for the accustom library.

This includes two decorators, one for the handler function, and one to apply to any resource handling
functions.
"""

#Exceptions
from .Exceptions import FailedToSendResponseException
from .Exceptions import DataIsNotDictException
from .Exceptions import InvalidResponseStatusException

#Constants
from .constants import RequestType
from .constants import Status
from .constants import RedactMode

# Required Libraries
import logging
import json
from functools import wraps
from uuid import uuid4
from .response import ResponseObject
import six
import re

logger = logging.getLogger(__name__)

def decorator(enforceUseOfClass=False,hideResourceDeleteFailure=False,redactProperties=None,redactMode=RedactMode.BLACKLIST):
    """Decorate a function to add exception handling and emit CloudFormation responses.

    Usage with Lambda:
        >>> import accustom
        >>> @accustom.decorator()
        ... def function_handler(event, context)
        ...     sum = (float(event['ResourceProperties']['key1']) +
        ...            float(event['ResourceProperties']['key2']))
        ...     return { 'sum' : sum }

    Usage outside Lambda:
        >>> import accustom
        >>> @accustom.decorator()
        ... def function_handler(event)
        ...     sum = (float(event['ResourceProperties']['key1']) +
        ...            float(event['ResourceProperties']['key2']))
        ...     r = accustom.ResponseObject(data={'sum':sum},physicalResourceId='abc')
        ...     return r

    Args:
        enforceUseOfClass (boolean): When true send a FAILED signal if a ResponseObject class is not utilised.
            This is implicitly set to true if no Lambda Context is provided.
        hideResourceDeleteFailure (boolean): When true will return SUCCESS even on getting an Exception for DELETE requests.
        redactProperties (dictionary of lists, regex as key, list of top level properties to redact): When provided and logging
            set to debug in blacklist mode these properties will be replaced with the [REDACTED] string in the output when ResourceType
            matches regex, or in whitelist mode these properties will be included and all other properties replaced with the [REDACTED]
            string in the output when ResourceType matches regex
        redactMode (RedactMode.BLACKLIST or RedactMode.WHITELIST): Determine if we should whitelist or blacklist resources, defaults to
            blacklist

    Returns:
        The response object sent to CloudFormation

    Raises:
         FailedToSendResponseException
    """
    def inner_decorator(func):
        @wraps(func)
        def handler_wrapper(event, lambdaContext=None):
            logger.info('Request recieved, processing...')

            # Debug Logging Handler
            if logger.getEffectiveLevel() <= logging.DEBUG:
                # Start with None to prevent copying unless it is needed
                ec = event.copy()
                if redactMode == RedactMode.BLACKLIST:
                    if 'ResourceProperties' in ec: ec['ResourceProperties'] = ec['ResourceProperties'].copy()
                    if 'OldResourceProperties' in ec: ec['OldResourceProperties'] = ec['OldResourceProperties'].copy()
                elif redactMode == RedactMode.WHITELIST:
                    if 'ResourceProperties' in ec: ec['ResourceProperties'] = {}
                    if 'OldResourceProperties' in ec: ec['OldResourceProperties'] = {}
                else:
                    logger.warn('redactMode %s unsupported, not redacting properties' % redactMode)
                    redactMode = RedactMode.UNSUPPORT

                if redactMode != RedactMode.UNSUPPORT and redactedProperties is not None:
                    if isinstance(redactedProperties, dict):
                        for regex, iprops in redactedProperties.items():
                            if isinstance(iprops, list):
                                # Check if ResourceType matches regex
                                if re.search(regex, event['ResourceType']) is not None:
                                    # Go through the Properties looking to see if they're in the ResourceProperties or OldResourceProperties
                                    for index, item in enumerate(iprops):
                                        if redactMode == RedactMode.BLACKLIST:
                                            if 'ResourceProperties' in ec and item in ec['ResourceProperties']: ec['ResourceProperties'][item] = '[REDACTED]'
                                            if 'OldResourceProperties' in ec and item in ec['OldResourceProperties']: ec['OldResourceProperties'][item] = '[REDACTED]'
                                        elif redactMode == RedactMode.WHITELIST:
                                            if 'ResourceProperties' in ec and item in event['ResourceProperties'] : ec['ResourceProperties'][item] = event['ResourceProperties'][item]
                                            if 'OldResourceProperties' in ec and item in event['OldResourceProperties'] : ec['OldResourceProperties'][item] = event['OldResourceProperties'][item]
                            elif iprops is None:
                                # Since the sdecorator will pass None here by default we don't want to error if this happens
                                pass
                            else:
                                logger.warn('For regex %s a list was not provided, ignoring' % key)
                    else:
                        logger.warn('Provided redactedProperties was not of type dict, ignoring')

                if redactMode == RedactMode.WHITELIST:
                    if 'ResourceProperties' in ec:
                        for key, value in event['ResourceProperties'].items():
                            if key not in ec['ResourceProperties']: ec['ResourceProperties'][key] = '[REDACTED]'
                    if 'OldResourceProperties' in ec:
                        for key, value in event['OldResourceProperties'].items():
                            if key not in ec['OldResourceProperties']: ec['OldResourceProperties'][key] = '[REDACTED]'

                logger.debug('Request Body:\n' + json.dumps(ec))

            try:
                # Run the function
                if lambdaContext is not None:
                    result = func(event, lambdaContext)
                else:
                    result = func(event)

            except Exception as e:
                # If there was an exception thrown by the function, send a failure response
                result = ResponseObject(
                            physicalResourceId=uuid4().hex if lambdaContext is None else None,
                            reason='Function %s failed due to exception "%s"' % (func.__name__, str(e)),
                            responseStatus=Status.FAILED)
                logger.error(result.reason)

            if not isinstance(result, ResponseObject):
                # If a ResponseObject is not provided, work out what kind of response object to pass, or return a failure if it is an
                # invalid response type, or if the enforceUseOfClass is explicitly or implicitly set.
                if lambdaContext is None:
                    result = ResponseObject(
                            reason='Response Object of type %s was not a ResponseObject and there is no Lambda Context' % result.__class__,
                            responseStatus=Status.FAILED)
                    logger.error(result.reason)
                elif enforceUseOfClass:
                    result = ResponseObject(
                            reason='Response Object of type %s was not a ResponseObject instance and enforceUseOfClass set to true' % result.__class__,
                            responseStatus=Status.FAILED)
                    logger.error(result.reason)
                elif result is False:
                    result = ResponseObject(
                            reason='Function %s returned False.'% func.__name__,
                            responseStatus=Status.FAILED)
                    logger.debug(result.reason)
                elif isinstance(result, dict):
                    result = ResponseObject(data=result)
                elif isinstance(result, six.string_types):
                    result = ResponseObject(data={'Return' : result})
                elif result is None or result is True:
                    result = ResponseObject()
                else:
                    result = ResponseObject(
                            reason='Return value from Function %s is of unsupported type %s' % (func.__name__,result.__class__),
                            responseStatus=Status.FAILED)
                    logger.error(result.reason)

            # This block will hide resources on delete failure if the flag is set to true
            if event['RequestType'] == RequestType.DELETE and result.responseStatus == Status.FAILED and hideResourceDeleteFailure:
                    logger.warn('Hiding Resource DELETE request failure')
                    if result.data is not None:
                        if not result.squashPrintResponse: 
                            logger.debug('Data:\n' + json.dumps(result.data))
                        else:
                            logger.debug('Data: [REDACTED]')
                    if result.reason is not None: logger.debug('Reason: %s' % result.reason)
                    if result.physicalResourceId is not None: logger.debug('PhysicalResourceId: %s' % result.physicalResourceId)
                    result = ResponseObject(
                            reason='There may be resources created by this Custom Resource that have not been cleaned up despite the fact this resource is in DELETE_COMPLETE',
                            physicalResourceId=result.physicalResourceId,
                            responseStatus=Status.SUCCESS)

            try:
                returnValue = result.send(event, lambdaContext)
            except Exception as e:
                if isinstance(e, FailedToSendResponseException):
                    raise e
                logger.error('Malformed request, Exception: %s' % str(e))
                if result.data is not None and not isinstance(e, DataIsNotDictException):
                        if not result.squashPrintResponse: 
                            logger.debug('Data:\n' + json.dumps(result.data))
                        else:
                            logger.debug('Data: [REDACTED]')
                if result.reason is not None: logger.debug('Reason: %s' % result.reason)
                if result.physicalResourceId is not None: logger.debug('PhysicalResourceId: %s' % result.physicalResourceId)
                if not isinstance(e, InvalidResponseStatusException): logger.debug('Status: %s' % result.responseStatus)
                result = ResponseObject(
                        reason='Malformed request, Exception: %s' % str(e),
                        physicalResourceId=result.physicalResourceId,
                        responseStatus=Status.FAILED)
                returnValue = result.send(event, lambdaContext)
            return returnValue
        return handler_wrapper
    return inner_decorator

def rdecorator(decoratorHandleDelete=False,expectedProperties=None,genUUID=True):
    """Decorate a function to add input validation for resource handler functions.


        Usage with Lambda:
            >>> import accustom
            >>> @accustom.rdecorator(expectedProperties=['key1','key2'],genUUID=False)
            ... def resource_function(event, context):
            ...     sum = (float(event['ResourceProperties']['key1']) +
            ...            float(event['ResourceProperties']['key2']))
            ...     return { 'sum' : sum }
            >>> @accustom.decorator()
            ... def function_handler(event, context)
            ...     return resource_function(event,context)

        Usage outside Lambda:
            >>> import accustom
            >>> @accustom.rdecorator(expectedProperties=['key1','key2'])
            ... def resource_function(event, context=None)
            ...     sum = (float(event['ResourceProperties']['key1']) +
            ...            float(event['ResourceProperties']['key2']))
            ...     r = accustom.ResponseObject(data={'sum':sum},physicalResourceId=event['PhysicalResourceId'])
            ...     return r
            >>> @accustom.decorator()
            ... def function_handler(event)
            ...     return resource_function(event)

        Args:
            decoratorHandleDelete (boolean): When set to true, if a delete request is made in event the decorator will
                return a ResponseObject with a with SUCCESS without actually executing the decorated function
            genUUID (boolean): When set to true, if the PhysicalResourceId in the event is not set, automatically generate
                a UUID4 and put it in the PhysicalResoruceId field.
            expectedProperties (list of expected properties): Pass in a list or tuple of properties that you want to check for before running
                the decorated function.

        Returns:
            The result of the decorated function, or a ResponseObject with SUCCESS depending on the event and flags.

        Raises:
            Any exception raised by the decorated function.

    """
    def resource_decorator_inner(func):
        @wraps(func)
        def resource_decorator_handler(event, context=None):
            logger.info('Supported resource %s' % event['ResourceType'])

            # Set the Physical Resource ID to a randomly generated UUID if it is not present
            if genUUID and 'PhysicalResourceId' not in event:
                event['PhysicalResourceId'] = uuid4().hex
                logger.info('Set PhysicalResourceId to %s' % event['PhysicalResourceId'])

            # Handle Delete when decoratorHandleDelete is set to True
            if decoratorHandleDelete and event['RequestType'] == RequestType.DELETE:
                logger.info('Request type %s detected, returning success without calling function' % RequestType.DELETE )
                return ResponseObject(physicalResourceId=event['PhysicalResourceId'])

            # Validate important properties exist
            if expectedProperties is not None and isinstance(expectedProperties, (list, tuple)):
                for index, item in enumerate(expectedProperties):
                    if item not in event['ResourceProperties']:
                        errMsg = 'Property %s missing, sending failure signal' % item
                        logger.info(errMsg)
                        return ResponseObject(reason=errMsg,responseStatus=Status.FAILED,physicalResourceId=event['PhysicalResourceId'])

            # If a list or tuple was not provided then log a warning
            elif expectedProperties is not None:
                logger.warn('expectedProperties passed to decorator is not a list, properties were not validated.')

            # Pre-validation complete, calling function
            return func(event, context)
        return resource_decorator_handler
    return resource_decorator_inner

def sdecorator(decoratorHandleDelete=False,expectedProperties=None,genUUID=True,enforceUseOfClass=False,hideResourceDeleteFailure=False,redactProperties=None,redactMode=RedactMode.BLACKLIST):
    """Decorate a function to add input validation for resource handler functions, exception handling and send
    CloudFormation responses.


    Usage with Lambda:
        >>> import accustom
        >>> @accustom.sdecorator(expectedProperties=['key1','key2'],genUUID=False)
        ... def resource_handler(event, context):
        ...     sum = (float(event['ResourceProperties']['key1']) +
        ...            float(event['ResourceProperties']['key2']))
        ...     return { 'sum' : sum }

    Usage outside Lambda:
        >>> import accustom
        >>> @accustom.sdecorator(expectedProperties=['key1','key2'])
        ... def resource_handler(event, context=None)
        ...     sum = (float(event['ResourceProperties']['key1']) +
        ...            float(event['ResourceProperties']['key2']))
        ...     r = accustom.ResponseObject(data={'sum':sum},physicalResourceId=event['PhysicalResourceId'])
        ...     return r

    Args:
        decoratorHandleDelete (boolean): When set to true, if a delete request is made in event the decorator will
            return SUCCESS to CloudFormation without actually executing the decorated function
        genUUID (boolean): When set to true, if the PhysicalResourceId in the event is not set, automatically generate
            a UUID4 and put it in the PhysicalResoruceId field.
        expectedProperties (list of expected properties): Pass in a list or tuple of properties that you want to check for
            before running the decorated function.
        enforceUseOfClass (boolean): When true send a FAILED signal if a ResponseObject class is not utilised.
            This is implicitly set to true if no Lambda Context is provided.
        hideResourceDeleteFailure (boolean): When true will return SUCCESS even on getting an Exception for DELETE requests.
            Note that this particular flag is made redundant if decoratorHandleDelete is set to True.
        redactProperties (list of top level properties to redact): When provided and logging
            set to debug these properties will be replaced with the [REDACTED] string in the output in blacklist mode, or these properties
            will be included and all other properties will be replaced with the [REDACTED] string in the output.
        redactMode (RedactMode.BLACKLIST or RedactMode.WHITELIST): Determine if we should whitelist or blacklist resources, defaults to
            blacklist

    Returns:
        The response object sent to CloudFormation

    Raises:
         FailedToSendResponseException
    """

    def standalone_decorator_inner(func):
        @wraps(func)
        @decorator(enforceUseOfClass=enforceUseOfClass,hideResourceDeleteFailure=hideResourceDeleteFailure,redactProperties={'^.*$' : redactProperties},redactMode=redactMode)
        @rdecorator(decoratorHandleDelete=decoratorHandleDelete,expectedProperties=expectedProperties,genUUID=genUUID)
        def standalone_decorator_handler(event, lambdaContext=None):
            return func(event, lambdaContext)
        return standalone_decorator_handler
    return standalone_decorator_inner
