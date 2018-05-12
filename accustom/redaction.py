""" RedactionConfig and StandaloneRedactConfig for the accustom library

This allows you to define a redaction policy for accustom
"""

from .constants import RedactMode
from .Exceptions import ConflictingValue
from .Exceptions import CannotApplyRuleToStandaloneRedactionConfig

import logging
import six
import re

logger = logging.getLogger(__name__)

_RESOURCEREGEX_DEFAULT = '^.*$'


class RedactionRuleSet(object):
    """Class that allows you to define a redaction rule set for accustom"""
    def __init__(self, resourceRegex=_RESOURCEREGEX_DEFAULT):
        """Init function for the class

        Args:
            resourceRegex (String): The regex used to work out what resources to apply this too.

        Raises:
            TypeError

        """
        if not isinstance(resourceRegex, six.string_types):
            raise TypeError('resourceRegex must be a string')

        self.resourceRegex = resourceRegex
        self._properties = []

    def addPropertyRegex(self, propertiesRegex):
        """Allows you to add a property regex to whitelist/blacklist

        Args:
            propertiesRegex (String): The regex used to work out what properties to whitelist/blacklist

        Raises:
            TypeError

        """
        if not isinstance(propertiesRegex, six.string_types):
            raise TypeError('propertiesRegex must be a string')
        self._properties.append(propertiesRegex)

    def addProperty(self, propertyName):
        """Allows you to add a specific property to whitelist/blacklist

        Args:
            propertyName (String): The name of the property to whitelist/blacklist

        Raises:
            TypeError

        """
        if not isinstance(propertyName, six.string_types):
            raise TypeError('propertyName must be a string')
        self._properties.append('^' + propertyName + '$')


class RedactionConfig(object):
    """Class that allows you define a redaction policy for accustom"""
    def __init__(self, redactMode=RedactMode.BLACKLIST, redactResponseURL=False):
        """Init function for the class

        Args:
            redactMode (RedactMode.BLACKLIST or RedactMode.WHITELIST): Determine if we should whitelist or blacklist
            resources, defaults to blacklist
        redactResponseURL (boolean): Prevents the pre-signed URL from being printed preventing out of band responses
        (recommended for production)

        Raises:
            TypeError

        """
        if redactMode != RedactMode.BLACKLIST and redactMode != RedactMode.WHITELIST:
            raise TypeError('Invalid Redaction Type')

        if not isinstance(redactResponseURL, bool):
            raise TypeError('redactResponseURL must be of boolean type')

        self.redactMode = redactMode
        self.redactResponseURL = redactResponseURL
        self._redactProperties = {}

    def addRuleSet(self, ruleSet):
        """ This function will add a RedactionRuleSet object to the RedactionConfig.

        Args:
            ruleSet (RedactionRuleSet): The rule to be added to the RedactionConfig

        Raises:
            TypeError
            ConflictingValue

        """

        if not isinstance(ruleSet, RedactionRuleSet):
            raise TypeError('Please use RedactionRuleSet class')
        if ruleSet.resourceRegex in self._redactProperties:
            raise ConflictingValue('There is already a record set for resource of regex: %s' % ruleSet.resourceRegex)

        self._redactProperties[ruleSet.resourceRegex] = ruleSet._properties

    def _redact(self, event):
        """ Internal Function. Not to be consumed outside of accustom Library.

            This function will take in an event and return the event redacted as per the redaction config.
        """
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
                        if 'OldResourceProperties' in ec and re.search(item,
                                                                       event['OldResourceProperties']) is not None:
                            ec['OldResourceProperties'][item] = event['OldResourceProperties'][item]
        if self.redactMode == RedactMode.WHITELIST:
            if 'ResourceProperties' in ec:
                for key, value in event['ResourceProperties'].items():
                    if key not in ec['ResourceProperties']: ec['ResourceProperties'][key] = '[REDACTED]'
            if 'OldResourceProperties' in ec:
                for key, value in event['OldResourceProperties'].items():
                    if key not in ec['OldResourceProperties']: ec['OldResourceProperties'][key] = '[REDACTED]'

        if self.redactResponseURL: del ec['ResponseURL']
        return ec

    def __str__(self):
        return 'RedactionConfg(%s)' % self.redactMode

    def __repr__(self):
        return str(self)


class StandaloneRedactionConfig(RedactionConfig):
    def __init__(self, ruleSet, redactMode=RedactMode.BLACKLIST, redactResponseURL=False):
        """Init function for the class

        Args:
            redactMode (RedactMode.BLACKLIST or RedactMode.WHITELIST): Determine if we should whitelist or blacklist
            resources, defaults to blacklist
        redactResponseURL (boolean): Prevents the pre-signed URL from being printed preventing out of band responses
        (recommended for production)
        ruleSet (RedactionRuleSet): The single rule set to be applied

        Raises:
            TypeError
        """

        RedactionConfig.__init__(self, redactMode=redactMode, redactResponseURL=redactResponseURL)
        ruleSet.resourceRegex=_RESOURCEREGEX_DEFAULT
            # override resource regex to be default
        RedactionConfig.addRuleSet(ruleSet)

    def addRuleSet(self, ruleSet):
        """ Overrides the addRuleSet operation with one that will immediately throw an exception

            Raises
                CannotApplyRuleToStandaloneRedactionConfig
        """
        raise CannotApplyRuleToStandaloneRedactionConfig('StandaloneRedactionConfig does not support additional rules.')
