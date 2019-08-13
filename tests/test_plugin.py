'''
unit tests for the plugin module
'''

#-----------------------------------------------------------------------------
# :author:    Pete R. Jemian
# :email:     prjemian@gmail.com
# :copyright: (c) 2014-2019, Pete R. Jemian
#
# Distributed under the terms of the Creative Commons Attribution 4.0 International Public License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------

import h5py
import os, sys
import unittest

_test_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_path = os.path.abspath(os.path.join(_test_path, 'src'))

sys.path.insert(0, _path)
sys.path.insert(0, _test_path)

from spec2nexus import spec
from spec2nexus import plugin
from spec2nexus import writer


class TestPlugin(unittest.TestCase):

    def setUp(self):
        os.environ['SPEC2NEXUS_PLUGIN_PATH'] = 'C://Users//Pete//Desktop, /tmp'
        self.basepath = os.path.join(_path, 'spec2nexus')
        self.datapath = os.path.join(self.basepath, 'data')
        self.manager = plugin.get_plugin_manager()
    
    def test_handler_keys(self):
        manager = plugin.get_plugin_manager()
        h = manager.registry["#F"]
        self.assertEqual(h.key, "#F")
    
    def test_sample_control_line_keys(self):
        spec_data = {
            '#S'           : r'#S 1 ascan eta 43.6355 44.0355 40 1',
            '#D'           : r'#D Thu Jul 17 02:38:24 2003',
            '#T'           : r'#T 1 (seconds)',
            '#G\\d+'       : r'#G0 0 0 0 0 0 1 0 0 0 0 0 0 50 0 0 0 1 0 0 0 0',
            '#V\\d+'       : r'#V110 101.701 56 1 4 1 1 1 1 992.253',
            '#N'           : r'#N 14',
            '#L'           : r'#L eta H K L elastic Kalpha Epoch seconds signal I00 harmonic signal2 I0 I0',
            '#@MCA'        : r'#@MCA 16C',
            '#@CHANN'      : r'#@CHANN 1201 1110 1200 1',
            '#o\d+'        : r'#o0 un0 mx my waxsx ax un5 az un7',
            #r'@A\d*'       : r'@A 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\\',
            r'@A\d*'       : r'@A1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\\',
            #r'@A\d*'       : r'@A2 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\\',
            'scan_data'    : r' 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0'.lstrip(),
            '#H\\d+'       : r'#H4 FB_o2_on FB_o2_r FB_o2_sp',
            None           : r'#Pete wrote this stuff',
            'scan_data'    : r'43.6835 0.998671 -0.0100246 11.0078 1 0 66 1 0 863 0 0 1225 1225',
            '#@[cC][aA][lL][iI][bB]'  : r'#@CALIB 1 2 3',
            '#@[cC][aA][lL][iI][bB]'  : r'#@Calib 0.0501959 0.0141105 0 mca1',
        }
        for k, v in spec_data.items():
            if k == '#@CALIB':
                pass
            _k = self.manager.getKey(v)
            self.assertEqual(k, self.manager.getKey(v))


class TestCustomPlugin(unittest.TestCase):
    """test a custom plugin"""
    
    def test_custom_plugin(self):
        manager = plugin.get_plugin_manager()
        self.assertNotEqual(manager, None)
        self.assertTrue(isinstance(manager, plugin.PluginManager))
        num_known_control_lines_before = len(manager.lazy_attributes)
        self.assertNotEqual(num_known_control_lines_before, 0)
        
        _p = os.path.dirname(__file__)
        _p = os.path.join(_p, "custom_plugins")
        _filename = os.path.join(_p, "specfile.txt")
        custom_key = "#TEST"            # in SPEC data file
        custom_attribute = "MyTest"     # in python, scan.MyTest
        
        # first, test data with custom control line without plugin loaded
        self.assertFalse("#TEST" in manager.registry)
        self.assertFalse("MyTest" in manager.lazy_attributes)
        sdf = spec.SpecDataFile(_filename)
        scan = sdf.getScan(50)
        self.assertTrue("G0" in scan.G)

        self.assertFalse(hasattr(scan, "MyTest"))
        with self.assertRaises(AttributeError) as exc:
            self.assertEqual(len(scan.MyTest), 1)
        expected = "'SpecDataFileScan' object has no attribute 'MyTest'"
        self.assertEqual(exc.exception.args[0], expected)
        
        # next, test again after loading plugin
        from tests.custom_plugins import process_only_plugin
        num_known_control_lines_after = len(manager.lazy_attributes)
        self.assertGreater(
            num_known_control_lines_after, 
            num_known_control_lines_before)
        self.assertTrue("#TEST" in manager.registry)
        self.assertTrue("MyTest" in manager.lazy_attributes)
        
        sdf = spec.SpecDataFile(_filename)
        scan = sdf.getScan(50)
        self.assertTrue("G0" in scan.G)

        self.assertTrue(hasattr(scan, "MyTest"))
        self.assertEqual(len(scan.MyTest), 1)
        expected = "this is a custom control line to be found"
        self.assertEqual(scan.MyTest[0], expected)


class TestSpecificPlugins(unittest.TestCase):
    """test a custom plugin"""
    
    def setUp(self):
        self.hname = "test.h5"

    def tearDown(self):
        if os.path.exists(self.hname):
            os.remove(self.hname)

    def test_geometry_plugin(self):
        fname = os.path.join(_path, "spec2nexus", 'data', '33bm_spec.dat')
        scan_number = 17
        sdf = spec.SpecDataFile(fname)
        scan = sdf.getScan(scan_number)

        self.assertEqual(
            scan.diffractometer.geometry_name_full, 
            "fourc.default")
        self.assertEqual(
            scan.diffractometer.mode, 
            "Omega equals zero")
        self.assertEqual(scan.diffractometer.sector, 0)
        self.assertIsNotNone(scan.diffractometer.lattice)
        self.assertEqual(len(scan.diffractometer.reflections), 2)

        out = writer.Writer(sdf)
        out.save(self.hname, [scan_number])

        with h5py.File(self.hname, "r") as hp:
            nxentry = hp["/S17"]
            group = nxentry["instrument/geometry_parameters"]

            self.assertTrue("instrument/name" in nxentry)
            self.assertEqual(
                nxentry["instrument/name"][0], 
                scan.diffractometer.geometry_name_full.encode())
            self.assertTrue("diffractometer_simple" in group)
            self.assertEqual(group["diffractometer_simple"][0], b"fourc")
            self.assertTrue("diffractometer_full" in group)
            self.assertEqual(group["diffractometer_full"][0], b"fourc.default")
            self.assertTrue("diffractometer_variant" in group)
            self.assertEqual(group["diffractometer_variant"][0], b"default")

            for k in "g_aa g_bb g_cc g_al g_be g_ga LAMBDA".split():
                self.assertTrue(k in group)
                v = group[k][()][0]
                self.assertGreater(v, 0)

            self.assertTrue("sample/unit_cell_abc" in nxentry)
            self.assertTrue("sample/unit_cell_alphabetagamma" in nxentry)
            self.assertTrue("sample/unit_cell" in nxentry)

            self.assertTrue("sample/ub_matrix" in nxentry)
            ds = nxentry["sample/ub_matrix"]
            self.assertTupleEqual(ds.shape, (3,3))

            self.assertTrue("sample/or0" in nxentry)
            self.assertTrue("sample/or0/h" in nxentry)
            self.assertTrue("sample/or0/k" in nxentry)
            self.assertTrue("sample/or0/l" in nxentry)
            self.assertTrue("sample/or1" in nxentry)
            self.assertTrue("sample/or1/h" in nxentry)
            self.assertTrue("sample/or1/k" in nxentry)
            self.assertTrue("sample/or1/l" in nxentry)

            self.assertTrue("instrument/monochromator/wavelength" in nxentry)
            self.assertTrue("sample/beam/incident_wavelength" in nxentry)
            self.assertEqual(
                nxentry["instrument/monochromator/wavelength"],
                nxentry["sample/beam/incident_wavelength"],
                )


def suite(*args, **kw):
    test_suite = unittest.TestSuite()
    test_list = [
        TestPlugin,
        TestCustomPlugin,
        TestSpecificPlugins,
        ]
    for test_case in test_list:
        test_suite.addTest(unittest.makeSuite(test_case))
    return test_suite


if __name__ == "__main__":
    runner=unittest.TextTestRunner()
    runner.run(suite())
