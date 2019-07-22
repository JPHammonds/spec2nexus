#!/usr/bin/env python 
# -*- coding: utf-8 -*-

#-----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     prjemian@gmail.com
# :copyright: (c) 2014-2019, Pete R. Jemian
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
define the plug-in architecture

Use :class:`spec2nexus.plugin.ControlLineHandler` as a metaclass
to create a plugin handler class for each SPEC control line.  
In each such class, it is necessary to:

* define a string value for the ``key`` (class attribute)
* override the definition of :meth:`process`

It is optional to:

* define :meth:`postprocess`
* define :meth:`writer`
* define :meth:`match_key`

.. rubric:: Functions

.. autosummary::

  ~get_registry
  ~get_registry_table
  ~load_plugins
  ~register_control_line_handler

.. rubric:: Classes

.. autosummary::

  ~ControlLineHandler
  ~PluginManager

.. rubric:: Exceptions

.. autosummary::

  ~DuplicateControlLineKey
  ~DuplicateControlLinePlugin
  ~DuplicatePlugin
  ~PluginBadKeyError
  ~PluginDuplicateKeyError
  ~PluginKeyNotDefined
  ~PluginProcessMethodNotDefined

"""


from collections import OrderedDict
import logging
import re


logger = logging.getLogger(__name__)


class PluginException(Exception):
    """parent exception for this module"""

class DuplicateControlLinePlugin(PluginException): 
    """This control line handler has been used more than once."""

class DuplicateControlLineKey(PluginException): 
    """This control line key regular expression has been used more than once."""

class DuplicatePlugin(PluginException): 
    """This plugin file name has been used more than once."""

class PluginKeyNotDefined(PluginException): 
    """Must define 'key' in class declaration."""

class PluginProcessMethodNotDefined(PluginException): 
    """Must define 'process()' method in class declaration."""

class PluginDuplicateKeyError(PluginException): 
    """This plugin key has been used before."""

class PluginBadKeyError(PluginException): 
    """The plugin 'key' value is not acceptable."""


registry = OrderedDict() # dictionary of known ControlLineHandler subclasses


def get_registry():
    return registry


def get_registry_table(print_it=False):
    """return a table of all the known plugins"""
    import pyRestTable
    tbl = pyRestTable.Table()
    tbl.addLabel("control line")
    tbl.addLabel("handler class")
    for k, v in get_registry().items():
        tbl.addRow((k, v))
    if print_it:
        print("Plugin registry")
        print(tbl)
    return tbl


def load_plugins():
    """load all spec2nexus plugin modules"""
    from . import spec
    from . import plugins   # issue #166: plugins are loaded here, NOT earlier!
    
    table = get_registry_table()
    logger.debug(str(table))

    manager = spec.plugin_manager or PluginManager()
    return manager


def register_control_line_handler(handler):
    """
    auto-registry of all AutoRegister plugins
    
    Called from AutoRegister.__init__
    """
    obj = handler()

    if not hasattr(obj, "key") or obj.key is None:
        emsg = "'key' not defined: " + obj.__class__.__name__
        raise PluginKeyNotDefined(emsg)

    key = obj.key

    if key in registry:
        emsg = "duplicate key=%s: %s" % (key, obj.__class__)
        previous = registry[key]()
        emsg += ", previously defined: " + previous.__class__.__name__
        raise PluginDuplicateKeyError(emsg)
    
    if len(key.strip().split()) != 1:
        emsg = "badly-formed 'key': received '%d'" % key
        raise PluginBadKeyError(emsg)

    if not hasattr(obj, "process") :
        emsg = "'process()' method not defined:" + obj.__class__.__name__
        raise PluginProcessMethodNotDefined(emsg)

    registry[key] = handler


class AutoRegister(type):

    """
    plugin to handle a single control line in a SPEC data file
    
    This class is a metaclass to auto-register plugins to handle
    various parts of a SPEC data file.  
    See :mod:`~spec2nexus.plugins.spec_common` for many examples.

    :param str key: regular expression to match a control line key, up to the first space
    :returns: None
    """
    
    key = None

    def __init__(cls, *args):       # args: name, bases, dict
        # logger.debug(" "*4 + "."*10)
        # logger.debug(f"__init__: cls={cls}")
        # logger.debug(f"__init__: name={name}")
        # logger.debug(f"__init__: bases={bases}")
        # logger.debug(f"__init__: dict={dict}")
        register_control_line_handler(cls)

    def __new__(metaname, classname, baseclasses, attrs):
        # logger.debug(" "*4 + "."*10)
        # logger.debug(f'__new__: metaname={metaname}')
        # logger.debug(f'__new__: classname={classname}')
        # logger.debug(f'__new__: baseclasses={baseclasses}')
        # logger.debug(f'__new__: attrs={attrs}')
        return type.__new__(metaname, classname, baseclasses, attrs)

    def __str__(self):
        return str(self.__name__)


class ControlLineHandler(object):
    """
    base class for SPEC data file control line handler plugins
    
    define one ControlLineHandler class for each different type of control line

    :param str key: regular expression to match a control line key, up to the first space
    :param [str] scan_attributes: list of scan attributes defined in this class
    :returns: None

    EXAMPLE of ``match_key`` method:
    
    Declaration of the ``match_key`` method is optional in a subclass.
    This is used to test a given line from a SPEC data file against the
    ``key`` of each ``ControlLineHandler``.
    
    If this method is defined in the subclass, it will be called
    instead of :meth:`~spec2nexus.plugin.PluginManager.match_key()`.
    This is the example used by 
    :class:`~spec2nexus.plugins.spec_common.SPEC_DataLine`::

        def match_key(self, text):
            try:
                float( text.strip().split()[0] )
                return True
            except ValueError:
                return False
    """
    key = None
    scan_attributes = []
    
    def process(self, text, spec_file_obj, *args, **kws):
        """*required:* handle this line from a SPEC data file"""
        raise NotImplementedError("must override in subclass")

    def postprocess(self, header, *args, **kws):
        """*optional:* additional processing deferred until *after* data file has been read"""
        raise NotImplementedError("must override in subclass")

    def writer(self, h5parent, writer, scan, nxclass=None, *args, **kws):
        """*optional:* Describe how to store this data in an HDF5 NeXus file"""
        raise NotImplementedError("must override in subclass")


class PluginManager(object):

    """
    Manage the set of SPEC data file control line plugins

    .. rubric:: Class Methods
    
    .. autosummary::
    
      ~get
      ~getKey
      ~match_key
      ~process
  
    """
    
    def __init__(self):
        self.handler_dict = registry
    
    def getKey(self, spec_data_file_line):
        """
        Find the key that matches this line in a SPEC data file.  Return None if not found.
        
        :param str spec_data_file_line: one line from a SPEC data file
        """
        pos = spec_data_file_line.find(' ')
        if pos < 0:
            return None
        text = spec_data_file_line[:pos]
        
        # try to locate the key directly
        if text in self.handler_dict:
            return text
        
        # brute force search and match using regular expressions
        return self.match_key(text)

    def match_key(self, text):
        """
        test if any handler's key matches text
        
        :param str text: first word on the line, 
            up to but not including the first whitespace
        :returns: key or None
        
        Applies a regular expression match using each handler's
        ``key`` as the regular expression to match with ``text``.
        """
        def _match_(text, handler):
            try:
                if handler().match_key(text):
                    return handler.key
            except AttributeError:
                # ensure that #X and #XPCS do not both match #X
                full_pattern = '^' + handler.key + '$'
                t = re.match(full_pattern, text)
                # test regexp match to avoid false positives
                # ensures that beginning and end are different positions
                return t and t.regs[0][1] != t.regs[0][0]

        for key, handler in self.handler_dict.items():
            if _match_(text, handler):
                return key
        
        return None

    def get(self, key):
        """return the handler identified by key or None"""
        return self.handler_dict.get(key)
    
    def process(self, key, *args, **kw):
        """pick the control line handler by key and call its process() method"""
        handler = self.get(key)
        if handler is not None:
            handler().process(*args, **kw)
