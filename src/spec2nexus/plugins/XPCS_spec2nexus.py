#!/usr/bin/env python 
# -*- coding: utf-8 -*-

#-----------------------------------------------------------------------------
# :author:    John Hammonds
# :email:     JPHammonds@anl.gov
#-----------------------------------------------------------------------------

"""
SPEC data file control lines unique to the APS XPCS instrument
"""

from ..plugin import ControlLineHandler
from ..eznx import makeGroup
from ..spec import SpecDataFileHeader, SpecDataFileScan
from ..utils import strip_first_word


class XPCS_VA(metaclass=ControlLineHandler):
    """**#VA**"""

    key = '#VA\d+'

    def process(self, text, spec_obj, *args, **kws):
        subkey = text.split()[0].lstrip('#')
        if not hasattr(spec_obj, 'VA'):
            spec_obj.VA = {}
        spec_obj.VA[subkey] = strip_first_word(text)
        if isinstance(spec_obj, SpecDataFileHeader):
            spec_obj.addH5writer(self.key, self.writer)
    
    def writer(self, h5parent, writer, scan, nxclass=None, *args, **kws):
        """ Describe how to write VA data"""
        desc = "XPCS VA parameters"
        group = makeGroup(h5parent, 'VA', nxclass,description=desc)
        dd = {}
        for item, value in scan.VA.items():
            dd[item] = list(map(str, value.split()))
        writer.save_dict(group, dd)


class XPCS_VD(metaclass=ControlLineHandler):
    """**#VD** """

    key = '#VD\d+'

    def process(self, text, spec_obj, *args, **kws):
        subkey = text.split()[0].lstrip('#')
        if not hasattr(spec_obj, 'VD'):
            spec_obj.VD = {}
            
        spec_obj.VD[subkey] = strip_first_word(text)
        if isinstance(spec_obj, SpecDataFileHeader):
            spec_obj.addH5writer(self.key, self.writer)
    
    def writer(self, h5parent, writer, scan, nxclass=None, *args, **kws):
        """Describe how to write VD data"""
        desc = "XPCS VD parameters"
        group = makeGroup(h5parent, 'VD', nxclass, description=desc)
        dd = {}
        for item, value in scan.VD.items():
            dd[item] = list(map(str, value.split()))
        writer.save_dict(group, dd)


class XPCS_VE(metaclass=ControlLineHandler):
    """**#VE** """

    key = '#VE\d+'

    def process(self, text, spec_obj, *args, **kws):
        subkey = text.split()[0].lstrip('#')
        if not hasattr(spec_obj, 'VE'):
            spec_obj.VE = {}
            
        spec_obj.VE[subkey] = strip_first_word(text)
        if isinstance(spec_obj, SpecDataFileHeader):
            spec_obj.addH5writer(self.key, self.writer)
    
    def writer(self, h5parent, writer, scan, nxclass=None, *args, **kws):
        """Describe how to write VE data"""
        desc = "XPCS VE parameters"
        group = makeGroup(h5parent, 'VE', nxclass,description=desc)
        dd = {}
        for item, value in scan.VE.items():
            dd[item] = list(map(str, value.split()))
        writer.save_dict(group, dd)


class XPCS_XPCS(metaclass=ControlLineHandler):
    """#XPCS"""
    
    key = '#XPCS'
    
    def process(self, text, spec_obj, *args, **kws):
        if not hasattr(spec_obj, 'XPCS'):
            spec_obj.XPCS = {}
        splitWord = strip_first_word(text).split()
        spec_obj.XPCS[splitWord[0]] = splitWord[1:]
        if isinstance(spec_obj, SpecDataFileScan):
            spec_obj.addH5writer(self.key, self.writer)
        
    def writer(self, h5parent, writer, scan, nxclass=None, *args, **kws):
        pass
    

class XPCS_CCD(metaclass=ControlLineHandler):
    """#CCD"""
    
    key = '#CCD'
    
    def process(self, text, spec_obj, *args, **kws):
        if not hasattr(spec_obj, 'CCD'):
            spec_obj.CCD = {}
        splitWord = strip_first_word(text).split()
        spec_obj.CCD[splitWord[0]] = splitWord[1:]
        if isinstance(spec_obj, SpecDataFileScan):
            spec_obj.addH5writer(self.key, self.writer)
        
    def writer(self, h5parent, writer, scan, nxclass=None, *args, **kws):
        pass
