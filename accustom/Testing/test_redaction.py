from accustom import RedactionRuleSet
from accustom import RedactionConfig
from accustom import StandaloneRedactionConfig
from accustom import RedactMode
from accustom.Exceptions import CannotApplyRuleToStandaloneRedactionConfig

from unittest import TestCase, main as umain

REDACTED_STRING = '[REDACTED]'
NOT_REDACTED_STRING = 'NotRedacted'


class RedactionRuleSetTests(TestCase):

    def setUp(self):
        self.ruleSet = RedactionRuleSet()

    def test_init(self):
        # This test ignores the setUp resources
        rs = RedactionRuleSet('^Custom::Test$')
        self.assertEqual(rs.resourceRegex, '^Custom::Test$')

    def test_invalid_init(self):
        # This test ignores the setUp Resources
        with self.assertRaises(TypeError):
            RedactionRuleSet(0)

    def test_default_regex(self):
        self.assertEqual(self.ruleSet.resourceRegex, '^.*$')

    def test_adding_regex(self):
        self.ruleSet.add_property_regex('^Test$')
        self.assertIn('^Test$', self.ruleSet._properties)

    def test_adding_invalid_regex(self):
        with self.assertRaises(TypeError):
            self.ruleSet.add_property_regex(0)

    def test_adding_property(self):
        self.ruleSet.add_property('Test')
        self.assertIn('^Test$', self.ruleSet._properties)

    def test_adding_invalid_property(self):
        with self.assertRaises(TypeError):
            self.ruleSet.add_property(0)


class RedactionConfigTests(TestCase):

    def setUp(self):
        self.ruleSetDefault = RedactionRuleSet()
        self.ruleSetDefault.add_property_regex('^Test$')
        self.ruleSetDefault.add_property('Example')

        self.ruleSetCustom = RedactionRuleSet('^Custom::Test$')
        self.ruleSetCustom.add_property('Custom')
        self.ruleSetCustom.add_property_regex('^DeleteMe.*$')

    def test_defaults(self):
        rc = RedactionConfig()
        self.assertEqual(rc.redactMode, RedactMode.BLACKLIST)
        self.assertFalse(rc.redactResponseURL)

    def test_input_values(self):
        rc = RedactionConfig(redactMode=RedactMode.WHITELIST, redactResponseURL=True)
        self.assertEqual(rc.redactMode, RedactMode.WHITELIST)
        self.assertTrue(rc.redactResponseURL)

    def test_invalid_input_values(self):
        with self.assertRaises(TypeError):
            RedactionConfig(redactMode='somestring')
        with self.assertRaises(TypeError):
            RedactionConfig(redactMode=0)
        with self.assertRaises(TypeError):
            RedactionConfig(redactResponseURL=0)

    def test_structure(self):
        rc = RedactionConfig()
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)

        self.assertIn('^.*$', rc._redactProperties)
        self.assertIn('^Custom::Test$', rc._redactProperties)
        self.assertIn('^Test$', rc._redactProperties['^.*$'])
        self.assertIn('^Example$', rc._redactProperties['^.*$'])
        self.assertIn('^DeleteMe.*$', rc._redactProperties['^Custom::Test$'])
        self.assertIn('^Custom$', rc._redactProperties['^Custom::Test$'])

    def test_redactResponseURL(self):
        rc = RedactionConfig(redactResponseURL=True)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Test'}
        revent = rc._redact(event)

        self.assertIn('ResponseURL', event)
        self.assertNotIn('ResponseURL', revent)

    def test_blacklist1(self):
        rc = RedactionConfig(redactMode=RedactMode.BLACKLIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Test',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)

    def test_blacklist2(self):
        rc = RedactionConfig(redactMode=RedactMode.BLACKLIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Hello',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)

    def test_whitelist1(self):
        rc = RedactionConfig(redactMode=RedactMode.WHITELIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Test',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], REDACTED_STRING)

    def test_whitelist2(self):
        rc = RedactionConfig(redactMode=RedactMode.WHITELIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Hello',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], REDACTED_STRING)

    def test_oldproperties1(self):
        rc = RedactionConfig(redactMode=RedactMode.BLACKLIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event = {'RequestType' : 'Update',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'PhysicalResourceId': 'Test',
                 'ResourceType': 'Custom::Hello',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING},
                 'OldResourceProperties': {'Test': NOT_REDACTED_STRING,
                                           'Example': NOT_REDACTED_STRING,
                                           'Custom': NOT_REDACTED_STRING,
                                           'DeleteMe1': NOT_REDACTED_STRING,
                                           'DeleteMe2': NOT_REDACTED_STRING,
                                           'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)

        self.assertEqual(event['OldResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Test'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Example'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)

    def test_oldproperties2(self):
        rc = RedactionConfig(redactMode=RedactMode.WHITELIST)
        rc.add_rule_set(self.ruleSetDefault)
        rc.add_rule_set(self.ruleSetCustom)
        event = {'RequestType' : 'Update',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'PhysicalResourceId': 'Test',
                 'ResourceType': 'Custom::Hello',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING},
                 'OldResourceProperties': {'Test': NOT_REDACTED_STRING,
                                           'Example': NOT_REDACTED_STRING,
                                           'Custom': NOT_REDACTED_STRING,
                                           'DeleteMe1': NOT_REDACTED_STRING,
                                           'DeleteMe2': NOT_REDACTED_STRING,
                                           'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], REDACTED_STRING)

        self.assertEqual(event['OldResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Custom'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DeleteMe1'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DeleteMe2'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DoNotDelete'], REDACTED_STRING)


class StandaloneRedactionConfigTests(TestCase):

    def setUp(self):
        self.ruleSetDefault = RedactionRuleSet()
        self.ruleSetDefault.add_property_regex('^Test$')
        self.ruleSetDefault.add_property('Example')

        self.ruleSetCustom = RedactionRuleSet('^Custom::Test$')
        self.ruleSetCustom.add_property('Custom')
        self.ruleSetCustom.add_property_regex('^DeleteMe.*$')

    def test_defaults(self):
        rc = StandaloneRedactionConfig(self.ruleSetDefault)
        self.assertEqual(rc.redactMode, RedactMode.BLACKLIST)
        self.assertFalse(rc.redactResponseURL)

    def test_input_values(self):
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.WHITELIST, redactResponseURL=True)
        self.assertEqual(rc.redactMode, RedactMode.WHITELIST)
        self.assertTrue(rc.redactResponseURL)

    def test_invalid_input_values(self):
        with self.assertRaises(TypeError):
            StandaloneRedactionConfig(self.ruleSetDefault, redactMode='somestring')
        with self.assertRaises(TypeError):
            StandaloneRedactionConfig(self.ruleSetDefault, redactMode=0)
        with self.assertRaises(TypeError):
            StandaloneRedactionConfig(self.ruleSetDefault, redactResponseURL=0)
        with self.assertRaises(CannotApplyRuleToStandaloneRedactionConfig):
            rc = StandaloneRedactionConfig(self.ruleSetDefault)
            rc.add_rule_set(self.ruleSetCustom)

    def test_structure(self):
        rc = StandaloneRedactionConfig(self.ruleSetDefault)

        self.assertIn('^.*$', rc._redactProperties)
        self.assertIn('^Test$', rc._redactProperties['^.*$'])
        self.assertIn('^Example$', rc._redactProperties['^.*$'])

    def test_redactResponseURL(self):
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactResponseURL=True)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Test'}
        revent = rc._redact(event)

        self.assertIn('ResponseURL', event)
        self.assertNotIn('ResponseURL', revent)

    def test_blacklist(self):
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.BLACKLIST)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Test',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)

    def test_whitelist(self):
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.WHITELIST)
        event = {'RequestType' : 'Create',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'ResourceType': 'Custom::Hello',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], REDACTED_STRING)

    def test_oldproperties(self):
        rc = StandaloneRedactionConfig(self.ruleSetDefault, redactMode=RedactMode.WHITELIST)
        event = {'RequestType' : 'Update',
                 'RequestId' : 'abcded',
                 'ResponseURL' : 'https://localhost',
                 'StackId': 'arn:...',
                 'LogicalResourceId': 'Test',
                 'PhysicalResourceId' : 'Test',
                 'ResourceType': 'Custom::Hello',
                 'ResourceProperties': {'Test': NOT_REDACTED_STRING,
                                        'Example': NOT_REDACTED_STRING,
                                        'Custom': NOT_REDACTED_STRING,
                                        'DeleteMe1': NOT_REDACTED_STRING,
                                        'DeleteMe2': NOT_REDACTED_STRING,
                                        'DoNotDelete': NOT_REDACTED_STRING},
                 'OldResourceProperties': {'Test': NOT_REDACTED_STRING,
                                           'Example': NOT_REDACTED_STRING,
                                           'Custom': NOT_REDACTED_STRING,
                                           'DeleteMe1': NOT_REDACTED_STRING,
                                           'DeleteMe2': NOT_REDACTED_STRING,
                                           'DoNotDelete': NOT_REDACTED_STRING}}
        revent = rc._redact(event)

        self.assertEqual(event['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['Custom'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe1'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DeleteMe2'], REDACTED_STRING)
        self.assertEqual(event['ResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['ResourceProperties']['DoNotDelete'], REDACTED_STRING)

        self.assertEqual(event['OldResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Test'], NOT_REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Example'], NOT_REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['Custom'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['Custom'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DeleteMe1'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DeleteMe1'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DeleteMe2'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DeleteMe2'], REDACTED_STRING)
        self.assertEqual(event['OldResourceProperties']['DoNotDelete'], NOT_REDACTED_STRING)
        self.assertEqual(revent['OldResourceProperties']['DoNotDelete'], REDACTED_STRING)


if __name__ == '__main__':
    umain()
