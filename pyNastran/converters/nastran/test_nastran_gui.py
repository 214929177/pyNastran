import os

from pyNastran.gui.testing_methods import add_dummy_gui_functions
from pyNastran.converters.nastran.nastranIOv import NastranIO
import pyNastran

pkg_path = pyNastran.__path__[0]
model_path = os.path.join(pkg_path, '..', 'models')

import unittest

class NastranGUI(unittest.TestCase):

    def test_solid_shell_bar_01(self):
        bdf_filename = os.path.join(model_path, 'sol_101_elements', 'static_solid_shell_bar.bdf')
        op2_filename = os.path.join(model_path, 'sol_101_elements', 'static_solid_shell_bar.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        test.load_nastran_results(op2_filename, None)

    def test_solid_shell_bar_02(self):
        bdf_filename = os.path.join(model_path, 'sol_101_elements', 'mode_solid_shell_bar.bdf')
        op2_filename = os.path.join(model_path, 'sol_101_elements', 'mode_solid_shell_bar.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        test.load_nastran_results(op2_filename, None)

    def test_solid_shell_bar_03(self):
        bdf_filename = os.path.join(model_path, 'sol_101_elements', 'static_solid_comp_bar.bdf')
        op2_filename = os.path.join(model_path, 'sol_101_elements', 'static_solid_comp_bar.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        test.load_nastran_results(op2_filename, None)

    def test_solid_bending(self):
        bdf_filename = os.path.join(model_path, 'solid_bending', 'solid_bending.bdf')
        op2_filename = os.path.join(model_path, 'solid_bending', 'solid_bending.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        test.load_nastran_results(op2_filename, None)

    def test_contact(self):
        bdf_filename = os.path.join(model_path, 'contact', 'contact.bdf')
        op2_filename = os.path.join(model_path, 'contact', 'contact.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        test.load_nastran_results(op2_filename, None)

    def test_fsi(self):
        bdf_filename = os.path.join(model_path, 'fsi', 'fsi.bdf')
        op2_filename = os.path.join(model_path, 'fsi', 'fsi.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        test.load_nastran_results(op2_filename, None)

    def test_beam_modes_01(self):
        dirname = bdf_filename = os.path.join(model_path, 'beam_modes')
        bdf_filename = os.path.join(dirname, 'beam_modes.dat')
        op2_filename = os.path.join(dirname, 'beam_modes_m1.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        #test.load_nastran_results(op2_filename, None)

        test.load_nastran_geometry(bdf_filename, dirname)
        #test.load_nastran_results(op2_filename, dirname)

        test.load_nastran_geometry(bdf_filename, '')

    def test_beam_modes_02(self):
        dirname = bdf_filename = os.path.join(model_path, 'beam_modes')
        bdf_filename = os.path.join(dirname, 'beam_modes.dat')
        op2_filename = os.path.join(dirname, 'beam_modes_m2.op2')

        test = NastranIO()
        test.is_nodal = False
        test.is_centroidal = True

        add_dummy_gui_functions(test)

        test.load_nastran_geometry(bdf_filename, None)
        test.load_nastran_results(op2_filename, None)

        test.load_nastran_geometry(bdf_filename, dirname)
        test.load_nastran_results(op2_filename, dirname)

        test.load_nastran_geometry(bdf_filename, '')


def test_bottle():
    """
    Tests Nastran GUI loading
    """
    test = NastranIO()
    test.is_nodal = False
    test.is_centroidal = True

    add_dummy_gui_functions(test)

    #test.load_panair_geometry('SWB.INP','')
    test.load_nastran_geometry('bottle_shell_w_holes_pmc.bdf', '')
    test.load_nastran_results('bottle_shell_w_holes_pmc.op2', '')

    keys = test.resultCases.keys()
    assert (1, 'Stress1', 1, 'centroid', '%.3f') in keys, keys

if __name__ == '__main__':  # pragma: no cover
    #test_solid_shell_bar_01()
    unittest.main()

