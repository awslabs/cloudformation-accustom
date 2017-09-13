""" ResponseObject and cfnresponse function for the accustom library

This allows you to communicate with CloudFormation

"""

# Exceptions
from .Exceptions import DataIsNotDictException
from .Exceptions import NoPhysicalResourceIdException
from .Exceptions import InvalidResponseStatusException
from .Exceptions import FailedToSendResponseException

# Constants
from .constants import Status

# Required Libraries
import json
import logging
import sys
from botocore.vendored import requests

logger = logging.getLogger(__name__)

def cfnresponse(event, responseStatus, responseReason=None, responseData=None, physicalResourceId=None, lambdaContext=None):
    """Format and send CloudFormation Custom Resource Objects

    This section is derived off the cfnresponse source code provided by Amazon:

    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-lambda-function-code.html

    Creates a JSON payload that is sent back to the ResponseURL (pre-signed S3 URL).

    Args:
        event: A dict containing CloudFormation custom resource request field
        responseStatus: Should have the value of 'SUCCESS' or 'FAILED'
        resonseData: The response data to be passed to CloudFormation. If it contains ExceptionThrown 
            on FAILED this is given as reason overriding responseReason.
        responseReason: The reason for this result.
        physicalResourceId: The PhysicalResourceID to be sent back to CloudFormation
        lambdaConext: Can be used in lieu of a PhysicalResourceId to use the Lambda Context to derive an ID.

        Note that either physicalResourceId or lambdaContext must be defined, and physicalResourceId supersedes
        lambdaContext

    Returns:
        Dictionary of Response Sent

    Raises:
        NoPhysicalResourceIdException
        InvalidResponseStatusException
        DataIsNotDictException
        FailedToSendResponseException

    """
    if physicalResourceId is None and lambdaContext is None and not 'PhysicalResourceId' in event:
        raise NoPhysicalResourceIdException("Both physicalResourceId and lambdaContext are None, and there is no physicalResourceId in the event")

    if responseStatus != Status.FAILED and responseStatus != Status.SUCCESS:
        raise InvalidResponseStatusException("%s is not a valid status" % responseStatus)

    if responseData is not None and not isinstance(responseData, dict):
        raise DataIsNotDictException("Data provided was not a dictionary")

    if (responseStatus == Status.FAILED):
        if responseReason is not None and responseData is not None and 'ExceptionThrown' in responseData:
            responseReason = "There was an exception thrown in execution of '%s'" % responseData['ExceptionThrown']
        elif responseReason is None:
            responseReason = 'Unknown failure occurred'

        if lambdaContext is not None:
            responseReason = "%s -- See the details in CloudWatch Log Stream: %s" % (responseReason, lambdaContext.log_stream_name)

    elif lambdaContext is not None and responseReason is None:
            responseReason = "See the details in CloudWatch Log Stream: %s" % lambdaContext.log_stream_name 

    responseUrl = event['ResponseURL']

    if physicalResourceId is None and 'PhysicalResourceId' in event: physicalResourceId = event['PhysicalResourceId']

    responseBody = {}
    responseBody['Status'] = responseStatus
    if responseReason is not None: responseBody['Reason'] = responseReason
    responseBody['PhysicalResourceId'] = physicalResourceId or lambdaContext.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['Data'] = responseData if responseData is not None else {'Placeholder':'No data provided'}

    json_responseBody = json.dumps(responseBody)

    logger.info("Sending response to URL: %s" % responseUrl)
    logger.debug("Response body:\n" + json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody)) 
    }


    # Flush the buffers to attempt tp prevent log truncations when resource is deleted
    # by stack in next action
    sys.stdout.flush() # Flush stdout buffer
    sys.stderr.flush() # Flush stderr buffer

    try:
        response = requests.put(responseUrl, data=json_responseBody, headers=headers)
        logger.debug("Reponse status code: %s" % response.reason)

    except Exception as e:
        logger.error('Unable to send response to URL, reason given: %s' % str(e))
        raise FailedToSendResponseException(str(e))

    return responseBody

class ResponseObject(object):
    """Class that allows you to init a ResponseObject for easy function writing"""
    def __init__(self,data=None,physicalResourceId=None,reason=None,responseStatus=Status.SUCCESS):
        """Init function for the class

        Args:
            data: data to be passed in the response. Must be a dict if used
            physicalResourceId: Physical resource ID to be used in the response
            reason: Reason to pass back to CloudFormation in the response Object
            responseStatus: response Status to use in the response Object, defaults to SUCCESS

        Raises:
            DataIsNotDictException

        """
        if data is not None and not isinstance(data, dict):
            raise DataIsNotDictException("Data provided was not a dictionary")

        self.data = data
        self.physicalResourceId = physicalResourceId
        self.reason = reason
        self.responseStatus = responseStatus

    def send(self, event, lambdaContext=None):
        """Send this CloudFormation Custom Resource Object

        Creates a JSON payload that is sent back to the ResponseURL (pre-signed S3 URL) based upon this response object using
        the cfnresponse function.

        Args:
            event: A dict containing CloudFormation custom resource request field
            lambdaConext: Can be used in lieu of a PhysicalResourceId to use the Lambda Context to derive an ID.


            Note that either physicalResourceId in the object or lambdaContext must be defined, and physicalResourceId supersedes
            lambdaContext

        Returns:
            Dictionary of Response Sent

        Raises:
            NoPhysicalResourceIdException
            InvalidResponseStatusException
            DataIsNotDictException
            FailedToSendResponseException
        """
        return cfnresponse(event, self.responseStatus, self.reason, self.data, self.physicalResourceId, lambdaContext)

    def __str__(self):
        return 'Response(Status=%s)' % self.responseStatus

    def __repr__(self):
        return str(self)
