
"""
test of "Using Metaclasses to Create Self-Registering Plugins"

see: https://www.effbot.org/zone/metaclass-plugins.htm
"""

from plugin_base import Plugin

class SpamPlugin(metaclass=Plugin):
    pass
