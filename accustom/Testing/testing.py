class TestEvent:
    Create = {
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "ResponseURL": "http://pre-signed-S3-url-for-response",
                "ResourceProperties": {
                "Content" : "test-content",
                "S3Bucket" : "cf-templates-bertiet-syd"
                },
                "RequestType": "Create",
                "ResourceType": "Custom::TestResource",
                "RequestId": "unique id for this create request",
                "LogicalResourceId": "MyTestResource"
            }
    Update =  {
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "ResponseURL": "http://pre-signed-S3-url-for-response",
                "ResourceProperties": {
                "Content" : "test-content",
                "S3Bucket" : "cf-templates-bertiet-syd"
                },
                "RequestType": "Update",
                "ResourceType": "Custom::TestResource",
                "RequestId": "unique id for this create request",
                "LogicalResourceId": "MyTestResource",
                "PhysicalResourceId" : "aabbcc"
            }
    Delete = {
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "ResponseURL": "http://pre-signed-S3-url-for-response",
                "ResourceProperties": {
                "Content" : "test-content",
                "S3Bucket" : "cf-templates-bertiet-syd"
                },
                "RequestType": "Delete",
                "ResourceType": "Custom::TestResource",
                "RequestId": "unique id for this create request",
                "LogicalResourceId": "MyTestResource",
                "PhysicalResourceId" : "aabbcc"
            }

