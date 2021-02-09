""" ResponseObject and cfnresponse function for the accustom library

This allows you to communicate with CloudFormation

"""

# Exceptions
from .Exceptions import DataIsNotDictException
from .Exceptions import NoPhysicalResourceIdException
from .Exceptions import InvalidResponseStatusException
from .Exceptions import FailedToSendResponseException
from .Exceptions import NotValidRequestObjectException

# Constants
from .constants import Status
from .constants import RequestType

# Required Libraries
import json
import logging
import sys
import six
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

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
    if not (all(v in event for v in (
        'RequestType',
        'ResponseURL',
        'StackId',
        'RequestId',
        'ResourceType',
        'LogicalResourceId'
    ))):
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

    """
    if not is_valid_event(event):
        # If it is not a valid event we need to raise an exception
        message = 'The event object passed is not a valid Request Object as per ' + \
                  'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html'
        logger.error(message)
        raise NotValidRequestObjectException(message)

    if physicalResourceId is None and context is None and 'PhysicalResourceId' not in event:
        raise NoPhysicalResourceIdException("Both physicalResourceId and context are None, and there is no" +
                                            "physicalResourceId in the event")

    if responseStatus != Status.FAILED and responseStatus != Status.SUCCESS:
        raise InvalidResponseStatusException("%s is not a valid status" % responseStatus)

    if responseData is not None and not isinstance(responseData, dict):
        raise DataIsNotDictException("Data provided was not a dictionary")

    if responseStatus == Status.FAILED:
        if responseReason is not None and responseData is not None and 'ExceptionThrown' in responseData:
            responseReason = "There was an exception thrown in execution of '%s'" % responseData['ExceptionThrown']
        elif responseReason is None:
            responseReason = 'Unknown failure occurred'

        if context is not None:
            responseReason = "%s -- See the details in CloudWatch Log Stream: %s" % (responseReason,
                                                                                     context.log_stream_name)

    elif context is not None and responseReason is None:
            responseReason = "See the details in CloudWatch Log Stream: %s" % context.log_stream_name

    responseUrl = event['ResponseURL']

    if physicalResourceId is None and 'PhysicalResourceId' in event: physicalResourceId = event['PhysicalResourceId']

    responseBody = {'Status': responseStatus}
    if responseReason is not None: responseBody['Reason'] = responseReason
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    if responseData is not None: responseBody['Data'] = responseData 
    if squashPrintResponse: responseBody['NoEcho'] = 'true'

    json_responseBody = json.dumps(responseBody)

    logger.info("Sending response to pre-signed URL.")
    logger.debug("URL: %s" % responseUrl)
    if not squashPrintResponse: logger.debug("Response body:\n" + json_responseBody)

    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    # Flush the buffers to attempt to prevent log truncations when resource is deleted
    # by stack in next action
    sys.stdout.flush()
    # Flush stdout buffer
    sys.stderr.flush()
    # Flush stderr buffer

    try:
        response = requests.put(responseUrl, data=json_responseBody, headers=headers)
        if response.status_code != 200:
            # Exceptions will only be thrown on timeout or other errors, in order to catch an invalid
            # status code like 403 we will need to explicitly check the status code. In normal operation
            # we should get a "200 OK" response to our PUT.
            message = "Unable to send response to URL, status code received: %d %s" % (response.status_code,
                                                                                       response.reason)
            logger.error(message)
            raise FailedToSendResponseException(message)
        logger.debug("Response status code: %d %s" % (response.status_code, response.reason))

    except FailedToSendResponseException as e:
        # Want to explicitly catch this exception we just raised in order to raise it unmodified
        raise e

    except Exception as e:
        logger.error('Unable to send response to URL, reason given: %s' % str(e))
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
        """
        return cfnresponse(event, self.responseStatus, self.reason, self.data, self.physicalResourceId, context,
                           self.squashPrintResponse)

    def __str__(self):
        return 'Response(Status=%s)' % self.responseStatus

    def __repr__(self):
        return str(self)
