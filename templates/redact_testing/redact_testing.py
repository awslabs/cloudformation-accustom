import logging
logging.getLogger().setLevel(logging.DEBUG)

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

logger = logging.getLogger(__name__)

@decorator(hideResourceDeleteFailure=True,
           timeoutFunction=False,
           redactConfig=rc)
def handler(event,context):
    # No action actually required since we'll be looking at CW Logs.
    pass