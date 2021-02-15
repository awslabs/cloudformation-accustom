# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

""" RedactionConfig and StandaloneRedactConfig for the accustom library

This allows you to define a redaction policy for accustom
"""

from .response import is_valid_event
from .constants import RedactMode
from .Exceptions import ConflictingValue
from .Exceptions import CannotApplyRuleToStandaloneRedactionConfig
from .Exceptions import NotValidRequestObjectException

import logging
import six
import re
import copy

logger = logging.getLogger(__name__)

_RESOURCEREGEX_DEFAULT = '^.*$'
REDACTED_STRING = '[REDACTED]'


class RedactionRuleSet(object):
    """Class that allows you to define a redaction rule set for accustom"""

    def __init__(self, resourceRegex: str = _RESOURCEREGEX_DEFAULT):
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

    def add_property_regex(self, propertiesRegex : str):
        """Allows you to add a property regex to whitelist/blacklist

        Args:
            propertiesRegex (String): The regex used to work out what properties to whitelist/blacklist

        Raises:
            TypeError

        """
        if not isinstance(propertiesRegex, six.string_types):
            raise TypeError('propertiesRegex must be a string')
        self._properties.append(propertiesRegex)

    def add_property(self, propertyName: str):
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

    def __init__(self, redactMode: str = RedactMode.BLACKLIST, redactResponseURL: bool = False):
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

    def add_rule_set(self, ruleSet: RedactionRuleSet):
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

    def _redact(self, event: dict):
        """ Internal Function. Not to be consumed outside of accustom Library.

            This function will take in an event and return the event redacted as per the redaction config.
        """
        if not is_valid_event(event):
            # If it is not a valid event we need to raise an exception
            message = 'The event object passed is not a valid Request Object as per ' + \
                      'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html'
            logger.error(message)
            raise NotValidRequestObjectException(message)
        ec = copy.deepcopy(event)
        if self.redactMode == RedactMode.WHITELIST:
            if 'ResourceProperties' in ec: ec['ResourceProperties'] = {}
            if 'OldResourceProperties' in ec: ec['OldResourceProperties'] = {}
        for resourceRegex, propertyRegex in self._redactProperties.items():
            if re.search(resourceRegex, event['ResourceType']) is not None:
                # Go through the Properties looking to see if they're in the ResourceProperties or OldResourceProperties
                for index, item in enumerate(propertyRegex):
                    r = re.compile(item)
                    if self.redactMode == RedactMode.BLACKLIST:
                        if 'ResourceProperties' in ec:
                            for mitem in filter(r.match, ec['ResourceProperties']):
                                ec['ResourceProperties'][mitem] = REDACTED_STRING
                        if 'OldResourceProperties' in ec:
                            for mitem in filter(r.match, ec['OldResourceProperties']):
                                ec['OldResourceProperties'][mitem] = REDACTED_STRING
                    elif self.redactMode == RedactMode.WHITELIST:
                        if 'ResourceProperties' in ec:
                            for mitem in filter(r.match, event['ResourceProperties']):
                                ec['ResourceProperties'][mitem] = event['ResourceProperties'][mitem]
                        if 'OldResourceProperties' in ec:
                            for mitem in filter(r.match, event['OldResourceProperties']):
                                ec['OldResourceProperties'][mitem] = event['OldResourceProperties'][mitem]
        if self.redactMode == RedactMode.WHITELIST:
            if 'ResourceProperties' in ec:
                for key, value in event['ResourceProperties'].items():
                    if key not in ec['ResourceProperties']: ec['ResourceProperties'][key] = REDACTED_STRING
            if 'OldResourceProperties' in ec:
                for key, value in event['OldResourceProperties'].items():
                    if key not in ec['OldResourceProperties']: ec['OldResourceProperties'][key] = REDACTED_STRING

        if self.redactResponseURL: del ec['ResponseURL']
        return ec

    def __str__(self):
        return 'RedactionConfig(%s)' % self.redactMode

    def __repr__(self):
        return str(self)


class StandaloneRedactionConfig(RedactionConfig):
    def __init__(self, ruleSet: RedactionRuleSet, redactMode: str = RedactMode.BLACKLIST,
                 redactResponseURL: bool = False):
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
        ruleSet.resourceRegex = _RESOURCEREGEX_DEFAULT
        # override resource regex to be default
        assert (ruleSet is not None)
        RedactionConfig.add_rule_set(self, ruleSet)

    def add_rule_set(self, ruleSet: RedactionRuleSet):
        """ Overrides the add_rule_set operation with one that will immediately throw an exception

            Raises
                CannotApplyRuleToStandaloneRedactionConfig
        """
        raise CannotApplyRuleToStandaloneRedactionConfig('StandaloneRedactionConfig does not support additional rules.')
