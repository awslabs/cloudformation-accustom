""" RedactionConfig and StandaloneRedactConfig for the accustom library

This allows you to define a redaction policy for accustom
"""

from .constants import RedactMode
from .Exceptions import ConflictingValue

import logging
import exceptions
import six

logger = logging.getLogger(__name__)

# TODO: Add function details in """ syntax

class RedactionRuleSet(object):
    def __init__(self,resourceRegex='^.*$'):
        if not isinstance(resourceRegex,six.string_types):
            raise exceptions.TypeError('resourceRegex must be a string')

        self.resource=resourceRegex
        self._properties =[]

    def addPropertyRegex(self,propertiesRegex):
        if not isinstance(propertiesRegex,six.string_types):
            raise exceptions.TypeError('propertiesRegex must be a string')
        self._properties.append(propertiesRegex)

    def addProperty(self,propertyName):
        if not isinstance(propertyName,six.string_types):
            raise exceptions.TypeError('propertyName must be a string')
        self._properties.append('^' + propertyName + '$')

class RedactionConfig(object):
    """Class that allows you define a redaction policy for accustom"""
    def __init__(self,redactMode=RedactMode.BLACKLIST,redactResponseURL=False):
        """Init function for the class

        Args:
            redactMode (RedactMode.BLACKLIST or RedactMode.WHITELIST): Determine if we should whitelist or blacklist resources, defaults to
            blacklist
        redactResponseURL (boolean): Prevents the pre-signed URL from being printed preventing out of band responses (recommended for
            production)

        Raises:
            TypeError

        """
        if redactMode != RedactMode.BLACKLIST or redactMode != RedactMode.WHITELIST:
            raise exceptions.TypeError('Invalid Redaction Type')

        if not isinstance(redactResponseURL,bool):
            raise exceptions.TypeError('redactResponseURL must be of boolean type')

        self.redactMode=redactMode
        self.redactResponseURL=redactResponseURL
        self._redactProperties={}

    def __str__(self):
        return 'RedactionConfg(%s)' % self.redactMode

    def __repr__(self):
        return str(self)

    def addRuleSet(self,ruleSet):
        if not isintance(ruleSet,RedactionRuleSet):
            raise exceptions.TypeError('Please use RedactionRuleSet class')
        if ruleSet.resourceRegex in self._redactProperties:
            raise ConflictingValue('There is already a record set for resource of regex: %s' % ruleSet.resourceRegex)

        self._redactProperties[ruleSet.resourceRegex] = ruleSet._properties

    def _redact(self,event):
        ec = event.copy()
        if self.redactMode == RedactMode.BLACKLIST:
            if 'ResourceProperties' in ec: ec['ResourceProperties'] = ec['ResourceProperties'].copy()
            if 'OldResourceProperties' in ec: ec['OldResourceProperties'] = ec['OldResourceProperties'].copy()
        elif self.redactMode == RedactMode.WHITELIST:
            if 'ResourceProperties' in ec: ec['ResourceProperties'] = {}
            if 'OldResourceProperties' in ec: ec['OldResourceProperties'] = {}
        for resourceRegex, propertyRegex in self._redactProperties.items():
            if re.search(resourceRegex, event['ResourceType']) is not None:
                # Go through the Properties looking to see if they're in the ResourceProperties or OldResourceProperties
                for index, item in enumerate(propertyRegex):
                    if self.redactMode == RedactMode.BLACKLIST:
                        if 'ResourceProperties' in ec and re.search(item, ec['ResourceProperties']) is not None:
                            ec['ResourceProperties'][item] = '[REDACTED]'
                        if 'OldResourceProperties' in ec and re.search(item, ec['OldResourceProperties']) is not None:
                            ec['OldResourceProperties'][item] = '[REDACTED]'
                    elif self.redactMode == RedactMode.WHITELIST:
                        if 'ResourceProperties' in ec and re.search(item, event['ResourceProperties']) is not None:
                            ec['ResourceProperties'][item] = event['ResourceProperties'][item]
                        if 'OldResourceProperties' in ec and re.search(item, event['OldResourceProperties']) is not None:
                            ec['OldResourceProperties'][item] = event['OldResourceProperties'][item]
        if self.redactMode == RedactMode.WHITELIST:
            if 'ResourceProperties' in ec:
                for key, value in event['ResourceProperties'].items():
                    if key not in ec['ResourceProperties']: ec['ResourceProperties'][key] = '[REDACTED]'
            if 'OldResourceProperties' in ec:
                for key, value in event['OldResourceProperties'].items():
                    if key not in ec['OldResourceProperties']: ec['OldResourceProperties'][key] = '[REDACTED]'

        if redactResponseURL: del ec['ResponseURL']
        return ec


class StandaloneRedactionConfig(RedactionConfig):
    def __init__(self,ruleSet,redactMode=RedactMode.BLACKLIST,redactResponseURL=False):
        RedactionConfig.__init__(self,redactMode=redactMode,redactResponseURL=redactResponseURL)
        self.addRuleSet(ruleSet)
