# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

""" Decorators for the accustom library.

This includes two decorators, one for the handler function, and one to apply to any resource handling
functions.
"""

# Exceptions
from .Exceptions import FailedToSendResponseException
from .Exceptions import DataIsNotDictException
from .Exceptions import InvalidResponseStatusException
from .Exceptions import NotValidRequestObjectException

# Constants
from .constants import RequestType
from .constants import Status

# Response
from .response import is_valid_event

# RedactionConfig
from .redaction import RedactionConfig
from .redaction import StandaloneRedactionConfig

# Required Libraries
import logging
import json
from functools import wraps
from uuid import uuid4
from .response import ResponseObject
import six
from boto3 import client
from botocore.client import Config
from botocore import exceptions as bexceptions

logger = logging.getLogger(__name__)

# Import Requests
try:
    import requests
except ImportError:
    from botocore.vendored import requests
    logger.warning("botocore.vendored version of requests is deprecated. Please include requests in your code bundle.")


# Time in milliseconds to set the alarm for (in milliseconds)
# Should be set to twice the worst case response time to send to S3
# Setting to 2 seconds for safety
TIMEOUT_THRESHOLD = 2000


def decorator(enforceUseOfClass: bool = False, hideResourceDeleteFailure: bool = False,
              redactConfig: RedactionConfig = None, timeoutFunction: bool = False):
    """Decorate a function to add exception handling and emit CloudFormation responses.

    Usage with Lambda:
        import accustom
        @accustom.decorator()
        def function_handler(event, context)
            sum = (float(event['ResourceProperties']['key1']) +
                   float(event['ResourceProperties']['key2']))
            return { 'sum' : sum }

    Usage outside Lambda:
        import accustom
        @accustom.decorator()
        def function_handler(event)
            sum = (float(event['ResourceProperties']['key1']) +
                   float(event['ResourceProperties']['key2']))
            r = accustom.ResponseObject(data={'sum':sum},physicalResourceId='abc')
            return r

    Args:
        enforceUseOfClass (boolean): When true send a FAILED signal if a ResponseObject class is not utilised.
            This is implicitly set to true if no Lambda Context is provided.
        hideResourceDeleteFailure (boolean): When true will return SUCCESS even on getting an Exception for
            DELETE requests.
        redactConfig (RedactionConfig): Configuration of how to redact the event object.
        timeoutFunction (boolean): Will automatically send a failure signal to CloudFormation before Lambda timeout
            provided that this function is executed in Lambda

    Returns:
        dict: The response object sent to CloudFormation

    Raises:
        FailedToSendResponseException
        NotValidRequestObjectException

    Decorated Function Arguments:
        event (dict): The request object being processed (Required).
        context (dict): The Lambda context of this execution (optional)

    """

    def inner_decorator(func):
        @wraps(func)
        def handler_wrapper(event: dict, context: dict = None):
            nonlocal redactConfig
            nonlocal timeoutFunction
            logger.info('Request received, processing...')
            if not is_valid_event(event):
                # If it is not a valid event we need to raise an exception
                message = 'The event object passed is not a valid Request Object as per ' + \
                          'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html'
                logger.error(message)
                raise NotValidRequestObjectException(message)

            # Timeout Function Handler
            if 'LambdaParentRequestId' in event:
                logger.info('This request has been invoked as a child, for parent logs please see request ID: %s' %
                            event['LambdaParentRequestId'])
            elif context is None and timeoutFunction:
                logger.warning('You cannot use the timeoutFunction option outside of Lambda. To suppress this warning' +
                               ', set timeoutFunction to False')
            elif timeoutFunction:
                # Attempt to invoke the function. Depending on the error we get may continue execution or return
                logger.info('Request has been invoked in Lambda with timeoutFunction set, attempting to invoke self')
                pevent = event.copy()
                pevent['LambdaParentRequestId'] = context.aws_request_id
                payload = json.dumps(pevent).encode('UTF-8')
                timeout = (context.get_remaining_time_in_millis() - TIMEOUT_THRESHOLD) / 1000
                # Edge case where time is set to very low timeout, use half the timeout threshold as the timeout for the
                # the Lambda Function
                if timeout <= 0: timeout = TIMEOUT_THRESHOLD / 2000
                config = Config(connect_timeout=2, read_timeout=timeout, retries={'max_attempts': 0})
                b_lambda = client('lambda', config=config)

                # Normally we would just do a catch all error handler but in this case we want to be paranoid
                try:
                    response = b_lambda.invoke(FunctionName=context.invoked_function_arn,
                                               InvocationType='RequestResponse', Payload=payload)
                    # Further checks
                    if 'FunctionError' in response:
                        response.get('Payload', ''.encode('UTF-8'))
                        message = 'Invocation got an error: %s' % payload.decode()
                        logger.error(message)
                        return ResponseObject(reason=message, responseStatus=Status.FAILED).send(event, context)
                    else:
                        # In this case the function returned without error which means we can assume the chained
                        # invokation sent a response, so we do not have too.
                        logger.info('Compeleted execution of chained invocation, returning payload')
                        response.get('Payload', ''.encode('UTF-8'))
                        return payload.decode()

                except bexceptions.ClientError as e:
                    logger.warning('Caught exception %s while trying to invoke function. Running handler locally.'
                                   % str(e))
                    logger.warning('You cannot use the timeoutFunction option without the ability for the function to' +
                                   ' invoke itself. To suppress this warning, set timeoutFunction to False')
                except bexceptions.ConnectionError as e:
                    logger.error('Got error %s while trying to invoke function. Running handler locally' % str(e))
                    logger.error('You cannot use the timeoutFunction option without the ability to connect to the ' +
                                 'Lambda API from within the function. As we may not have time to execute the ' +
                                 'function, returning failure.')
                    return ResponseObject(reason='Unable to call Lambda to do chained invoke, returning failure.',
                                          responseStatus=Status.FAILED).send(event, context)
                except bexceptions.ReadTimeoutError:
                    # This should be a critical failure
                    logger.error('Waited the read timeout and function did not return, returning an error')
                    return ResponseObject(reason='Lambda function timed out, returning failure.',
                                          responseStatus=Status.FAILED).send(event, context)
                except Exception as e:
                    message = 'Got an %s I did not understand while trying to invoke child function: %s' % (e.__class__,
                                                                                                            str(e))
                    logger.error(message)
                    return ResponseObject(reason=message, responseStatus=Status.FAILED).send(event, context)

            # Debug Logging Handler
            if logger.getEffectiveLevel() <= logging.DEBUG:
                if context is not None:
                    logger.debug('Running request with Lambda RequestId: %s' % context.aws_request_id)
                if redactConfig is not None and isinstance(redactConfig, (StandaloneRedactionConfig, RedactionConfig)):
                    logger.debug('Request Body:\n' + json.dumps(redactConfig._redact(event)))
                elif redactConfig is not None:
                    logger.warning('A non valid RedactionConfig was provided, and ignored')
                    logger.debug('Request Body:\n' + json.dumps(event))
                else:
                    logger.debug('Request Body:\n' + json.dumps(event))

            try:
                logger.info('Running CloudFormation request %s for stack: %s' % (event['RequestId'], event['StackId']))
                # Run the function
                if context is not None:
                    result = func(event, context)
                else:
                    result = func(event)

            except Exception as e:
                # If there was an exception thrown by the function, send a failure response
                result = ResponseObject(
                    physicalResourceId=str(uuid4()) if context is None else None,
                    reason='Function %s failed due to exception "%s"' % (func.__name__, str(e)),
                    responseStatus=Status.FAILED)
                logger.error(result.reason)

            if not isinstance(result, ResponseObject):
                # If a ResponseObject is not provided, work out what kind of response object to pass, or return a
                # failure if it is an invalid response type, or if the enforceUseOfClass is explicitly or implicitly set
                if context is None:
                    result = ResponseObject(
                        reason='Response Object of type %s was not a ResponseObject and there is no Lambda Context'
                               % result.__class__,
                        responseStatus=Status.FAILED)
                    logger.error(result.reason)
                elif enforceUseOfClass:
                    result = ResponseObject(
                        reason='Response Object of type %s was not a ResponseObject instance and ' +
                               'enforceUseOfClass set to true' % result.__class__,
                        responseStatus=Status.FAILED)
                    logger.error(result.reason)
                elif result is False:
                    result = ResponseObject(
                        reason='Function %s returned False.' % func.__name__,
                        responseStatus=Status.FAILED)
                    logger.debug(result.reason)
                elif isinstance(result, dict):
                    result = ResponseObject(data=result)
                elif isinstance(result, six.string_types):
                    result = ResponseObject(data={'Return': result})
                elif result is None or result is True:
                    result = ResponseObject()
                else:
                    result = ResponseObject(
                        reason='Return value from Function %s is of unsupported type %s' % (func.__name__,
                                                                                            result.__class__),
                        responseStatus=Status.FAILED)
                    logger.error(result.reason)

            # This block will hide resources on delete failure if the flag is set to true
            if event['RequestType'] == RequestType.DELETE and result.responseStatus == Status.FAILED \
                    and hideResourceDeleteFailure:
                logger.warning('Hiding Resource DELETE request failure')
                if result.data is not None:
                    if not result.squashPrintResponse:
                        logger.debug('Data:\n' + json.dumps(result.data))
                    else:
                        logger.debug('Data: [REDACTED]')
                if result.reason is not None: logger.debug('Reason: %s' % result.reason)
                if result.physicalResourceId is not None: logger.debug('PhysicalResourceId: %s'
                                                                       % result.physicalResourceId)
                result = ResponseObject(
                    reason='There may be resources created by this Custom Resource that have not been cleaned' +
                           'up despite the fact this resource is in DELETE_COMPLETE',
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.SUCCESS)

            try:
                return_value = result.send(event, context)
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
                if result.physicalResourceId is not None: logger.debug('PhysicalResourceId: %s'
                                                                       % result.physicalResourceId)
                if not isinstance(e, InvalidResponseStatusException): logger.debug('Status: %s'
                                                                                   % result.responseStatus)
                result = ResponseObject(
                    reason='Malformed request, Exception: %s' % str(e),
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.FAILED)
                return_value = result.send(event, context)
            return return_value

        return handler_wrapper

    return inner_decorator


def rdecorator(decoratorHandleDelete: bool = False, expectedProperties: list = None, genUUID: bool = True):
    """Decorate a function to add input validation for resource handler functions.

        Usage with Lambda:
            import accustom
            @accustom.rdecorator(expectedProperties=['key1','key2'],genUUID=False)
            def resource_function(event, context):
                sum = (float(event['ResourceProperties']['key1']) +
                       float(event['ResourceProperties']['key2']))
                return { 'sum' : sum }
            @accustom.decorator()
            def function_handler(event, context)
                return resource_function(event,context)

        Usage outside Lambda:
            import accustom
            @accustom.rdecorator(expectedProperties=['key1','key2'])
            def resource_function(event, context=None)
                sum = (float(event['ResourceProperties']['key1']) +
                       float(event['ResourceProperties']['key2']))
                r = accustom.ResponseObject(data={'sum':sum},physicalResourceId=event['PhysicalResourceId'])
                return r
            @accustom.decorator()
            def function_handler(event)
                return resource_function(event)

        Args:
            decoratorHandleDelete (boolean): When set to true, if a delete request is made in event the decorator will
                return a ResponseObject with a with SUCCESS without actually executing the decorated function
            genUUID (boolean): When set to true, if the PhysicalResourceId in the event is not set, automatically
                generate a UUID4 and put it in the PhysicalResourceId field.
            expectedProperties (list of expected properties): Pass in a list or tuple of properties that you want to
                check for before running the decorated function.

        Returns:
            The result of the decorated function, or a ResponseObject with SUCCESS depending on the event and flags.

        Raises:
            NotValidRequestObjectException
            Any exception raised by the decorated function.


        Decorated Function Arguments:
            event (dict): The request object being processed (Required).
    """

    def resource_decorator_inner(func):
        @wraps(func)
        def resource_decorator_handler(event: dict, *args, **kwargs):
            if not is_valid_event(event):
                # If it is not a valid event we need to raise an exception
                message = 'The event object passed is not a valid Request Object as per ' + \
                          'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html'
                logger.error(message)
                raise NotValidRequestObjectException(message)
            logger.info('Supported resource %s' % event['ResourceType'])

            # Set the Physical Resource ID to a randomly generated UUID if it is not present
            if genUUID and 'PhysicalResourceId' not in event:
                event['PhysicalResourceId'] = str(uuid4())
                logger.info('Set PhysicalResourceId to %s' % event['PhysicalResourceId'])

            # Handle Delete when decoratorHandleDelete is set to True
            if decoratorHandleDelete and event['RequestType'] == RequestType.DELETE:
                logger.info('Request type %s detected, returning success without calling function' % RequestType.DELETE)
                return ResponseObject(physicalResourceId=event['PhysicalResourceId'])

            # Validate important properties exist
            if expectedProperties is not None and isinstance(expectedProperties, (list, tuple)):
                for index, item in enumerate(expectedProperties):
                    if item not in event['ResourceProperties']:
                        err_msg = 'Property %s missing, sending failure signal' % item
                        logger.info(err_msg)
                        return ResponseObject(reason=err_msg, responseStatus=Status.FAILED,
                                              physicalResourceId=event['PhysicalResourceId'])

            # If a list or tuple was not provided then log a warning
            elif expectedProperties is not None:
                logger.warning('expectedProperties passed to decorator is not a list, properties were not validated.')

            # Pre-validation complete, calling function
            return func(event, *args, **kwargs)

        return resource_decorator_handler

    return resource_decorator_inner


def sdecorator(decoratorHandleDelete: bool = False, expectedProperties: list = None, genUUID: bool = True,
               enforceUseOfClass: bool = False, hideResourceDeleteFailure: bool = False,
               redactConfig: RedactionConfig = None, timeoutFunction: bool = True):
    """Decorate a function to add input validation for resource handler functions, exception handling and send
    CloudFormation responses.


    Usage with Lambda:
        import accustom
        @accustom.sdecorator(expectedProperties=['key1','key2'],genUUID=False)
        def resource_handler(event, context):
            sum = (float(event['ResourceProperties']['key1']) +
                   float(event['ResourceProperties']['key2']))
            return { 'sum' : sum }

    Usage outside Lambda:
        import accustom
        @accustom.sdecorator(expectedProperties=['key1','key2'])
        def resource_handler(event, context=None)
            sum = (float(event['ResourceProperties']['key1']) +
                   float(event['ResourceProperties']['key2']))
            r = accustom.ResponseObject(data={'sum':sum},physicalResourceId=event['PhysicalResourceId'])
            return r

    Args:
        decoratorHandleDelete (boolean): When set to true, if a delete request is made in event the decorator will
            return SUCCESS to CloudFormation without actually executing the decorated function
        genUUID (boolean): When set to true, if the PhysicalResourceId in the event is not set, automatically generate
            a UUID4 and put it in the PhysicalResourceId field.
        expectedProperties (list of expected properties): Pass in a list or tuple of properties that you want to check
            for before running the decorated function.
        enforceUseOfClass (boolean): When true send a FAILED signal if a ResponseObject class is not utilised.
            This is implicitly set to true if no Lambda Context is provided.
        hideResourceDeleteFailure (boolean): When true will return SUCCESS even on getting an Exception for DELETE
            requests. Note that this particular flag is made redundant if decoratorHandleDelete is set to True.
        redactConfig (StandaloneRedactionConfig): Configuration of how to redact the event object.
        timeoutFunction (boolean): Will automatically send a failure signal to CloudFormation 1 second before Lambda
            timeout provided that this function is executed in Lambda

    Returns:
        The response object sent to CloudFormation

    Raises:
         FailedToSendResponseException
         NotValidRequestObjectException
    """
    if not isinstance(redactConfig, StandaloneRedactionConfig) and logger.getEffectiveLevel() <= logging.DEBUG:
        logger.warning('A non valid StandaloneRedactionConfig was provided, and ignored')
        redactConfig = None

    def standalone_decorator_inner(func):
        @wraps(func)
        @decorator(enforceUseOfClass=enforceUseOfClass, hideResourceDeleteFailure=hideResourceDeleteFailure,
                   redactConfig=redactConfig, timeoutFunction=timeoutFunction)
        @rdecorator(decoratorHandleDelete=decoratorHandleDelete, expectedProperties=expectedProperties, genUUID=genUUID)
        def standalone_decorator_handler(event: dict, context: dict = None):
            return func(event, context)

        return standalone_decorator_handler

    return standalone_decorator_inner
