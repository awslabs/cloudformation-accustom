# CloudFormation Accustom
CloudFormation Accustom is a library for responding to Custom Resources in AWS CloudFormation using the decorator
pattern.

This library provides a cfnresponse method, some helper static classes, and some decorator methods to help with the
function.

## Installation

CloudFormation Accustom can be found under PyPI at
[https://pypi.python.org/pypi/accustom](https://pypi.python.org/pypi/accustom).

To install:

```bash
python3 -m pip install accustom
```

To create a Lambda Code Bundle in Zip Format with CloudFormation Accustom and dependencies (including `requests`), 
create a directory with only your code in it and run the following. Alternatively you can create a Lambda Layer with
CloudFormation Accustom and dependencies installed and use that as your base layer for custom resources.  

```bash
python3 -m pip install accustom -t .
zip code.zip * -r 
```

## Quickstart

The quickest way to use this library is to use the standalone decorator `@accustom.sdecorator`, in a Lambda function.

```python
import accustom
@accustom.sdecorator(expectedProperties=['key1','key2'])
def resource_handler(event, context):
     result = (float(event['ResourceProperties']['key1']) +
            float(event['ResourceProperties']['key2']))
     return { 'sum' : result }
```

In this configuration, the decorator will check to make sure the properties `key1` and `key2` have been passed by the
user, and automatically send a response back to CloudFormation based upon the `event` object.

As you can see, this greatly simplifies the developer effort required to get a working custom resource that will
correctly respond to CloudFormation Custom Resource Requests.

## The Decorator Patterns

The most important part of this library are the Decorator patterns. These provide Python decorators that can be put 
around handler functions, or resource specific functions, that prepare the data for ease of usage. These decorators will
also handle exceptions for you.

### `@accustom.decorator()`

This is the primary decorator in the library. The purpose of this decorator is to take the return value of the handler
function, and respond back to CloudFormation based upon the input `event` automatically.

It takes the following options:

- `enforceUseOfClass` (Boolean) : When this is set to `True`, you must use a `ResponseObject`. This is implicitly set
  to true if no Lambda Context is provided.
- `hideResourceDeleteFailure` (Boolean) : When this is set to `True` the function will return `SUCCESS` even on getting
  an Exception for `Delete` requests.
- `redactConfig` (accustom.RedactionConfig) : For more details on how this works please see "Redacting Confidential
  Information From Logs"
- `timeoutFunction` (Boolean): Will automatically send a failure signal to CloudFormation before Lambda timeout
  provided that this function is executed in Lambda.

Without a `ResponseObject` the decorator will make the following assumptions:
- if a Lambda Context is not passed, the function will return `FAILED` 
- if a dictionary is passed back, this will be used for the Data to be returned to CloudFormation and the function will 
  return `SUCCESS`.
- if a string is passed back, this will be put in the return attribute `Return` and the function will return `SUCCESS`.
- if `None` or `True` is passed back, the function will return `SUCCESS`
- if `False` is passed back, the function will return `FAILED`

### `@accustom.rdecorator()`

This decorator, known as the "Resource Decorator" is used when you break the function into different resources, e.g. 
by making a decision based upon which `ResourceType` was passed to the handler and calling a function related to that
resource.

It takes the following option:
- `decoratorHandleDelete` (Boolean) : When set to `True`, if a `Delete` request is made in `event` the decorator will
  return a `ResponseObject` with a with `SUCCESS` without actually executing the decorated function.
- `genUUID` (Boolean) : When set to `True`, if the `PhysicalResourceId` in the `event` is not set, automatically
  generate a UUID4 and put it in the `PhysicalResoruceId` field.
- `expectedProperties` (Array or Tuple) : Pass in a list or tuple of properties that you want to check for before
  running the decorated function. If any are missing, return `FAILED`.

The most useful of these options is `expectedProperties`. With it is possible to quickly define mandatory properties
for your resource and fail if they are not included.

### `@accustom.sdecorator()`
This decorator is just a combination of `@accustom.decorator()` and `@accustom.rdecorator()`. This allows you to have a
single, stand-alone resource handler that has some defined properties and can automatically handle delete. The options
available to it is the combination of both of the options available to the other two Decorators, except for
`redactProperties` which takes an accustom.StandaloneRedactionConfig object instead of an accustom.RedactionConfig 
object. For more information on `redactProperties` see "Redacting Confidential Information From Logs".

The other important note about combining these two decorators is that `hideResourceDeleteFailure` becomes redundant if
`decoratorHandleDelete` is set to `True`.

## Response Function and Object
The `cfnresponse()` function and the `ResponseObject` are convenience function for interacting with CloudFormation.

### `cfnresponse()`
`cfnresponse()` is a traditional function. At the very minimum it needs to take in the `event` and a status, `SUCCESS`
or `FAILED`. In practice this function will likely not be used very often outside the library, but it is included for
completeness. For more details look directly at the source code for this function.

### `ResponseObject`
The `ResponseObject` allows you to define a message to be sent to CloudFormation. It only has one method, `send()`, 
which uses the `cfnresponse()` function under the hood to fire the event. A response object can be initialised and
fired with:

```python
import accustom

def handler(event, context):
    r = accustom.ResponseObject()
    r.send(event)
```

If you are using the decorator pattern it is strongly recommended that you do not invoke the `send()` method, and
instead allow the decorator to process the sending of the events for you by returning from your function.

To construct a response object you can provide the following optional parameters:

- `data` (Dictionary) : data to be passed in the response. Must be a dict if used
- `physicalResourceId` (String) : Physical resource ID to be used in the response
- `reason` (String) : Reason to pass back to CloudFormation in the response Object
- `responseStatus` (accustom.Status): response Status to use in the response Object, defaults to `SUCCESS`
- `squashPrintResponse` (Boolean) : In `DEBUG` logging the function will often print out the `Data` section of the
  response. If the `Data` contains confidential information you'll want to squash this output. This option, when set to
  `True`, will squash the output.

## Logging Recommendations
The decorators utilise the [logging](https://docs.python.org/3/library/logging.html) library for logging. It is strongly
recommended that your function does the same, and sets the logging level to at least `INFO`. Ensure the log level is set
_before_ importing Accustom.

```python
import logging
logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)
import accustom
```

## Redacting Confidential Information From `DEBUG` Logs
If you often pass confidential information like passwords and secrets in properties to Custom Resources, you may want to
prevent certain properties from being printed to debug logs. To help with this we provide a functionality to either 
blocklist or allowlist Resource Properties based upon provided regular expressions.

To utilise this functionality you must initialise and include a `RedactionConfig`. A `RedactionConfig` consists of some
flags to define the redaction mode and if the response URL should be redacted, as well as a series of `RedactionRuleSet`
objects that define what to redact based upon regular expressions. There is a special case of `RedactionConfig` called a
`StandaloneRedactionConfig` that has one, and only one, `RedactionRuleSet` that is provided at initialisation.

Each `RedactionRuleSet` defines a single regex that defines which ResourceTypes this rule set should be applied too. You
can then apply any number of rules, based upon an explicit property name, or a regex. Please see the definitions, and an
example below.

### `RedactionRuleSet`
The `RedactionRuleSet` object allows you to define a series of properties or regexes which to allowlist or blocklist for
a given resource type regex. It is initialised with the following:

- `resourceRegex` (String) : The regex used to work out what resources to apply this too.

#### `add_property_regex(propertiesRegex)`

- `propertiesRegex` (String) : The regex used to work out what properties to allowlist/blocklist

#### `add_property(propertyName)`

- `propertyName` (String) : The name of the property to allowlist/blocklist


### `RedactionConfig`
The `RedactionConfig` object allows you to create a collection of `RedactionRuleSet` objects as well as define what mode
(allowlist/blocklist) to use, and if the presigned URL provided by CloudFormation should be redacted from the logs.

- `redactMode` (accustom.RedactMode) : What redaction mode should be used, if it should be a blocklist or allowlist
- `redactResponseURL` (Boolean) : If the response URL should be not be logged.

#### `add_rule_set(ruleSet)`

- `ruleSet` (accustom.RedactionRuleSet) : The rule set to be added to the RedactionConfig

### `StandaloneRedactionConfig`
The `StandaloneRedactionConfig` object allows you to apply a single `RedactionRuleSet` object as well as define what
mode (allowlist/blocklist) to use, and if the presigned URL provided by CloudFormation should be redacted from the logs.

- `redactMode` (accustom.RedactMode) : What redaction mode should be used, if it should be a blocklist or allowlist
- `redactResponseURL` (Boolean) : If the response URL should be not be logged.
- `ruleSet` (accustom.RedactionRuleSet) : The rule set to be added to the RedactionConfig

### Example of Redaction

The below example takes in two rule sets. The first ruleset applies to all resources types, and the second ruleset
applies only to the `Custom::Test` resource type.

All resources will have properties called `Test` and `Example` redacted and replaced with `[REDATED]`. The
`Custom::Test` resource will also additionally redact properties called `Custom` and those that *start with* `DeleteMe`.

Finally, as `redactResponseURL` is set to `True`, the response URL will not be printed in the debug logs.
   
```python3
from accustom import RedactionRuleSet, RedactionConfig, decorator

ruleSetDefault = RedactionRuleSet()
ruleSetDefault.add_property_regex('^Test$')
ruleSetDefault.add_property('Example')

ruleSetCustom = RedactionRuleSet('^Custom::Test$')
ruleSetCustom.add_property('Custom')
ruleSetCustom.add_property_regex('^DeleteMe.*$')
    
rc = RedactionConfig(redactResponseURL=True)
rc.add_rule_set(ruleSetDefault)
rc.add_rule_set(ruleSetCustom)
    
@decorator(redactConfig=rc)
def resource_handler(event, context):
    result = (float(event['ResourceProperties']['Test']) +
           float(event['ResourceProperties']['Example']))
    return { 'sum' : result }
```

## Note on Timeouts and Permissions
The timeout is implemented using a *synchronous chained invocation* of your Lambda function. For this reason, please be
aware of the following limitations:

- The function must have access to the Lambda API Endpoints in order to self invoke.
- The function must have permission to self invoke (i.e. lambda:InvokeFunction permission).

If your requirements violate any of these conditions, set the `timeoutFunction` option to `False`. Please also note that
this will *double* the invocations per request, so if you're not in the free tier for Lambda make sure you are aware of
this as it may increase costs.

## Constants
We provide three constants for ease of use:

- Static value : how to access

### `Status`
- `SUCCESS` : `accustom.Status.SUCCESS`
- `FAILED` : `accustom.Status.FAILED`

### `RequestType`
- `Create` : `accustom.RequestType.CREATE`
- `Update` : `accustom.RequestType.UPDATE`
- `Delete` : `accustom.RequestType.DELETE`

### `RedactMode`

- Blocklisting : `accustom.RedactMode.BLOCKLIST`
- Allowlisting : `accustom.RedactMode.ALLOWLIST`

## How to Contribute
Feel free to open issues, fork, or submit a pull request:

- Issue Tracker: [https://github.com/awslabs/cloudformation-accustom/issues](https://github.com/awslabs/cloudformation-accustom/issues)
- Source Code: [https://github.com/awslabs/cloudformation-accustom](https://github.com/awslabs/cloudformation-accustom)
