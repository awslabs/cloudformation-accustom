from accustom import RedactionRuleSet
from accustom import RedactionConfig
from accustom import StandaloneRedactionConfig
from accustom import RedactMode

from unittest import TestCase, main as umain


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
        self.ruleSet.addPropertyRegex('^Test$')
        self.assertIn('^Test$', self.ruleSet._properties)

    def test_adding_invalid_regex(self):
        with self.assertRaises(TypeError):
            self.ruleSet.addPropertyRegex(0)

    def test_adding_property(self):
        self.ruleSet.addProperty('Test')
        self.assertIn('^Test$', self.ruleSet._properties)

    def test_adding_invalid_property(self):
        with self.assertRaises(TypeError):
            self.ruleSet.addProperty(0)


class RedactionConfigTests(TestCase):

    def setUp(self):
        self.ruleSetDefault = RedactionRuleSet()
        self.ruleSetDefault.addPropertyRegex('^Test$')
        self.ruleSetDefault.addProperty('Example')

        self.ruleSetCustom = RedactionRuleSet('^Custom::Test$')
        self.ruleSetCustom.addProperty('Custom')
        self.ruleSetCustom.addPropertyRegex('^DeleteMe.*$')

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
        rc.addRuleSet(self.ruleSetDefault)
        rc.addRuleSet(self.ruleSetCustom)

        self.assertIn('^.*$', rc._redactProperties)
        self.assertIn('^Custom::Test$', rc._redactProperties)
        self.assertIn('^Test$', rc._redactProperties['^.*$'])
        self.assertIn('^Example$', rc._redactProperties['^.*$'])
        self.assertIn('^DeleteMe.*$', rc._redactProperties['^Custom::Test$'])
        self.assertIn('^Custom$', rc._redactProperties['^Custom::Test$'])

    def test_redactResponseURL(self):
        rc = RedactionConfig(redactResponseURL=True)
        event = {'ResponseURL': True}
        revent = rc._redact(event)

        self.assertIn('ResponseURL', event)
        self.assertNotIn('ResponseURL', revent)

    def test_blacklist(self):
        rc = RedactionConfig(redactMode=RedactMode.BLACKLIST)
        rc.addRuleSet(self.ruleSetDefault)
        rc.addRuleSet(self.ruleSetCustom)

        # TODO: Finish tests


if __name__ == '__main__':
    umain()
