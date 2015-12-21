#!/usr/bin/env python 
# -*- coding: utf-8 -*-

'''developer test for extractSpecScan'''

#-----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     prjemian@gmail.com
# :copyright: (c) 2014-2015, Pete R. Jemian
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import extractSpecScan

#args = 'data/APS_spec_data.dat -s 1 6   -c mr USAXS_PD I0 seconds'
#args = 'data/33id_spec.dat     -s 1 6   -c H K L signal elastic I0 seconds'
args = 'data/CdOsO     -s 1 1.1 48   -c HerixE H K L T_control_LS340  T_sample_LS340 ICO-C  PIN-D  PIN-C Seconds'
for _ in args.split():
    sys.argv.append(_)

sys.argv.append('-G')
sys.argv.append('-V')
sys.argv.append('-Q')
sys.argv.append('-P')
extractSpecScan.main()
