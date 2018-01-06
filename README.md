# accustom
Accustom is a library for responding to Custom Resources in AWS CloudFormation using the decorator pattern.

This library was written based upon the same decorator methods used by the [cfnlambda](https://github.com/gene1wood/cfnlambda) library written by Gene Wood. As that library is no longer maintained I wrote a new version.

This library provides a cfnresponse method, some helper static classes, and some decorator methods to help with the function.

## Installation

accustom can be found under PyPI at [https://pypi.python.org/pypi/accustom](https://pypi.python.org/pypi/accustom).

To install:

```bash
pip3 install accustom
```

To create a Lambda Code Zip with accustom included:

```bash
pip3 install accustom -t . --no-deps
zip code.zip function.py accustom -r 
```

## Quickstart

The quickest way to use this library is to use the standalone decorator `@accustom.sdecorator`, in a Lambda function.

    import accustom
    @accustom.sdecorator(expectedProperties=['key1','key2'])
    def resource_handler(event, context):
        sum = (float(event['ResourceProperties']['key1']) +
              float(event['ResourceProperties']['key2']))
            return { 'sum' : sum }


In this configuration, the decorator will check to make sure the properties `key1` and `key2` have been passed by the user, and automatically send a response back to CloudFormation based upon the `event` object.

As you can see, this greatly simplifies the developer effort required to get a working custom resource that will correctly respond to CloudFormation.

## The Decorator Patterns

The most important part of this library are the Decorator patterns. These provide Python decorators that can be put around handler functions, or resource specific functions, that prepare the data for ease of usage, and also handle exceptions.

### `@accustom.decorator()`

This is the primary decorator in the library. The purpose of this decorator is to take the return value of the handler function, and respond back to CloudFormation based upon the input `event` automatically.

It takes the following options:

- `enforceUseOfClass` (Boolean) : When this is set to `True`, you must use a `ResponseObject`. This is implicitly set to true if no Lambda Context is provided.
- `hideResourceDeleteFailure` (Boolean) : When this is set to `True` the function will return `SUCCESS` even on getting an Exception for `Delete` requests.
- `redactProperties` (Dictionary of Lists) : For more details on how this works please see "Redacting Confidential Information From Logs"
- `redactMode` (accustom.RedactMode) : For more details on how this works please see "Redacting Confidential Information"

Without a `ResponseObject` the decorator will make the following assumptions:
- if a Lambda Context is not passed, the function will return `FAILED` 
- if a dictionary is passed back, this will be used for the Data to be returned to CloudFormation and the function will return `SUCCESS`.
- if a string is passed back, this will be put in the return attribute `Return` and the function will return `SUCCESS`.
- if `None` or `True` is passed back, the function will return `SUCCESS`
- if `False` is passed back, the function will return `FAILED`

### `@accustom.rdecorator()`

This decorator, known as the "Resource Decorator" is used when you break the function into different resources, e.g. by making a decision based upon which `ResourceType` was passed to the handler and calling a function related to that resource.

It takes the following option:
- `decoratorHandleDelete` (Boolean) : When set to `True`, if a `Delete` request is made in `event` the decorator will return a `ResponseObject` with a with `SUCCESS` without actually executing the decorated function.
- `genUUID` (Boolean) : When set to `True`, if the `PhysicalResourceId` in the `event` is not set, automatically generate a UUID4 and put it in the `PhysicalResoruceId` field.
- `expectedProperties` (Array or Tuple) : Pass in a list or tuple of properties that you want to check for before running the decorated function. If any are missing, return `FAILED`.

The most useful of these options is `expectedProperties`. With it is possible to quickly define mandatory properties for your resource and fail if they are not included.

### `@accustom.sdecorator()`
This decorator is just a combination of `@accustom.decorator()` and `@accustom.rdecorator()`. This allows you have a single, stand alone resource handler that has some defined properties and can automatically handle delete. The options available to it is the combination of both of the options available to the other two Decorators, with the exception of `redactProperties` which takes a list instead of a dictionary. For more information on `redactProperties` see "Redacting Confidential Information From Logs".

The other important note about combining these two decorators is that `hideResourceDeleteFailure` becomes redundant if `decoratorHandleDelete` is set to `True`.

## Response Function and Object
The `cfnresponse()` function and the `ResponseObject` are convenience function for interacting with CloudFormation.

### `cfnresponse()`
`cfnresponse()` is a traditional function. At the very minimum it needs to take in the `event` and a status, `SUCCESS` or `FAILED`. In practice this function will likely not be used very often outside the library, but it is included for completeness. For more details look directly at the source code for this function.

### `ResponseObject`
The `ResponseObject` allows you to define a message to be sent to CloudFormation. It only has one method, `send()`, which uses the `cfnresponse()` function under the hood to fire the event. A response object can be initialised and fired with:

        import accustom
        r = accustom.ResponseObject()
        r.send(event)

If you are using the decorator pattern it is strongly recommended that you do not invoke the `send()` method, and instead allow the decorator to process the sending of the events for you.

To construct a response object you can provide the following optional parameters:

- `data` (Dictionary) : data to be passed in the response. Must be a dict if used
- `physicalResourceId` (String) : Physical resource ID to be used in the response
- `reason` (String) : Reason to pass back to CloudFormation in the response Object
- `responseStatus` (accustom.Status): response Status to use in the response Object, defaults to `SUCCESS`
- `squashPrintResponse` (Boolean) : In `DEBUG` logging the function will often print out the `Data` section of the response. If the `Data` contains confidential information you'll want to squash this output. This option, when set to `True`, will squash the output.

## Redacting Confidential Information From Logs
As you often pass confidential information like passwords and secrets in properties to Custom Resources, you may want to prevent certain properties from being printed to debug logs. To help with this we provide a functionality to either blacklist or whitelist Resource Properties.

<< Documentation WIP >>

## Constants
We provide there constants for ease of use:

- Static value : how to access

### `Status`
- `SUCCESS` : `accustom.Status.SUCCESS`
- `FAILED` : `accustom.Status.FAILED`

### `RequestType`
- `Create` : `accustom.RequestType.CREATE`
- `Update` : `accustom.RequestType.UPDATE`
- `Delete` : `accustom.RequestType.DELETE`

### `RedactMode`

- Blacklisting : `accustom.RedactMode.BLACKLIST`
- Whitelisting : `accustom.RedactMode.WHITELIST`

## How to Contribute
Feel free to open issues, fork, or submit a pull request:

- Issue Tracker: [https://github.com/NightKhaos/accustom/issues](https://github.com/NightKhaos/accustom/issues)
- Source Code: [https://github.com/NightKhaos/accustom](https://github.com/NightKhaos/accustom)
