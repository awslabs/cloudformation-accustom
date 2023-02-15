# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

""" ResponseObject and cfnresponse function for the accustom library

This allows you to communicate with CloudFormation

"""

# Exceptions
from accustom.Exceptions import DataIsNotDictException
from accustom.Exceptions import NoPhysicalResourceIdException
from accustom.Exceptions import InvalidResponseStatusException
from accustom.Exceptions import FailedToSendResponseException
from accustom.Exceptions import NotValidRequestObjectException
from accustom.Exceptions import ResponseTooLongException

# Constants
from accustom.constants import Status
from accustom.constants import RequestType

# Required Libraries
import json
import logging
import sys
import six
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
CUSTOM_RESOURCE_SIZE_LIMIT = 4096

# Import Requests
try:
    import requests
except ImportError:
    from botocore.vendored import requests

    logger.warning("botocore.vendored version of requests is deprecated. Please include requests in your code bundle.")


def is_valid_event(event: dict) -> bool:
    """This function takes in a CloudFormation Request Object and checks for the required fields as per:
    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html

    Args:
        event (dict): The request object being processed.

    Returns:
        bool: If the request object is a valid request object

    """
    if not (all(
            v in event for v in (
                    'RequestType',
                    'ResponseURL',
                    'StackId',
                    'RequestId',
                    'ResourceType',
                    'LogicalResourceId'
                    )
            )):
        # Check we have all the required fields
        return False

    if event['RequestType'] not in [RequestType.CREATE, RequestType.DELETE, RequestType.UPDATE]:
        # Check if the request type is a valid request type
        return False

    scheme = urlparse(event['ResponseURL']).scheme
    if scheme == '' or scheme not in ('http', 'https'):
        # Check if the URL appears to be a valid HTTP or HTTPS URL
        # Technically it should always be an HTTPS URL but hedging bets for testing to allow http
        return False

    if event['RequestType'] in [RequestType.UPDATE, RequestType.DELETE] and 'PhysicalResourceId' not in event:
        # If it is an Update or Delete request there needs to be a PhysicalResourceId key
        return False

    # All checks passed
    return True


def collapse_data(response_data: dict):
    """This function takes in a dictionary and collapses it into single object keys

    For example: it would translate something like this:

    { "Address" { "Street" : "Apple Street" }}

    Into this:

    { "Address.Street" : "Apple Street" }

    Where there is an explict instance of a dot-notated item, this will override any collapsed items

    Args:
        response_data (dict): The data object that needs to be collapsed
    Returns:
        dict: collapsed response data with higher level keys removed and replaced with dot-notation
    """

    for item in list(response_data):
        if isinstance(response_data[item], dict):
            response_data[item] = collapse_data(response_data[item])
            for c_item in response_data[item]:
                new_key = f"{item}.{c_item}"
                if new_key not in response_data:
                    # This if statement prevents overrides of existing keys
                    response_data[new_key] = response_data[item][c_item]
            del response_data[item]

    return response_data


def cfnresponse(event: dict, responseStatus: str, responseReason: str = None, responseData: dict = None,
                physicalResourceId: str = None, context: dict = None, squashPrintResponse: bool = False):
    """Format and send CloudFormation Custom Resource Objects

    This section is derived off the cfnresponse source code provided by Amazon:

    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-lambda-function-code.html

    Creates a JSON payload that is sent back to the ResponseURL (pre-signed S3 URL).

    Args:
        event: A dict containing CloudFormation custom resource request field
        responseStatus (Status.SUCCESS or Status.FAILED): Should have the value of 'SUCCESS' or 'FAILED'
        responseData (dict): The response data to be passed to CloudFormation. If it contains ExceptionThrown
            on FAILED this is given as reason overriding responseReason.
        responseReason (str): The reason for this result.
        physicalResourceId (str): The PhysicalResourceID to be sent back to CloudFormation
        context (context object): Can be used in lieu of a PhysicalResourceId to use the Lambda Context to derive
            an ID.
        squashPrintResponse (boolean): When logging set to debug and this is set to False, it will print the response
            (defaults to False). If set to True this will also send the response with NoEcho set to True.

        Note that either physicalResourceId or context must be defined, and physicalResourceId supersedes
        context

    Returns:
        Dictionary of Response Sent

    Raises:
        NoPhysicalResourceIdException
        InvalidResponseStatusException
        DataIsNotDictException
        FailedToSendResponseException
        NotValidRequestObjectException
        ResponseTooLongException

    """
    if not is_valid_event(event):
        # If it is not a valid event we need to raise an exception
        message = 'The event object passed is not a valid Request Object as per ' + \
                  'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html'
        logger.error(message)
        raise NotValidRequestObjectException(message)

    if physicalResourceId is None and context is None and 'PhysicalResourceId' not in event:
        raise NoPhysicalResourceIdException(
            "Both physicalResourceId and context are None, and there is no" +
            "physicalResourceId in the event"
            )

    if responseStatus != Status.FAILED and responseStatus != Status.SUCCESS:
        raise InvalidResponseStatusException(f"{responseStatus} is not a valid status")

    if responseData is not None and not isinstance(responseData, dict):
        raise DataIsNotDictException("Data provided was not a dictionary")

    if responseStatus == Status.FAILED:
        if responseReason is not None and responseData is not None and 'ExceptionThrown' in responseData:
            responseReason = f"There was an exception thrown in execution of '{responseData['ExceptionThrown']}'"
        elif responseReason is None:
            responseReason = 'Unknown failure occurred'

        if context is not None:
            responseReason = f"{responseReason} -- See the details in CloudWatch Log Stream: {context.log_stream_name}"

    elif context is not None and responseReason is None:
        responseReason = f"See the details in CloudWatch Log Stream: {context.log_stream_name}"

    responseUrl = event['ResponseURL']

    if physicalResourceId is None and 'PhysicalResourceId' in event: physicalResourceId = event['PhysicalResourceId']

    responseBody = {'Status': responseStatus}
    if responseReason is not None: responseBody['Reason'] = responseReason
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    if responseData is not None: responseBody['Data'] = collapse_data(responseData)
    if squashPrintResponse: responseBody['NoEcho'] = 'true'

    json_responseBody = json.dumps(responseBody)
    json_responseSize = sys.getsizeof(json_responseBody)
    logger.debug(f"Determined size of message to {json_responseSize:d}n bytes")

    if json_responseSize >= CUSTOM_RESOURCE_SIZE_LIMIT:
        raise ResponseTooLongException(
            f"Response ended up {json_responseSize:d}n bytes long which exceeds {CUSTOM_RESOURCE_SIZE_LIMIT:d}n bytes"
            )

    logger.info("Sending response to pre-signed URL.")
    logger.debug(f"URL: {responseUrl}")
    if not squashPrintResponse: logger.debug("Response body:\n" + json_responseBody)

    headers = {
        'content-type':   '',
        'content-length': str(json_responseSize)
        }

    # Flush the buffers to attempt to prevent log truncations when resource is deleted
    # by stack in next action
    sys.stdout.flush()
    # Flush stdout buffer
    sys.stderr.flush()
    # Flush stderr buffer

    try:
        response = requests.put(responseUrl, data=json_responseBody, headers=headers)
        if 'x-amz-id-2' in response.headers and 'x-amz-request-id' in response.headers:
            logger.debug("Got headers for PUT request to pre-signed URL. Printing to debug log.")
            logger.debug(f"x-amz-request-id =\n{response.headers['x-amz-request-id']}")
            logger.debug(f"x-amz-id-2 =\n{response.headers['x-amz-id-2']}")
        if response.status_code != 200:
            # Exceptions will only be thrown on timeout or other errors, in order to catch an invalid
            # status code like 403 we will need to explicitly check the status code. In normal operation
            # we should get a "200 OK" response to our PUT.
            message = f"Unable to send response to URL, status code received: {response.status_code:d} " \
                      f"{response.reason}"
            logger.error(message)
            raise FailedToSendResponseException(message)
        logger.debug(f"Response status code: {response.status_code:d} {response.reason}")

    except FailedToSendResponseException as e:
        # Want to explicitly catch this exception we just raised in order to raise it unmodified
        raise e

    except Exception as e:
        logger.error(f'Unable to send response to URL, reason given: {str(e)}')
        raise FailedToSendResponseException(str(e))

    return responseBody


class ResponseObject(object):
    """Class that allows you to init a ResponseObject for easy function writing"""

    def __init__(self, data: dict = None, physicalResourceId: str = None, reason: str = None,
                 responseStatus: str = Status.SUCCESS, squashPrintResponse: bool = False):
        """Init function for the class

        Args:
            data (dict): data to be passed in the response. Must be a dict if used
            physicalResourceId (str): Physical resource ID to be used in the response
            reason (str): Reason to pass back to CloudFormation in the response Object
            responseStatus (Status.SUCCESS or Status.FAILED): response Status to use in the response Object,
                defaults to SUCCESS
            squashPrintResponse (boolean): When logging set to debug and this is set to False, it will print the
                response (defaults to False). If set to True it will also be sent with NoEcho set to true.

        Raises:
            DataIsNotDictException
            TypeError

        """
        if data is not None and not isinstance(data, dict):
            raise DataIsNotDictException("Data provided was not a dictionary")

        if not isinstance(physicalResourceId, six.string_types) and physicalResourceId is not None:
            raise TypeError('physicalResourceId must be of type string')

        if not isinstance(reason, six.string_types) and reason is not None:
            raise TypeError('message must be of type string')

        if responseStatus != Status.SUCCESS and responseStatus != Status.FAILED:
            raise TypeError('Invalid response status')

        if not isinstance(squashPrintResponse, bool):
            raise TypeError('squashPrintResponse must be of boolean type')

        self.data = data
        self.physicalResourceId = physicalResourceId
        self.reason = reason
        self.responseStatus = responseStatus
        self.squashPrintResponse = squashPrintResponse

    def send(self, event: dict, context: dict = None):
        """Send this CloudFormation Custom Resource Object

        Creates a JSON payload that is sent back to the ResponseURL (pre-signed S3 URL) based upon this response object
        using the cfnresponse function.

        Args:
            event: A dict containing CloudFormation custom resource request field
            context: Can be used in lieu of a PhysicalResourceId to use the Lambda Context to derive an ID.

            Note that either physicalResourceId in the object or context must be defined, and physicalResourceId
            supersedes context

        Returns:
            Dictionary of Response Sent

        Raises:
            NoPhysicalResourceIdException
            InvalidResponseStatusException
            DataIsNotDictException
            FailedToSendResponseException
            NotValidRequestObjectException
            ResponseTooLongException
        """
        return cfnresponse(
            event, self.responseStatus, self.reason, self.data, self.physicalResourceId, context,
            self.squashPrintResponse
            )

    def __str__(self):
        return f'Response(Status={self.responseStatus})'

    def __repr__(self):
        return str(self)
