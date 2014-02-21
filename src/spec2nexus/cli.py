#!/usr/bin/env python 
# -*- coding: utf-8 -*-

#-----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     prjemian@gmail.com
# :copyright: (c) 2014, Pete R. Jemian
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------


'''Converts SPEC data files and scans into NeXus HDF5 files'''


import os                           #@UnusedImport
import sys                          #@UnusedImport
import numpy as np                  #@UnusedImport

if __name__ == "__main__":
    # put us on the path for developers
    path = os.path.join('..', os.path.dirname(__file__))
    sys.path.insert(0, os.path.abspath(path))

import spec2nexus
import prjPySpec
import tree_api_parser


hdf5_extension = '.hdf5'


#-------------------------------------------------------------------------------------------


def developer_test():
    """
    test support for specific scans
    """
    spec_file_name = os.path.join('data', '33id_spec.dat')
    spec_data = prjPySpec.SpecDataFile(spec_file_name)
    scan = spec_data.getScan(22)
    print str(scan)
    root = tree_api_parser.Parser(spec_data).toTree([22])
    #print root._str_tree(indent=2, attrs=True, recursive=True)
    print root.tree


REPORTING_QUIET    = 'quiet'
REPORTING_STANDARD = 'standard'
REPORTING_VERBOSE  = 'verbose'
SCAN_LIST_ALL      = 'all'


def get_user_parameters():
    '''configure user's command line parameters from sys.argv'''
    global hdf5_extension
    import argparse
    parser = argparse.ArgumentParser(prog='spec2nexus', 
                                     description=main.__doc__.strip())
    parser.add_argument('infile', 
                        action='store', 
                        nargs='+', 
                        help="SPEC data file name(s)")
    msg =  "NeXus HDF5 output file extension"
    msg += ", default = %s" % hdf5_extension
    parser.add_argument('-e', 
                        '--hdf5-extension',
                        action='store', 
                        dest='hdf5_extension', 
                        help=msg, 
                        default=hdf5_extension)
    parser.add_argument('-f', 
                        '--force-overwrite', 
                        action='store_true',
                        dest='force_write',
                        help='overwrite output file if it exists',
                        default=False)
    parser.add_argument('-V', 
                        '--version', 
                        action='version', 
                        version=spec2nexus.__version__)
    msg =  'specify which scans to save'
    msg += ', such as: -s all  or  -s 1  or  -s 1,2,3-5  (no spaces!)'
    msg += ', default = %s' % SCAN_LIST_ALL
    parser.add_argument('-s', 
                        '--scan',
                        nargs=1, 
                        #action='append',
                        dest='scan_list',
                        default=SCAN_LIST_ALL,
                        help=msg)
    parser.add_argument('-t', 
                        '--tree-only', 
                        action='store_true',
                        dest='tree_only',
                        help='print NeXus/HDF5 node tree (does not save to a file)',
                        default=False)

    group = parser.add_mutually_exclusive_group()
    group.set_defaults(reporting_level=REPORTING_STANDARD)
    msg =  'suppress all program output (except errors)'
    msg += ', do not use with -v option'
    group.add_argument('-q', 
                       '--quiet', 
                       dest='reporting_level',
                       action='store_const',
                       const=REPORTING_QUIET,
                       help=msg)
    msg =  'print more program output'
    msg += ', do not use with -q option'
    group.add_argument('-v', 
                       '--verbose', 
                       dest='reporting_level',
                       action='store_const',
                       const=REPORTING_VERBOSE,
                       help=msg)

    return parser.parse_args()


def parse_scan_list_spec(scan_list_spec):
    '''parses the argument of the -s option, returns a scan number list'''
    # can this be simpler?
    sl = scan_list_spec[0].split(',')   # FIXME: why is this a list?

    scan_list = []
    for item in sl:
        sublist = item.split('-')
        if len(sublist) == 1:
            scan_list.append(int(sublist[0]))
        elif len(sublist) == 2:
            scan_list += range(int(sublist[0]), int(sublist[1])+1)
        else:
            raise ValueError, 'improper scan list specifier: ' + sublist

    sl = []
    for item in sorted(scan_list):
        if item not in sl:
            sl.append(item)

    return sl


def pick_scans(all_scans, opt_scan_list):
    '''
    edit opt_scan_list for the scans to be converted
    
    To be converted, a scan number must be first specified in opt_scan_list
    and then all_scans is checked to make sure that scan exists.
    The final list is returned.
    '''
    if opt_scan_list == SCAN_LIST_ALL:
        scan_list = all_scans
    else:
        scan_list = opt_scan_list
        for item in scan_list:
            if item not in all_scans:
                scan_list.remove(item)
    return scan_list


def main():
    '''spec2nexus: Convert SPEC data file into a NeXus HDF5 file.'''
    
    # developer test items
    #sys.argv.append('--help')
    #sys.argv.append('-V')
    #sys.argv.append('-q')
    #sys.argv.append('-v')
    #sys.argv.append('-f')
    #sys.argv.append('-t')
    #sys.argv.append('-s 19,1-4,19')
    #sys.argv.append('-s 2')
    #sys.argv.append(os.path.join('data', 'APS_spec_data.dat'))
    #sys.argv.append(os.path.join('data', '33id_spec.dat'))
    #sys.argv.append(os.path.join('data', '33bm_spec.dat'))
    
    # FIXME:  routine looks too complicated
    # TODO:   change to use eznx parser (issue #1)

    user_parms = get_user_parameters()

    spec_data_file_name_list = user_parms.infile

    if user_parms.scan_list != SCAN_LIST_ALL:
        user_parms.scan_list = parse_scan_list_spec(user_parms.scan_list)
    
    if user_parms.tree_only:
        if user_parms.reporting_level in (REPORTING_QUIET):
            msg = 'do not use -t/--tree-only and -q/--quiet options together'
            raise ValueError, msg
        elif user_parms.reporting_level in (REPORTING_VERBOSE):
            user_parms.reporting_level = REPORTING_STANDARD
    else:
        if not user_parms.hdf5_extension.startswith(os.extsep):
            user_parms.hdf5_extension = os.extsep + user_parms.hdf5_extension

    for spec_data_file_name in spec_data_file_name_list:
        if not os.path.exists(spec_data_file_name):
            msg = 'File not found: ' + spec_data_file_name
            print msg
            continue

        if user_parms.reporting_level in (REPORTING_STANDARD, REPORTING_VERBOSE):
            if not user_parms.tree_only:
                print 'reading SPEC data file: '+spec_data_file_name
        spec_data = prjPySpec.SpecDataFile(spec_data_file_name)
    
        scan_list = pick_scans(spec_data.scans.keys(), user_parms.scan_list)
        if user_parms.reporting_level in (REPORTING_VERBOSE):
            print '  discovered', len(spec_data.scans.keys()), ' scans'
            print '  converting scans: '  +  ', '.join(map(str, scan_list))

        tree = tree_api_parser.Parser(spec_data).toTree(scan_list)
    
        if user_parms.tree_only:
            print tree.tree
        else:
            basename = os.path.splitext(spec_data_file_name)[0]
            nexus_output_file_name = basename + user_parms.hdf5_extension
            if user_parms.force_write or not os.path.exists(nexus_output_file_name):
                tree.save(nexus_output_file_name)
                if user_parms.reporting_level in (REPORTING_STANDARD, REPORTING_VERBOSE):
                    print 'wrote NeXus HDF5 file: ' + nexus_output_file_name


if __name__ == "__main__":
    #developer_test()
    main()
