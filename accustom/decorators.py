# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

""" Decorators for the accustom library.

This includes two decorators, one for the handler function, and one to apply to any resource handling
functions.
"""

# Exceptions
from accustom.Exceptions import FailedToSendResponseException
from accustom.Exceptions import DataIsNotDictException
from accustom.Exceptions import InvalidResponseStatusException
from accustom.Exceptions import NotValidRequestObjectException
from accustom.Exceptions import ResponseTooLongException
from accustom.Exceptions import NoPhysicalResourceIdException

# Constants
from accustom.constants import RequestType
from accustom.constants import Status

# Response
from accustom.response import is_valid_event

# RedactionConfig
from accustom.redaction import RedactionConfig
from accustom.redaction import StandaloneRedactionConfig

# Required Libraries
import logging
import json
from functools import wraps
from uuid import uuid4
from accustom.response import ResponseObject
import six
from boto3 import client
from botocore.client import Config
from botocore import exceptions as boto_exceptions
from typing import Callable, TypeVar, Any, Union
from typing_extensions import ParamSpec

logger = logging.getLogger(__name__)

# Import Requests
try:
    import requests
except ImportError:
    from botocore.vendored import requests
    logger.warning("botocore.vendored version of requests is deprecated. Please include requests in your code bundle.")

_T = TypeVar('_T')
_P = ParamSpec('_P')

# Time in milliseconds to set the alarm for (in milliseconds)
# Should be set to twice the worst case response time to send to S3
# Setting to 2 seconds for safety
TIMEOUT_THRESHOLD = 2000


def decorator(enforceUseOfClass: bool = False, hideResourceDeleteFailure: bool = False,
              redactConfig: RedactionConfig = None, timeoutFunction: bool = False) -> Callable[_P, _T]:
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

    def inner_decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        @wraps(func)
        def handler_wrapper(event: dict, context: Any, *args, **kwargs) -> Union[dict, str]:
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
                logger.info(
                    f'This request has been invoked as a child, for parent logs please see request ID: '
                    f'{event["LambdaParentRequestId"]}'
                    )
            elif context is None and timeoutFunction:
                logger.warning(
                    'You cannot use the timeoutFunction option outside of Lambda. To suppress this warning' +
                    ', set timeoutFunction to False'
                    )
            elif timeoutFunction:
                # Attempt to invoke the function. Depending on the error we get may continue execution or return
                logger.info('Request has been invoked in Lambda with timeoutFunction set, attempting to invoke self')
                p_event = event.copy()
                p_event['LambdaParentRequestId'] = context.aws_request_id
                payload = json.dumps(p_event).encode('UTF-8')
                timeout = (context.get_remaining_time_in_millis() - TIMEOUT_THRESHOLD) / 1000
                # Edge case where time is set to very low timeout, use half the timeout threshold as the timeout for
                # the Lambda Function
                if timeout <= 0: timeout = TIMEOUT_THRESHOLD / 2000
                config = Config(connect_timeout=2, read_timeout=timeout, retries={'max_attempts': 0})
                b_lambda = client('lambda', config=config)

                # Normally we would just do a catch-all error handler but in this case we want to be paranoid
                try:
                    response = b_lambda.invoke(
                        FunctionName=context.invoked_function_arn,
                        InvocationType='RequestResponse', Payload=payload
                        )
                    # Further checks
                    if 'FunctionError' in response:
                        response.get('Payload', ''.encode('UTF-8'))
                        message = f'Invocation got an error: {payload.decode()}'
                        logger.error(message)
                        return ResponseObject(reason=message, responseStatus=Status.FAILED).send(event, context)
                    else:
                        # In this case the function returned without error which means we can assume the chained
                        # invocation sent a response, so we do not have too.
                        logger.info('Completed execution of chained invocation, returning payload')
                        response.get('Payload', ''.encode('UTF-8'))
                        return payload.decode()

                except boto_exceptions.ClientError as e:
                    logger.warning(
                        f'Caught exception {str(e)} while trying to invoke function. Running handler locally.'
                        )
                    logger.warning(
                        'You cannot use the timeoutFunction option without the ability for the function to' +
                        ' invoke itself. To suppress this warning, set timeoutFunction to False'
                        )
                except boto_exceptions.ConnectionError as e:
                    logger.error(f'Got error {str(e)} while trying to invoke function. Running handler locally')
                    logger.error(
                        'You cannot use the timeoutFunction option without the ability to connect to the ' +
                        'Lambda API from within the function. As we may not have time to execute the ' +
                        'function, returning failure.'
                        )
                    return ResponseObject(
                        reason='Unable to call Lambda to do chained invoke, returning failure.',
                        responseStatus=Status.FAILED
                        ).send(event, context)
                except boto_exceptions.ReadTimeoutError:
                    # This should be a critical failure
                    logger.error('Waited the read timeout and function did not return, returning an error')
                    return ResponseObject(
                        reason='Lambda function timed out, returning failure.',
                        responseStatus=Status.FAILED
                        ).send(event, context)
                except Exception as e:
                    message = f'Got an {e.__class__} I did not understand while trying to invoke child function: ' \
                              f'{str(e)}'
                    logger.error(message)
                    return ResponseObject(reason=message, responseStatus=Status.FAILED).send(event, context)

            # Debug Logging Handler
            if logger.getEffectiveLevel() <= logging.DEBUG:
                if context is not None:
                    logger.debug(f'Running request with Lambda RequestId: {context.aws_request_id}')
                if redactConfig is not None and isinstance(redactConfig, (StandaloneRedactionConfig, RedactionConfig)):
                    # noinspection PyProtectedMember
                    logger.debug('Request Body:\n' + json.dumps(redactConfig._redact(event)))
                elif redactConfig is not None:
                    logger.warning('A non valid RedactionConfig was provided, and ignored')
                    logger.debug('Request Body:\n' + json.dumps(event))
                else:
                    logger.debug('Request Body:\n' + json.dumps(event))

            try:
                logger.info(f'Running CloudFormation request {event["RequestId"]} for stack: {event["StackId"]}')
                # Run the function
                result = func(event, context, *args, **kwargs)

            except Exception as e:
                # If there was an exception thrown by the function, send a failure response
                result = ResponseObject(
                    physicalResourceId=str(uuid4()) if context is None else None,
                    reason=f'Function {func.__name__} failed due to exception "{str(e)}"',
                    responseStatus=Status.FAILED
                    )
                logger.error(result.reason)

            if not isinstance(result, ResponseObject):
                # If a ResponseObject is not provided, work out what kind of response object to pass, or return a
                # failure if it is an invalid response type, or if the enforceUseOfClass is explicitly or implicitly set
                if context is None:
                    result = ResponseObject(
                        reason=f'Response Object of type {result.__class__} was not a ResponseObject and there is no '
                               f'Lambda Context',
                        responseStatus=Status.FAILED
                        )
                    logger.error(result.reason)
                elif enforceUseOfClass:
                    result = ResponseObject(
                        reason=f'Response Object of type {result.__class__} was not a ResponseObject instance and '
                               f'enforceUseOfClass set to true',
                        responseStatus=Status.FAILED
                        )
                    logger.error(result.reason)
                elif result is False:
                    result = ResponseObject(
                        reason=f'Function {func.__name__} returned False.',
                        responseStatus=Status.FAILED
                        )
                    logger.debug(result.reason)
                elif isinstance(result, dict):
                    result = ResponseObject(data=result)
                elif isinstance(result, six.string_types):
                    result = ResponseObject(data={'Return': result})
                elif result is None or result is True:
                    result = ResponseObject()
                else:
                    result = ResponseObject(
                        reason=f'Return value from Function {func.__name__} is of unsupported type {result.__class__}',
                        responseStatus=Status.FAILED
                        )
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
                if result.reason is not None: logger.debug(f'Reason: {result.reason}')
                if result.physicalResourceId is not None: logger.debug(
                    f'PhysicalResourceId: {result.physicalResourceId}'
                    )
                result = ResponseObject(
                    reason='There may be resources created by this Custom Resource that have not been cleaned' +
                           'up despite the fact this resource is in DELETE_COMPLETE',
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.SUCCESS
                    )

            try:
                return_value = result.send(event, context)
            except NoPhysicalResourceIdException:
                message = "An unexpected error has occurred, No Physical Resource ID provided in response."
                logger.error(message)
                result = ResponseObject(
                    reason=message,
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.FAILED
                    )
                return_value = result.send(event, context)
            except InvalidResponseStatusException:
                message = f'Status provided "{result.responseStatus}" is not a valid status.'
                logger.error(message)
                result = ResponseObject(
                    reason=message,
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.FAILED
                    )
                return_value = result.send(event, context)
            except DataIsNotDictException as e:
                message = f'Malformed Data Block in Response, Exception; {str(e)}'
                logger.error(message)
                result = ResponseObject(
                    reason=message,
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.FAILED
                    )
                return_value = result.send(event, context)
            except ResponseTooLongException as e:
                message = str(e)
                logger.error(message)
                result = ResponseObject(
                    reason=message,
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.FAILED
                    )
                return_value = result.send(event, context)
            except FailedToSendResponseException as e:
                # Capturing and re-raising exception to prevent generic exception handler from kicking in
                raise e
            except Exception as e:
                # Generic error capture
                message = f'Malformed request, Exception: {str(e)}'
                logger.error(message)
                result = ResponseObject(
                    reason=message,
                    physicalResourceId=result.physicalResourceId,
                    responseStatus=Status.FAILED
                    )
                return_value = result.send(event, context)
            return return_value

        return handler_wrapper

    return inner_decorator


def rdecorator(decoratorHandleDelete: bool = False,
               expectedProperties: list = None,
               genUUID: bool = True) -> Callable[_P, _T]:
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

    def resource_decorator_inner(func: Callable[_P, _T]) -> Callable[_P, _T]:
        @wraps(func)
        def resource_decorator_handler(event: dict, *args, **kwargs) -> Union[ResponseObject, dict, str]:
            if not is_valid_event(event):
                # If it is not a valid event we need to raise an exception
                message = 'The event object passed is not a valid Request Object as per ' + \
                          'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html'
                logger.error(message)
                raise NotValidRequestObjectException(message)
            logger.info(f'Supported resource {event["ResourceType"]}')

            # Set the Physical Resource ID to a randomly generated UUID if it is not present
            if genUUID and 'PhysicalResourceId' not in event:
                event['PhysicalResourceId'] = str(uuid4())
                logger.info(f'Set PhysicalResourceId to {event["PhysicalResourceId"]}')

            # Handle Delete when decoratorHandleDelete is set to True
            if decoratorHandleDelete and event['RequestType'] == RequestType.DELETE:
                logger.info(f'Request type {RequestType.DELETE} detected, returning success without calling function')
                return ResponseObject(physicalResourceId=event['PhysicalResourceId'])

            # Validate important properties exist
            if expectedProperties is not None and isinstance(expectedProperties, (list, tuple)):
                for index, item in enumerate(expectedProperties):
                    if item not in event['ResourceProperties']:
                        err_msg = f'Property {item} missing, sending failure signal'
                        logger.info(err_msg)
                        return ResponseObject(
                            reason=err_msg, responseStatus=Status.FAILED,
                            physicalResourceId=event['PhysicalResourceId']
                            )

            # If a list or tuple was not provided then log a warning
            elif expectedProperties is not None:
                logger.warning('expectedProperties passed to decorator is not a list, properties were not validated.')

            # Pre-validation complete, calling function
            return func(event, *args, **kwargs)

        return resource_decorator_handler

    return resource_decorator_inner


def sdecorator(decoratorHandleDelete: bool = False, expectedProperties: list = None, genUUID: bool = True,
               enforceUseOfClass: bool = False, hideResourceDeleteFailure: bool = False,
               redactConfig: RedactionConfig = None, timeoutFunction: bool = True) -> Callable[_P, _T]:
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
    if redactConfig is not None and not isinstance(redactConfig, StandaloneRedactionConfig) and \
            logger.getEffectiveLevel() <= logging.DEBUG:
        logger.warning('A non valid StandaloneRedactionConfig was provided, and ignored')
        redactConfig = None

    def standalone_decorator_inner(func: Callable[_P, _T]) -> Callable[_P, _T]:
        @wraps(func)
        @decorator(
            enforceUseOfClass=enforceUseOfClass, hideResourceDeleteFailure=hideResourceDeleteFailure,
            redactConfig=redactConfig, timeoutFunction=timeoutFunction
            )
        @rdecorator(decoratorHandleDelete=decoratorHandleDelete, expectedProperties=expectedProperties, genUUID=genUUID)
        def standalone_decorator_handler(event: dict, context: Any, *args, **kwargs) -> Union[dict, str]:
            return func(event, context, *args, **kwargs)

        return standalone_decorator_handler

    return standalone_decorator_inner
