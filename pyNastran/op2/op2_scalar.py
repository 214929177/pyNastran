#pylint: disable=C0301,W0613,W0612,R0913
"""
Defines the OP2 class.
"""
from __future__ import (nested_scopes, generators, division, absolute_import,
                        print_function, unicode_literals)
from six import string_types, iteritems, PY2
from six.moves import range
import os
from struct import unpack, Struct

from numpy import array

from pyNastran import is_release
from pyNastran.f06.errors import FatalError
from pyNastran.op2.op2_common import SortCodeError
from pyNastran.f06.tables.grid_point_weight import GridPointWeight

#============================

from pyNastran.op2.tables.lama_eigenvalues.lama import LAMA
from pyNastran.op2.tables.oee_energy.onr import ONR
from pyNastran.op2.tables.opg_appliedLoads.ogpf import OGPF

from pyNastran.op2.tables.oef_forces.oef import OEF
from pyNastran.op2.tables.oes_stressStrain.oes import OES
from pyNastran.op2.tables.ogs import OGS

from pyNastran.op2.tables.opg_appliedLoads.opg import OPG
from pyNastran.op2.tables.oqg_constraintForces.oqg import OQG
from pyNastran.op2.tables.oug.oug import OUG
from pyNastran.op2.tables.ogpwg import OGPWG
from pyNastran.op2.fortran_format import FortranFormat

from pyNastran.utils import is_binary_file
from pyNastran.utils.log import get_logger


class TrashWriter(object):
    """
    A dummy file that just trashes all data
    """
    def __init__(self, *args, **kwargs):
        """does nothing"""
        pass
    def open(self, *args, **kwargs):
        """does nothing"""
        pass
    def write(self, *args, **kwargs):
        """does nothing"""
        pass
    def close(self, *args, **kwargs):
        """does nothing"""
        pass

GEOM_TABLES = [
     b'GEOM1', b'GEOM2', b'GEOM3', b'GEOM4',  # regular
     b'GEOM1S', b'GEOM2S', b'GEOM3S', b'GEOM4S', # superelements
     b'GEOM1N', b'GEOM1VU', b'GEOM2VU',
     b'GEOM1OLD', b'GEOM2OLD', b'GEOM4OLD',

     b'EPT', b'EPTS', b'EPTOLD',
     b'EDTS',
     b'MPT', b'MPTS',

     b'PVT0', b'CASECC',
     b'EDOM', b'OGPFB1',
     b'BGPDT', b'BGPDTS', b'BGPDTOLD',
     b'DYNAMIC', b'DYNAMICS',
     b'EQEXIN', b'EQEXINS',
     b'GPDT', b'ERRORN',
     b'DESTAB', b'R1TABRG', b'HISADD',

     # eigenvalues
     b'BLAMA', b'LAMA', b'CLAMA',  #CLAMA is new
     # strain energy
     b'ONRGY1',
     # grid point weight
     b'OGPWG', b'OGPWGM',

     # other
     b'CONTACT', b'VIEWTB',
     b'KDICT', b'MONITOR', b'PERF',
]

RESULT_TABLES = [
    # stress
    b'OES1X1', b'OES1', b'OES1X', b'OES1C', b'OESCP',
    b'OESNLXR', b'OESNLXD', b'OESNLBR', b'OESTRCP',
    b'OESNL1X', b'OESRT',
    # strain
    b'OSTR1X', b'OSTR1C',
    # forces
    b'OEFIT', b'OEF1X', b'OEF1', b'DOEF1',
    # spc forces - gset - sort 1
    b'OQG1', b'OQGV1',
    # mpc forces - gset - sort 1
    b'OQMG1',
    # ??? forces
    b'OQP1',
    # displacement/velocity/acceleration/eigenvector/temperature
    b'OUG1', b'OUGV1', b'BOUGV1', b'OUPV1', b'OUGV1PAT',

    b'ROUGV1', b'TOUGV1', b'RSOUGV1', b'RESOES1', b'RESEF1',

    # applied loads
    b'OPNL1', # nonlinear applied loads - sort 1
    b'OPG1', b'OPGV1', # applied loads - gset? - sort 1
    b'OPG2', # applied loads - sort 2 - v0.8

    # grid point stresses
    b'OGS1', # grid point stresses/strains - sort 1

    # other
    b'OPNL1', b'OFMPF2M',
    b'OSMPF2M', b'OPMPF2M', b'OLMPF2M', b'OGPMPF2M',

    b'OAGPSD2', b'OAGCRM2', b'OAGRMS2', b'OAGATO2', b'OAGNO2',
    b'OESPSD2', b'OESCRM2', b'OESRMS2', b'OESATO2', b'OESNO2',
    b'OEFPSD2', b'OEFCRM2', b'OEFRMS2', b'OEFATO2', b'OEFNO2',
    b'OPGPSD2', b'OPGCRM2', b'OPGRMS2', b'OPGATO2', b'OPGNO2',
    b'OQGPSD2', b'OQGCRM2', b'OQGRMS2', b'OQGATO2', b'OQGNO2',
    b'OQMPSD2', b'OQMCRM2', b'OQMRMS2', b'OQMATO2', b'OQMNO2',
    b'OUGPSD2', b'OUGCRM2', b'OUGRMS2', b'OUGATO2', b'OUGNO2',
    b'OVGPSD2', b'OVGCRM2', b'OVGRMS2', b'OVGATO2', b'OVGNO2',
    b'OSTRPSD2', b'OSTRCRM2', b'OSTRRMS2', b'OSTRATO2', b'OSTRNO2',
    b'OCRUG',
    b'OCRPG',
    b'STDISP',

    # autoskip
    b'MATPOOL',
    b'CSTM',
    b'AXIC',
    b'BOPHIG',
    b'HOEF1',
    b'ONRGY2',

    #------------------------------------------
    # new skipped - v0.8

    # buggy
    b'IBULK',
    b'FRL',
    b'TOL',
    b'DSCM2', # normalized design sensitivity coeff. matrix

    # dont seem to crash
    b'DESCYC',
    b'DBCOPT', # design optimization history for post-processing
    b'PVT',    # table containing PARAM data
    b'XSOP2DIR',
    b'ONRGY',
    #b'CLAMA',
    b'DSCMCOL', # design sensitivity parameters
    b'CONTACTS',
    b'EDT', # aero and element deformations
    b'EXTDB',


    b'OQG2', # single point forces - sort 2 - v0.8
    b'OBC1', b'OBC2', # contact pressures and tractions at grid points
    b'OBG1', # glue normal and tangential tractions at grid points in basic coordinate system
    b'OES2', # element stresses - sort 2 - v0.8
    b'OEF2', # element forces - sort 2 - v0.8
    b'OPG2', # applied loads - sort 2 - v0.8
    b'OUGV2', # absolute displacements/velocity/acceleration - sort 2

    # contact
    b'OSPDSI1', # intial separation distance
    b'OSPDS1',  # final separation distance
    b'OQGCF1', b'OQGCF2', # contact force at grid point
    b'OQGGF1', b'OQGGF2', # glue forces in grid point basic coordinate system

    b'OUGRMS1',
    b'OESRMS1',
    b'OUGNO1',
    b'OESNO1',

    b'OSPDSI2',
    b'OSPDS2',
    b'OSTR2',
    b'OESNLXR2',

    b'CMODEXT',
    b'ROUGV2',  # relative displacement
    b'CDDATA',  # cambpell diagram table
    b'OEKE1',
    b'OES1MX', # extreme stresses?
    b'OESNLBR2',
    b'BGPDTVU', # basic grid point defintion table for a superelement and related to geometry with view-grids added
]

class OP2_Scalar(LAMA, ONR, OGPF,
                 OEF, OES, OGS, OPG, OQG, OUG, OGPWG, FortranFormat):
    """
    Defines an interface for the Nastran OP2 file.
    """
    def set_as_nx(self):
        self.is_nx = True
        self.is_msc = False

    def set_as_msc(self):
        self.is_nx = False
        self.is_msc = True

    def __init__(self, debug=False, log=None, debug_file=None):
        """
        Initializes the OP2_Scalar object

        :param debug: enables the debug log and sets the debug in the logger (default=False)
        :param log: a logging object to write debug messages to
         (.. seealso:: import logging)
        :param debug_file: sets the filename that will be written to (default=None -> no debug)
        """
        assert isinstance(debug, bool), 'debug=%r' % debug

        self.log = get_logger(log, 'debug' if debug else 'info')
        self.op2_filename = None
        self.bdf_filename = None
        self.f06_filename = None

        LAMA.__init__(self)
        ONR.__init__(self)
        OGPF.__init__(self)

        OEF.__init__(self)
        OES.__init__(self)
        OGS.__init__(self)

        OPG.__init__(self)
        OQG.__init__(self)
        OUG.__init__(self)
        OGPWG.__init__(self)
        FortranFormat.__init__(self)

        self.read_mode = 0
        self.is_vectorized = False
        self._close_op2 = True

        self.result_names = set([])

        self.grid_point_weight = GridPointWeight()
        self.words = []
        self.debug = debug
        #self.debug = True
        #self.debug = False
        #debug_file = None
        if debug_file is None:
            self.debug_file = None
        else:
            assert isinstance(debug_file, string_types), debug_file
            self.debug_file = debug_file
        self.make_geom = False

    def set_as_vectorized(self, vectorized=False, ask=False):
        """don't call this...testing"""
        if vectorized is True:
            msg = 'OP2_Scalar class doesnt support vectorization.  Use OP2 '
            msg += 'from pyNastran.op2.op2 instead.'
            raise RuntimeError(msg)
        if ask is True:
            msg = 'OP2_Scalar class doesnt support ask.'
            raise RuntimeError(msg)

    def set_subcases(self, subcases=None):
        """
        Allows you to read only the subcases in the list of iSubcases

        :param subcases: list of [subcase1_ID,subcase2_ID]
                         (default=None; all subcases)
        """
        #: stores the set of all subcases that are in the OP2
        self.subcases = set()
        if subcases is None or subcases == []:
            #: stores if the user entered [] for iSubcases
            self.isAllSubcases = True
            self.valid_subcases = []
        else:
            #: should all the subcases be read (default=True)
            self.isAllSubcases = False

            #: the set of valid subcases -> set([1,2,3])
            self.valid_subcases = set(subcases)
        self.log.debug("set_subcases - subcases = %s" % self.valid_subcases)

    def set_transient_times(self, times):  # TODO this name sucks...
        """
        Takes a dictionary of list of times in a transient case and
        gets the output closest to those times.

        .. code-block:: python
          times = {subcaseID_1: [time1, time2],
                   subcaseID_2: [time3, time4]}
        """
        expected_times = {}
        for (isubcase, eTimes) in iteritems(times):
            eTimes = list(times)
            eTimes.sort()
            expected_times[isubcase] = array(eTimes)
        self.expected_times = expected_times

    def _get_table_mapper(self):
        table_mapper = {
            #b'HISADD': [self._hisadd_3, self._hisadd_4],  # optimization history (SOL200)
            b'HISADD': [self._table_passer, self._table_passer],
            b'R1TABRG': [self._table_passer, self._table_passer],

            b'MATPOOL': [self._table_passer, self._table_passer],
            b'CSTM':    [self._table_passer, self._table_passer],
            b'TOUGV1':  [self._table_passer, self._table_passer],  # grid point temperature
            b'AXIC':    [self._table_passer, self._table_passer],
            b'BOPHIG':  [self._table_passer, self._table_passer],  # eigenvectors in basic coordinate system
            b'ONRGY2':  [self._table_passer, self._table_passer],

            b'RSOUGV1': [self._table_passer, self._table_passer],
            b'RESOES1': [self._table_passer, self._table_passer],
            b'RESEF1' : [self._table_passer, self._table_passer],
            b'DESCYC' : [self._table_passer, self._table_passer],
            #=======================
            # OEF
            # element forces
            b'OEFIT' : [self._read_oef1_3, self._read_oef1_4],  # failure indices
            b'OEF1X' : [self._read_oef1_3, self._read_oef1_4],  # element forces at intermediate stations
            b'OEF1'  : [self._read_oef1_3, self._read_oef1_4],  # element forces or heat flux
            b'HOEF1':  [self._table_passer, self._table_passer], # element heat flux
            b'DOEF1' : [self._read_oef1_3, self._read_oef1_4],  # scaled response spectra - spc forces?
            #=======================
            # OQG
            # spc forces
            b'OQG1'  : [self._read_oqg1_3, self._read_oqg1_4],  # spc forces in the nodal frame
            b'OQGV1' : [self._read_oqg1_3, self._read_oqg1_4],  # spc forces in the nodal frame
            # mpc forces
            b'OQMG1' : [self._read_oqg1_3, self._read_oqg1_4],

            # ???? - passer
            #'OQP1': [self._table_passer, self._table_passer],  # scaled response spectra - displacement
            #=======================
            # OPG
            # applied loads
            b'OPG1'  : [self._read_opg1_3, self._read_opg1_4],  # applied loads in the nodal frame
            b'OPGV1' : [self._read_opg1_3, self._read_opg1_4],
            b'OPNL1' : [self._read_opg1_3, self._read_opg1_4],  # nonlinear loads

            # OGPFB1
            # grid point forces
            b'OGPFB1' : [self._read_ogpf1_3, self._read_ogpf1_4],  # grid point forces

            # ONR/OEE
            # strain energy density
            b'ONRGY1' : [self._read_onr1_3, self._read_onr1_4],  # strain energy density
            #=======================
            # OES
            # stress
            b'OES1X1'  : [self._read_oes1_3, self._read_oes1_4],  # stress - nonlinear elements
            b'OES1'    : [self._read_oes1_3, self._read_oes1_4],  # stress - linear only
            b'OES1X'   : [self._read_oes1_3, self._read_oes1_4],  # element stresses at intermediate stations & nonlinear stresses
            b'OES1C'   : [self._read_oes1_3, self._read_oes1_4],  # stress - composite
            b'OESCP'   : [self._read_oes1_3, self._read_oes1_4],
            b'OESNLXR' : [self._read_oes1_3, self._read_oes1_4],  # nonlinear stresses
            b'OESNLXD' : [self._read_oes1_3, self._read_oes1_4],  # nonlinear transient stresses
            b'OESNLBR' : [self._read_oes1_3, self._read_oes1_4],
            b'OESTRCP' : [self._read_oes1_3, self._read_oes1_4],
            b'OESNL1X' : [self._read_oes1_3, self._read_oes1_4],
            b'OESRT'   : [self._read_oes1_3, self._read_oes1_4],

            # strain
            b'OSTR1X'  : [self._read_oes1_3, self._read_oes1_4],  # strain - isotropic
            b'OSTR1C'  : [self._read_oes1_3, self._read_oes1_4],  # strain - composite

            #=======================
            # OUG
            # displacement/velocity/acceleration/eigenvector/temperature
            b'OUG1'    : [self._read_oug1_3, self._read_oug1_4],  # displacements in nodal frame
            b'OUGV1'   : [self._read_oug1_3, self._read_oug1_4],  # displacements in nodal frame
            b'BOUGV1'  : [self._read_oug1_3, self._read_oug1_4],  # OUG1 on the boundary???
            b'OUGV1PAT': [self._read_oug1_3, self._read_oug1_4],  # OUG1 + coord ID
            b'OUPV1'   : [self._read_oug1_3, self._read_oug1_4],  # scaled response spectra - displacement

            #=======================
            # OGPWG
            # grid point weight
            b'OGPWG'  : [self._read_ogpwg_3, self._read_ogpwg_4],  # grid point weight
            b'OGPWGM' : [self._read_ogpwg_3, self._read_ogpwg_4],  # modal? grid point weight

            #=======================
            # OGS
            # grid point stresses
            b'OGS1' : [self._read_ogs1_3, self._read_ogs1_4],  # grid point stresses
            #=======================
            # eigenvalues
            b'BLAMA': [self._read_buckling_eigenvalue_3, self._read_buckling_eigenvalue_4], # buckling eigenvalues
            b'CLAMA': [self._read_complex_eigenvalue_3, self._read_complex_eigenvalue_4],   # complex eigenvalues
            b'LAMA' : [self._read_real_eigenvalue_3, self._read_real_eigenvalue_4],         # eigenvalues

            # ===geom passers===
            # geometry
            b'GEOM1': [self._table_passer, self._table_passer],
            b'GEOM2': [self._table_passer, self._table_passer],
            b'GEOM3': [self._table_passer, self._table_passer],
            b'GEOM4': [self._table_passer, self._table_passer],

            # superelements
            b'GEOM1S': [self._table_passer, self._table_passer],  # GEOMx + superelement
            b'GEOM2S': [self._table_passer, self._table_passer],
            b'GEOM3S': [self._table_passer, self._table_passer],
            b'GEOM4S': [self._table_passer, self._table_passer],

            b'GEOM1N': [self._table_passer, self._table_passer],
            b'GEOM2N': [self._table_passer, self._table_passer],
            b'GEOM3N': [self._table_passer, self._table_passer],
            b'GEOM4N': [self._table_passer, self._table_passer],

            b'GEOM1OLD': [self._table_passer, self._table_passer],
            b'GEOM2OLD': [self._table_passer, self._table_passer],
            b'GEOM3OLD': [self._table_passer, self._table_passer],
            b'GEOM4OLD': [self._table_passer, self._table_passer],

            b'EPT' : [self._table_passer, self._table_passer],  # elements
            b'EPTS': [self._table_passer, self._table_passer],  # elements - superelements
            b'EPTOLD' : [self._table_passer, self._table_passer],

            b'MPT' : [self._table_passer, self._table_passer],  # materials
            b'MPTS': [self._table_passer, self._table_passer],  # materials - superelements

            b'DYNAMIC': [self._table_passer, self._table_passer],
            b'DYNAMICS': [self._table_passer, self._table_passer],
            b'DIT': [self._table_passer, self._table_passer],

            # geometry
            #b'GEOM1': [self._read_geom1_4, self._read_geom1_4],
            #b'GEOM2': [self._read_geom2_4, self._read_geom2_4],
            #b'GEOM3': [self._read_geom3_4, self._read_geom3_4],
            #b'GEOM4': [self._read_geom4_4, self._read_geom4_4],

            # superelements
            #b'GEOM1S': [self._read_geom1_4, self._read_geom1_4],
            #b'GEOM2S': [self._read_geom2_4, self._read_geom2_4],
            #b'GEOM3S': [self._read_geom3_4, self._read_geom3_4],
            #b'GEOM4S': [self._read_geom4_4, self._read_geom4_4],

            #b'GEOM1N': [self._read_geom1_4, self._read_geom1_4],
            #b'GEOM2N': [self._read_geom2_4, self._read_geom2_4],
            #b'GEOM3N': [self._read_geom3_4, self._read_geom3_4],
            #b'GEOM4N': [self._read_geom4_4, self._read_geom4_4],

            #b'GEOM1OLD': [self._read_geom1_4, self._read_geom1_4],
            #b'GEOM2OLD': [self._read_geom2_4, self._read_geom2_4],
            #b'GEOM3OLD': [self._read_geom3_4, self._read_geom3_4],
            #b'GEOM4OLD': [self._read_geom4_4, self._read_geom4_4],

            #b'EPT' : [self._read_ept_4, self._read_ept_4],
            #b'EPTS': [self._read_ept_4, self._read_ept_4],
            #b'EPTOLD' : [self._read_ept_4, self._read_ept_4],

            #b'MPT' : [self._read_mpt_4, self._read_mpt_4],
            #b'MPTS': [self._read_mpt_4, self._read_mpt_4],

            #b'DYNAMIC': [self._read_dynamics_4, self._read_dynamics_4],
            #b'DYNAMICS': [self._read_dynamics_4, self._read_dynamics_4],
            #b'DIT': [self._read_dit_4, self._read_dit_4],   # table objects (e.g. TABLED1)

            # ===passers===
            b'EQEXIN': [self._table_passer, self._table_passer],
            b'EQEXINS': [self._table_passer, self._table_passer],

            b'GPDT': [self._table_passer, self._table_passer],     # grid points?
            b'BGPDT': [self._table_passer, self._table_passer],    # basic grid point defintion table
            b'BGPDTS': [self._table_passer, self._table_passer],
            b'BGPDTOLD': [self._table_passer, self._table_passer],

            b'PVT0': [self._table_passer, self._table_passer],  # user parameter value table
            b'DESTAB': [self._table_passer, self._table_passer],
            b'STDISP': [self._table_passer, self._table_passer],
            b'CASECC': [self._table_passer, self._table_passer],  # case control deck

            b'EDTS': [self._table_passer, self._table_passer],
            b'FOL': [self._table_passer, self._table_passer],
            b'MONITOR': [self._table_passer, self._table_passer],  # monitor points
            b'PERF': [self._table_passer, self._table_passer],
            b'VIEWTB': [self._table_passer, self._table_passer],   # view elements

            #==================================
            b'OUGATO2': [self._table_passer, self._table_passer],
            b'OUGCRM2': [self._table_passer, self._table_passer],
            b'OUGNO2': [self._table_passer, self._table_passer],
            b'OUGPSD2': [self._table_passer, self._table_passer],  # psd
            b'OUGRMS2': [self._table_passer, self._table_passer],  # rms

            b'OQGATO2': [self._table_passer, self._table_passer],
            b'OQGCRM2': [self._table_passer, self._table_passer],

            b'OQGNO2': [self._table_passer, self._table_passer],
            b'OQGPSD2': [self._table_passer, self._table_passer],
            b'OQGRMS2': [self._table_passer, self._table_passer],

            b'OFMPF2M': [self._table_passer, self._table_passer],
            b'OLMPF2M': [self._table_passer, self._table_passer],
            b'OPMPF2M': [self._table_passer, self._table_passer],
            b'OSMPF2M': [self._table_passer, self._table_passer],
            b'OGPMPF2M': [self._table_passer, self._table_passer],

            b'OEFATO2': [self._table_passer, self._table_passer],
            b'OEFCRM2': [self._table_passer, self._table_passer],
            b'OEFNO2': [self._table_passer, self._table_passer],
            b'OEFPSD2': [self._table_passer, self._table_passer],
            b'OEFRMS2': [self._table_passer, self._table_passer],

            b'OESATO2': [self._table_passer, self._table_passer],
            b'OESCRM2': [self._table_passer, self._table_passer],
            b'OESNO2': [self._table_passer, self._table_passer],
            b'OESPSD2': [self._table_passer, self._table_passer],
            b'OESRMS2': [self._table_passer, self._table_passer],

            b'OVGATO2': [self._table_passer, self._table_passer],
            b'OVGCRM2': [self._table_passer, self._table_passer],
            b'OVGNO2': [self._table_passer, self._table_passer],
            b'OVGPSD2': [self._table_passer, self._table_passer],
            b'OVGRMS2': [self._table_passer, self._table_passer],

            #==================================
            #b'GPL': [self._table_passer, self._table_passer],
            b'OMM2': [self._table_passer, self._table_passer],
            b'ERRORN': [self._table_passer, self._table_passer],  # p-element error summary table
            #==================================

            b'OCRPG': [self._table_passer, self._table_passer],
            b'OCRUG': [self._table_passer, self._table_passer],

            b'EDOM': [self._table_passer, self._table_passer],

            b'OAGPSD2': [self._table_passer, self._table_passer],
            b'OAGATO2': [self._table_passer, self._table_passer],
            b'OAGRMS2': [self._table_passer, self._table_passer],
            b'OAGNO2': [self._table_passer, self._table_passer],
            b'OAGCRM2': [self._table_passer, self._table_passer],

            b'OPGPSD2': [self._table_passer, self._table_passer],
            b'OPGATO2': [self._table_passer, self._table_passer],
            b'OPGRMS2': [self._table_passer, self._table_passer],
            b'OPGNO2': [self._table_passer, self._table_passer],
            b'OPGCRM2': [self._table_passer, self._table_passer],

            b'OSTRPSD2': [self._table_passer, self._table_passer],
            b'OSTRATO2': [self._table_passer, self._table_passer],
            b'OSTRRMS2': [self._table_passer, self._table_passer],
            b'OSTRNO2': [self._table_passer, self._table_passer],
            b'OSTRCRM2': [self._table_passer, self._table_passer],

            b'OQMPSD2': [self._table_passer, self._table_passer],
            b'OQMATO2': [self._table_passer, self._table_passer],
            b'OQMRMS2': [self._table_passer, self._table_passer],
            b'OQMNO2': [self._table_passer, self._table_passer],
            b'OQMCRM2': [self._table_passer, self._table_passer],

            #b'AAA': [self._table_passer, self._table_passer],
            #b'AAA': [self._table_passer, self._table_passer],
            #b'AAA': [self._table_passer, self._table_passer],
            #b'AAA': [self._table_passer, self._table_passer],
        }
        return table_mapper

    #def _hisadd_3(self, data):
        #"""
        #table of design iteration history for current design cycle
        #HIS table
        #"""
        #self.show_data(data, types='ifs')
        #asf

    #def _hisadd_4(self, data):
        #self.show_data(data, types='ifs')
        #asf

    def _not_available(self, data):
        """testing function"""
        if len(data) > 0:
            raise RuntimeError('this should never be called...table_name=%r len(data)=%s' % (self.table_name, len(data)))

    def _table_passer(self, data):
        """auto-table skipper"""
        return len(data)

    def _validate_op2_filename(self, op2_filename):
        """
        Pops a GUI if the op2_filename hasn't been set.

        :param op2_filename:  the filename to check (None -> gui)
        :returns op2_filename:  a valid file string
        """
        if op2_filename is None:
            from pyNastran.utils.gui_io import load_file_dialog
            wildcard_wx = "Nastran OP2 (*.op2)|*.op2|" \
                "All files (*.*)|*.*"
            wildcard_qt = "Nastran OP2 (*.op2);;All files (*)"
            title = 'Please select a OP2 to load'
            op2_filename, wildcard_level = load_file_dialog(title, wildcard_wx, wildcard_qt, dirname='')
            assert op2_filename is not None, op2_filename
        return op2_filename

    def _create_binary_debug(self):
        """
        Instatiates the ``self.binary_debug`` variable/file
        """
        if hasattr(self, 'binary_debug') and self.binary_debug is not None:
            self.binary_debug.close()
            del self.binary_debug

        wb = 'w'
        if PY2:
            wb = 'wb'

        if self.debug_file is not None:
            #: an ASCII version of the op2 (creates lots of output)
            self.binary_debug = open(self.debug_file, wb)
            self.binary_debug.write(self.op2_filename + '\n')
        else:
            self.binary_debug = open(os.devnull, wb)  #TemporaryFile()
            self.binary_debug = TrashWriter('debug.out', wb)

    def read_op2(self, op2_filename=None):
        """
        Starts the OP2 file reading

        :param op2_filename: the op2 file
        +--------------+-----------------------+
        | op2_filename | Description           |
        +--------------+-----------------------+
        |     None     | a dialog is popped up |
        +--------------+-----------------------+
        |    string    | the path is used      |
        +--------------+-----------------------+
        """
        if self.read_mode in [0, 1]:
            #sr = list(self._results.saved)
            #sr.sort()
            #self.log.debug('_results.saved = %s' % str(sr))
            #self.log.info('_results.saved = %s' % str(sr))
            pass

        if self.read_mode != 2:
            op2_filename = self._validate_op2_filename(op2_filename)
            self.log.debug('op2_filename = %r' % op2_filename)
            if not is_binary_file(op2_filename):
                if os.path.getsize(op2_filename) == 0:
                    raise IOError('op2_filename=%r is empty.' % op2_filename)
                raise IOError('op2_filename=%r is not a binary OP2.' % op2_filename)

        bdf_extension = '.bdf'
        f06_extension = '.f06'
        (fname, extension) = os.path.splitext(op2_filename)

        self.op2_filename = op2_filename
        self.bdf_filename = fname + bdf_extension
        self.f06_filename = fname + f06_extension

        self._create_binary_debug()

        #: file index
        self.n = 0
        self.table_name = None

        if not hasattr(self, 'f') or self.f is None:
            #: the OP2 file object
            self.f = open(self.op2_filename, 'rb')
        else:
            self.goto(self.n)

        try:
            markers = self.get_nmarkers(1, rewind=True)
        except:
            self.goto(0)
            try:
                self.f.read(4)
            except:
                raise FatalError("The OP2 is empty.")
            raise

        if markers == [3,]:  # PARAM, POST, -1
            self.read_markers([3])
            data = self.read_block()

            self.read_markers([7])
            data = self.read_block()
            data = self._read_record()
            self.read_markers([-1, 0])
        elif markers == [2,]:  # PARAM, POST, -2
            pass
        else:
            raise NotImplementedError(markers)

        #table_name = self.read_table_name(rewind=False, stop_on_failure=False)
        #=================
        table_name = self.read_table_name(rewind=True, stop_on_failure=False)
        if table_name is None:
            raise FatalError('no tables exists...')

        table_names = self._read_tables(table_name)
        if self.debug:
            self.binary_debug.write('-' * 80 + '\n')
            self.binary_debug.write('f.tell()=%s\ndone...\n' % self.f.tell())
        self.binary_debug.close()
        if self._close_op2:
            self.f.close()
            del self.binary_debug
            del self.f
        #self.remove_unpickable_data()
        return table_names

    #def create_unpickable_data(self):
        #raise NotImplementedError()
        ##==== not needed ====
        ##self.f
        ##self.binary_debug

        ## needed
        #self._geom1_map
        #self._geom2_map
        #self._geom3_map
        #self._geom4_map
        #self._dit_map
        #self._dynamics_map
        #self._ept_map
        #self._mpt_map
        #self._table_mapper

    #def remove_unpickable_data(self):
        #del self.f
        #del self.binary_debug
        #del self._geom1_map
        #del self._geom2_map
        #del self._geom3_map
        #del self._geom4_map
        #del self._dit_map
        #del self._dynamics_map
        #del self._ept_map
        #del self._mpt_map
        #del self._table_mapper

    def _read_tables(self, table_name):
        """
        Reads all the geometry/result tables.
        The OP2 header is not read by this function.

        :param table_name: the first table's name
        """
        table_names = []
        while table_name is not None:
            table_names.append(table_name)

            if self.debug:
                self.binary_debug.write('-' * 80 + '\n')
                self.binary_debug.write('table_name = %r; f.tell()=%s\n' % (table_name, self.f.tell()))

            if is_release:
                self.log.info('  table_name=%r' % table_name)

            self.table_name = table_name
            if 0:
                self._skip_table(table_name)
            else:
                if table_name in GEOM_TABLES:
                    self._read_geom_table()  # DIT (agard)
                elif table_name in [b'GPL', ]:
                    self._read_gpl()
                elif table_name in [b'MEFF', ]:
                    self._read_meff()
                elif table_name in [b'INTMOD', ]:
                    self._read_intmod()
                #elif table_name in [b'HISADD', ]:
                    #self._read_hisadd()

                elif table_name in [b'OMM2', ]:
                    self._read_omm2()
                elif table_name in [b'DIT']:  # tables
                    self._read_dit()
                elif table_name in [b'KELM']:
                    self._read_kelm()
                elif table_name in [b'PCOMPTS']: # blade
                    self._read_pcompts()
                elif table_name == b'FOL':
                    self._read_fol()
                elif table_name in [b'SDF', b'PMRF']:  #, 'PERF'
                    self._read_sdf()
                elif table_name in RESULT_TABLES:
                    self._read_results_table()
                elif table_name.strip() in self.additional_matrices:
                    self._read_matrix()
                else:
                    msg = 'geom/results split: %r\n\n' % table_name
                    msg += 'If you have matrices that you want to read, see:\n'
                    msg += '  model.set_additional_matrices(matrices)'
                    raise NotImplementedError(msg)

            table_name = self.read_table_name(rewind=True, stop_on_failure=False)
        return table_names

    def _read_matrix(self):
        print('----------------------------------------------------------------')
        table_name = self.read_table_name(rewind=False, stop_on_failure=True)
        print('table_name = %r' % table_name)
        self.read_markers([-1])
        data = self._read_record()
        matrix_num, form, Mrows, Ncols, tout, nvalues, g = unpack('7i', data)
        m = Matrix(table_name)
        self.matrices[table_name] = m

        # matrix_num is a counter (101, 102, 103, ...)
        # 101 will be the first matrix 'A' (matrix_num=101),
        # then we'll read a new matrix 'B' (matrix_num=102),
        # etc.
        #
        # the matrix is Mrows x Ncols
        #
        # it has nvalues in it
        #
        # tout is the precision of the matrix
        # 0 - set precision by cell
        # 1 - real, single precision (float32)
        # 2 - real, double precision (float64)
        # 3 - complex, single precision (complex64)
        # 4 - complex, double precision (complex128)

        # form (bad name)
        # 1 - column matrix
        # 2 - factor matrix
        # 3 - factor matrix

        assert matrix_num in [101, 102, 103, 104, 104, 105], matrix_num
        if matrix_num in [101, 102]:
            assert form == 2, form
            assert Mrows == 4, Mrows
            assert Ncols == 2, Ncols
            assert tout == 1, tout
            assert nvalues == 3, nvalues
            assert g == 6250, g
        elif matrix_num in [103, 104]:
            assert form == 2, form
            assert Mrows == 2, Mrows
            assert Ncols == 1, Ncols
            assert tout == 2, tout
            assert nvalues == 4, nvalues
            assert g == 10000, g
        elif matrix_num == 105:
            assert form == 1, form  # why is this one?
            assert Mrows == 36, Mrows
            assert Ncols == 2, Ncols
            assert tout == 1, tout
            assert nvalues == 36, nvalues  ## TODO: is this correct?
            assert g == 10000, g  ## TODO: what does this mean?
        else:
            vals = unpack('7i', data)
            msg = 'name=%r matrix_num=%s form=%s Mrows=%s Ncols=%s tout=%s nvalues=%s g=%s' % (
                table_name, matrix_num, form, Mrows, Ncols, tout, nvalues, g)
            raise NotImplementedError(msg)
        #self.show_data(data)
        #print('------------')
        self.read_markers([-2, 1, 0])
        data = self._read_record()
        name, a, b = unpack('8s 2i', data)
        assert a == 170, a
        assert b == 170, b

        #self.show_data(data)
        print('------------')
        itable = -3
        if 0:
            self.read_markers([itable, 1])
            one, = self.get_nmarkers(1, rewind=False)
            assert one == 1, one
            if one:
                nvalues, = self.get_nmarkers(1, rewind=False)
                print('nvalues =', nvalues)
                data = self.read_block()
                out = unpack('i %if' % nvalues, data)

                i = out[0]
                values = out[1:]
                if matrix_num in [101, 102]:
                    assert nvalues == 3, nvalues
                    assert i == 1, i
                    assert values[0] == 1.0, values
                    assert values[1] == 3.0, values
                    assert values[2] == 5.0, values
                elif matrix_num in [103, 104]:
                    assert nvalues == 4, nvalues
                    assert values[0] == 0.0, values
                    assert values[1] == 3.0234375, values
                    assert values[2] == 0.0, values
                    assert values[3] == 2.78125, values
                elif matrix_num == 105:
                    assert nvalues == 36, nvalues
                    values_expected = (
                        -1.0, 1.0, 1.0, -1.0, 1.0,
                        2.0, -1.0, 1.0, 3.0, -1.0, 1.0, 4.0, -1.0,
                        1.0, 5.0, -1.0, 1.0, 6.0, -1.0, 2.0, 1.0,
                        -1.0, 2.0, 2.0, -1.0, 2.0, 3.0, -1.0, 2.0,
                        4.0, -1.0, 2.0, 5.0, -1.0, 2.0, 6.0,)
                    assert len(values_expected) == 36
                    msg = 'values   = %s\n' % str(values)
                    msg += 'expected = %s' % str(values_expected)
                    assert values == values_expected, msg
                else:
                    raise NotImplementedError(matrix_num)
                itable -= 1
            else:
                asdf
            #a, data = unpack('i 3f', data)

        if 0:
            self.read_markers([itable, 1])
            one, = self.get_nmarkers(1, rewind=False)
            assert one == 1, 'itable=%s one=%s' % (itable, one)
            if one:
                nvalues, = self.get_nmarkers(1, rewind=False)
                #print('***')
                #print('nvalues =', nvalues)
                data = self.read_block()
                out = unpack('i %if' % nvalues, data)
                i = out[0]
                values = out[1:]
                print(i, values)

                if matrix_num in [101, 102]:
                    assert i == 2, i
                    assert values[0] == 6.0, b
                elif matrix_num in [103, 104]:
                    assert i == 1, i
                    assert values[0] == 0.0, values
                    assert values[1] == 2.78125, values
                    assert values[2] == 0.0, values
                    assert values[3] == 3.390625, values
                itable -= 1
            else:
                raise NotImplementedError(matrix_num)
        #self.show_data(data)

        #one, = self.get_nmarkers(1, rewind=False)
        #nvalues, = self.get_nmarkers(1, rewind=True)

        j = None
        while 1:
            #nvalues, = self.get_nmarkers(1, rewind=True)
            #print('nvalues4a =', nvalues)
            self.read_markers([itable, 1])
            one, = self.get_nmarkers(1, rewind=False)
            if one:
                nvalues, = self.get_nmarkers(1, rewind=True)
                while nvalues >= 0:
                    nvalues, = self.get_nmarkers(1, rewind=False)
                    data = self.read_block()
                    #self.show_data(data)

                    fmt = b'i %if' % nvalues
                    #print('***itable=%s nvalues=%s fmt=%r' % (itable, nvalues, fmt))

                    #print(len(data))
                    out = unpack(fmt, data)
                    i = out[0]
                    values = out[1:]
                    if matrix_num in [101, 102, 103, 104, 105]:
                        print('II=%s i=%s j=%s %s' % (abs(itable+2), i, j, values))
                        #print(i, values)
                        #assert i == 4, i
                        #assert values[0] == 8, values
                    else:
                        raise NotImplementedError(matrix_num)
                    nvalues, = self.get_nmarkers(1, rewind=True)
            else:
                nvalues, = self.get_nmarkers(1, rewind=False)
                assert nvalues == 0, nvalues
                print('nvalues =', nvalues)
                print('returning...')
                m.data = 1
                #nvalues, = self.get_nmarkers(1, rewind=True)
                #self.show(100)
                return
            itable -= 1
        #else:

        #self.show(30)
        #self.read_markers([0])
        #nvalues, = self.get_nmarkers(1, rewind=False)

        #print('nvalues5 =', nvalues)
        #if nvalues == 0:
            #return
        #else:
            #self.show(100)
            #asdf

        #self.show(50)
        #data = self.read_block()
        #self.read_markers([2])
        #data = self.read_block()
        #self.read_markers([-1])

        #data = b''
        #self.show(100)
        #for data in self._stream_record():
            #data = datai + data

        #data = self._read_record()
        print('------------')
        #self.show(100)

        #asdf

    def _skip_table(self, table_name):
        """bypasses the next table as quickly as possible"""
        if table_name in ['DIT']:  # tables
            self._read_dit()
        elif table_name in ['PCOMPTS']:
            self._read_pcompts()
        else:
            self._skip_table_helper()

    def _read_dit(self):
        """
        Reads the DIT table (poorly).
        The DIT table stores information about table cards (e.g. TABLED1, TABLEM1).
        """
        table_name = self.read_table_name(rewind=False)
        self.read_markers([-1])
        data = self._read_record()

        self.read_markers([-2, 1, 0])
        data = self._read_record()
        table_name, = unpack(b'8s', data)

        self.read_markers([-3, 1, 0])
        data = self._read_record()

        self.read_markers([-4, 1, 0])
        data = self._read_record()

        self.read_markers([-5, 1, 0])

        markers = self.get_nmarkers(1, rewind=True)
        if markers != [0]:
            data = self._read_record()
            self.read_markers([-6, 1, 0])

        markers = self.get_nmarkers(1, rewind=True)
        if markers != [0]:
            data = self._read_record()
            self.read_markers([-7, 1, 0])

        markers = self.get_nmarkers(1, rewind=True)
        if markers != [0]:
            data = self._read_record()
            self.read_markers([-8, 1, 0])

        markers = self.get_nmarkers(1, rewind=True)
        if markers != [0]:
            data = self._read_record()
            self.read_markers([-9, 1, 0])

        #self.show(100)
        self.read_markers([0])

    def _read_kelm(self):
        """
        .. todo:: this table follows a totally different pattern...
        The KELM table stores information about the K matrix???
        """
        self.log.debug("table_name = %r" % self.table_name)
        table_name = self.read_table_name(rewind=False)
        self.read_markers([-1])
        data = self._read_record()

        self.read_markers([-2, 1, 0])
        data = self._read_record()
        if len(data) == 16:  # KELM
            table_name, dummyA, dummyB = unpack(b'8sii', data)
            assert dummyA == 170, dummyA
            assert dummyB == 170, dummyB
        else:
            raise NotImplementedError(self.show_data(data))

        self.read_markers([-3, 1, 1])

        # data = read_record()
        for i in range(170//10):
            self.read_markers([2])
            data = self.read_block()
            #print "i=%s n=%s" % (i, self.n)

        self.read_markers([4])
        data = self.read_block()

        for i in range(7):
            self.read_markers([2])
            data = self.read_block()
            #print "i=%s n=%s" % (i, self.n)


        self.read_markers([-4, 1, 1])
        for i in range(170//10):
            self.read_markers([2])
            data = self.read_block()
            #print "i=%s n=%s" % (i, self.n)

        self.read_markers([4])
        data = self.read_block()

        for i in range(7):
            self.read_markers([2])
            data = self.read_block()
            #print "i=%s n=%s" % (i, self.n)

        self.read_markers([-5, 1, 1])
        self.read_markers([600])
        data = self.read_block()  # 604

        self.read_markers([-6, 1, 1])
        self.read_markers([188])
        data = self.read_block()

        self.read_markers([14])
        data = self.read_block()
        self.read_markers([16])
        data = self.read_block()
        self.read_markers([18])
        data = self.read_block()
        self.read_markers([84])
        data = self.read_block()
        self.read_markers([6])
        data = self.read_block()

        self.read_markers([-7, 1, 1])
        self.read_markers([342])
        data = self.read_block()

        self.read_markers([-8, 1, 1])
        data = self.read_block()
        data = self.read_block()
        while 1:
            n = self.get_nmarkers(1, rewind=True)[0]
            if n not in [2, 4, 6, 8]:
                #print "n =", n
                break
            n = self.get_nmarkers(1, rewind=False)[0]
            #print n
            data = self.read_block()


        i = -9
        while i != -13:
            n = self.get_nmarkers(1, rewind=True)[0]

            self.read_markers([i, 1, 1])
            while 1:
                n = self.get_nmarkers(1, rewind=True)[0]
                if n not in [2, 4, 6, 8]:
                    #print "n =", n
                    break
                n = self.get_nmarkers(1, rewind=False)[0]
                #print n
                data = self.read_block()
            i -= 1

        #print "n=%s" % (self.n)
        #strings, ints, floats = self.show(100)

    def _skip_pcompts(self):
        """
        Reads the PCOMPTS table (poorly).
        The PCOMPTS table stores information about the PCOMP cards???
        """
        self.log.debug("table_name = %r" % self.table_name)
        table_name = self.read_table_name(rewind=False)

        self.read_markers([-1])
        data = self._skip_record()

        self.read_markers([-2, 1, 0])
        data = self._skip_record()
        #table_name, = unpack(b'8s', data)
        #print "table_name = %r" % table_name

        self.read_markers([-3, 1, 0])
        markers = self.get_nmarkers(1, rewind=True)
        if markers != [-4]:
            data = self._skip_record()

        self.read_markers([-4, 1, 0])
        markers = self.get_nmarkers(1, rewind=True)
        if markers != [0]:
            data = self._skip_record()
        else:
            self.read_markers([0])
            return

        self.read_markers([-5, 1, 0])
        data = self._skip_record()

        self.read_markers([-6, 1, 0])
        self.read_markers([0])

    def _read_pcompts(self):
        """
        Reads the PCOMPTS table (poorly).
        The PCOMPTS table stores information about the PCOMP cards???
        """
        self._skip_pcompts()
        return
        #if self.read_mode == 1:
            #return
        #self.log.debug("table_name = %r" % self.table_name)
        #table_name = self.read_table_name(rewind=False)

        #self.read_markers([-1])
        #data = self._read_record()

        #self.read_markers([-2, 1, 0])
        #data = self._read_record()
        #table_name, = unpack(b'8s', data)
        ##print "table_name = %r" % table_name

        #self.read_markers([-3, 1, 0])
        #markers = self.get_nmarkers(1, rewind=True)
        #if markers != [-4]:
            #data = self._read_record()

        #self.read_markers([-4, 1, 0])
        #markers = self.get_nmarkers(1, rewind=True)
        #if markers != [0]:
            #data = self._read_record()
        #else:
            #self.read_markers([0])
            #return

        #self.read_markers([-5, 1, 0])
        #data = self._read_record()

        #self.read_markers([-6, 1, 0])
        #self.read_markers([0])

    def read_table_name(self, rewind=False, stop_on_failure=True):
        """Reads the next OP2 table name (e.g. OUG1, OES1X1)"""
        ni = self.n
        if stop_on_failure:
            data = self._read_record(debug=False)
            table_name, = unpack(b'8s', data)
            if self.debug:
                self.binary_debug.write('marker = [4, 2, 4]\n')
                self.binary_debug.write('table_header = [8, %r, 8]\n\n' % table_name)
            table_name = table_name.strip()
        else:
            try:
                data = self._read_record()
                table_name, = unpack(b'8s', data)
                table_name = table_name.strip()
            except:
                # we're done reading
                self.n = ni
                self.f.seek(self.n)

                try:
                    # we have a trailing 0 marker
                    self.read_markers([0])
                except:
                    # if we hit this block, we have a FATAL error
                    raise FatalError('last table=%r' % self.table_name)
                table_name = None

                # we're done reading, so we're going to ignore the rewind
                rewind = False

        if rewind:
            self.n = ni
            self.f.seek(self.n)
        return table_name

    def set_additional_matrices_to_read(self, matrices):
        """
        :param matrices: a dictionary of key=name, value=True/False,
                         where True/False indicates the matrix should be read

        .. note:: If you use an already defined table (e.g. OUGV1), it will be ignored.
                  If the table you requested doesn't exist, there will be no effect.
        """
        self.additional_matrices = matrices

    def _skip_table_helper(self):
        """
        Skips the majority of geometry/result tables as they follow a very standard format.
        Other tables don't follow this format.
        """
        self.table_name = self.read_table_name(rewind=False)
        if self.debug:
            self.binary_debug.write('skipping table...%r\n' % self.table_name)
        self.read_markers([-1])
        data = self._skip_record()
        self.read_markers([-2, 1, 0])
        data = self._skip_record()
        self._skip_subtables()

    def _read_omm2(self):
        """
        :param self:    the OP2 object pointer
        """
        self.log.debug("table_name = %r" % self.table_name)
        self.table_name = self.read_table_name(rewind=False)
        self.read_markers([-1])
        data = self._read_record()

        self.read_markers([-2, 1, 0])
        data = self._read_record()
        if len(data) == 28:
            subtable_name, month, day, year, zero, one = unpack(b'8s5i', data)
            if self.debug:
                self.binary_debug.write('  recordi = [%r, %i, %i, %i, %i, %i]\n'  % (subtable_name, month, day, year, zero, one))
                self.binary_debug.write('  subtable_name=%r\n' % subtable_name)
            self._print_month(month, day, year, zero, one)
        else:
            raise NotImplementedError(self.show_data(data))
        self._read_subtables()

    def _read_fol(self):
        """
        :param self:    the OP2 object pointer
        """
        self.log.debug("table_name = %r" % self.table_name)
        self.table_name = self.read_table_name(rewind=False)
        self.read_markers([-1])
        data = self._read_record()

        self.read_markers([-2, 1, 0])
        data = self._read_record()
        if len(data) == 12:
            subtable_name, double = unpack(b'8sf', data)
            if self.debug:
                self.binary_debug.write('  recordi = [%r, %f]\n'  % (subtable_name, double))
                self.binary_debug.write('  subtable_name=%r\n' % subtable_name)
        else:
            strings, ints, floats = self.show_data(data)
            msg = 'len(data) = %i\n' % len(data)
            msg += 'strings  = %r\n' % strings
            msg += 'ints     = %r\n' % str(ints)
            msg += 'floats   = %r' % str(floats)
            raise NotImplementedError(msg)
        self._read_subtables()

    def _read_gpl(self):
        """
        :param self:    the OP2 object pointer
        """
        self.table_name = self.read_table_name(rewind=False)
        self.log.debug('table_name = %r' % self.table_name)
        if self.debug:
            self.binary_debug.write('_read_geom_table - %s\n' % self.table_name)
        self.read_markers([-1])
        if self.debug:
            self.binary_debug.write('---markers = [-1]---\n')
        data = self._read_record()

        markers = self.get_nmarkers(1, rewind=True)
        self.binary_debug.write('---marker0 = %s---\n' % markers)
        n = -2
        while markers[0] != 0:
            self.read_markers([n, 1, 0])
            if self.debug:
                self.binary_debug.write('---markers = [%i, 1, 0]---\n' % n)

            markers = self.get_nmarkers(1, rewind=True)
            if markers[0] == 0:
                markers = self.get_nmarkers(1, rewind=False)
                break
            data = self._read_record()
            #self.show_data(data, 'i')
            n -= 1
            markers = self.get_nmarkers(1, rewind=True)

    def _read_meff(self):
        """
        :param self:    the OP2 object pointer
        """
        self.table_name = self.read_table_name(rewind=False)
        self.log.debug('table_name = %r' % self.table_name)
        if self.debug:
            self.binary_debug.write('_read_geom_table - %s\n' % self.table_name)
        self.read_markers([-1])
        if self.debug:
            self.binary_debug.write('---markers = [-1]---\n')
        data = self._read_record()

        markers = self.get_nmarkers(1, rewind=True)
        self.binary_debug.write('---marker0 = %s---\n' % markers)
        self.read_markers([-2, 1, 0])
        data = self._read_record()

        for n in [-3, -4, -5, -6, -7, -8, ]:
            self.read_markers([n, 1, 1])
            markers = self.get_nmarkers(1, rewind=False)
            #print('markers =', markers)
            nbytes = markers[0]*4 + 12
            data = self.f.read(nbytes)
            self.n += nbytes

        n = -9
        self.read_markers([n, 1, 0, 0])
        #data = self._read_record()

        #self.table_name = self.read_table_name(rewind=False)
        #self.log.info('table_name2 = %r' % self.table_name)

        #self.show(50)
        #raise NotImplementedError(self.table_name)

    def _read_intmod(self):
        """reads the INTMOD table"""
        self.table_name = self.read_table_name(rewind=False)
        #self.log.debug('table_name = %r' % self.table_name)
        if self.debug:
            self.binary_debug.write('_read_geom_table - %s\n' % self.table_name)
        self.read_markers([-1])
        if self.debug:
            self.binary_debug.write('---markers = [-1]---\n')
        data = self._read_record()
        #print('intmod data1')
        #self.show_data(data)

        markers = self.get_nmarkers(1, rewind=True)
        self.binary_debug.write('---marker0 = %s---\n' % markers)
        self.read_markers([-2, 1, 0])
        data = self._read_record()
        #print('intmod data2')
        #self.show_data(data)

        for n in [-3, -4, -5, -6, -7, -8,]:
            self.read_markers([n, 1, 1])
            markers = self.get_nmarkers(1, rewind=False)
            #print('markers =', markers)
            nbytes = markers[0]*4 + 12
            data = self.f.read(nbytes)
            #print('intmod data%i' % n)
            #self.show_data(data)
            self.n += nbytes

        n = -9
        self.read_markers([n, 1, 0, 0])
        #self.show(50)
        #raise NotImplementedError(self.table_name)


    def _read_hisadd(self):
        """preliminary reader for the HISADD table"""
        self.table_name = self.read_table_name(rewind=False)
        #self.log.debug('table_name = %r' % self.table_name)
        if self.debug:
            self.binary_debug.write('_read_geom_table - %s\n' % self.table_name)
        self.read_markers([-1])
        if self.debug:
            self.binary_debug.write('---markers = [-1]---\n')
        data = self._read_record()
        #print('hisadd data1')
        self.show_data(data)

        markers = self.get_nmarkers(1, rewind=True)
        self.binary_debug.write('---marker0 = %s---\n' % markers)
        self.read_markers([-2, 1, 0])
        data = self._read_record()
        print('hisadd data2')
        self.show_data(data)

        self.read_markers([-3, 1, 0])
        markers = self.get_nmarkers(1, rewind=False)
        print('markers =', markers)
        nbytes = markers[0]*4 + 12
        data = self.f.read(nbytes)
        self.n += nbytes
        self.show_data(data[4:-4])
        #self.show(100)
        datai = data[:-4]

        irec = data[:32]
        design_iter, iconvergence, conv_result, obj_intial, obj_final, constraint_max, row_constraint_max, desvar_value = unpack(b'3i3fif', irec)
        if iconvergence == 1:
            iconvergence = 'soft'
        elif iconvergence == 2:
            iconvergence = 'hard'

        if conv_result == 0:
            conv_result = 'no'
        elif conv_result == 1:
            conv_result = 'soft'
        elif conv_result == 2:
            conv_result = 'hard'

        print('design_iter=%s iconvergence=%s conv_result=%s obj_intial=%s obj_final=%s constraint_max=%s row_constraint_max=%s desvar_value=%s' % (design_iter, iconvergence, conv_result, obj_intial, obj_final, constraint_max, row_constraint_max, desvar_value))
        self.show_data(datai[32:])
        raise NotImplementedError()
        #for n in [-3, -4, -5, -6, -7, -8,]:
            #self.read_markers([n, 1, 1])
            #markers = self.get_nmarkers(1, rewind=False)
            ##print('markers =', markers)
            #nbytes = markers[0]*4 + 12
            #data = self.f.read(nbytes)
            ##print('intmod data%i' % n)
            ##self.show_data(data)
            #self.n += nbytes

        #n = -9
        #self.read_markers([n, 1, 0, 0])

    def get_marker_n(self, nmarkers):
        """
        Gets N markers

        A marker is a flag that is used.  It's a series of 3 ints (4, n, 4)
        where n changes from marker to marker.

        :param nmarkers:  the number of markers to read
        :returns markers:  a list of nmarker integers
        """
        markers = []
        s = Struct('3i')
        for i in range(nmarkers):
            block = self.f.read(12)
            marker = s.unpack(block)
            markers.append(marker)
        return markers

    def _read_geom_table(self):
        """
        Reads a geometry table

        :param self:  the OP2 object pointer
        """
        self.table_name = self.read_table_name(rewind=False)
        if self.debug:
            self.binary_debug.write('_read_geom_table - %s\n' % self.table_name)
        self.read_markers([-1])
        data = self._read_record()

        self.read_markers([-2, 1, 0])
        data = self._read_record()
        if len(data) == 8:
            table_name, = unpack(b'8s', data)
        else:
            strings, ints, floats = self.show_data(data)
            msg = 'len(data) = %i\n' % len(data)
            msg += 'strings  = %r\n' % strings
            msg += 'ints     = %r\n' % str(ints)
            msg += 'floats   = %r' % str(floats)
            raise NotImplementedError(msg)
        self._read_subtables()

    def _read_sdf(self):
        """
        :param self:    the OP2 object pointer
        """
        self.log.debug("table_name = %r" % self.table_name)
        self.table_name = self.read_table_name(rewind=False)
        self.read_markers([-1])
        data = self._read_record()

        self.read_markers([-2, 1, 0])
        data = self._read_record()
        if len(data) == 16:
            subtable_name, dummyA, dummyB = unpack(b'8sii', data)
            if self.debug:
                self.binary_debug.write('  recordi = [%r, %i, %i]\n'  % (subtable_name, dummyA, dummyB))
                self.binary_debug.write('  subtable_name=%r\n' % subtable_name)
                assert dummyA == 170, dummyA
                assert dummyB == 170, dummyB
        else:
            strings, ints, floats = self.show_data(data)
            msg = 'len(data) = %i\n' % len(data)
            msg += 'strings  = %r\n' % strings
            msg += 'ints     = %r\n' % str(ints)
            msg += 'floats   = %r' % str(floats)
            raise NotImplementedError(msg)

        self.read_markers([-3, 1, 1])

        markers0 = self.get_nmarkers(1, rewind=False)
        record = self.read_block()

        #data = self._read_record()
        self.read_markers([-4, 1, 0, 0])
        #self._read_subtables()

    def _read_results_table(self):
        """
        Reads a results table
        """
        if self.debug:
            self.binary_debug.write('read_results_table - %s\n' % self.table_name)
        self.table_name = self.read_table_name(rewind=False)
        self.read_markers([-1])
        if self.debug:
            self.binary_debug.write('---markers = [-1]---\n')
            #self.binary_debug.write('marker = [4, -1, 4]\n')
        data = self._read_record()

        self.read_markers([-2, 1, 0])
        if self.debug:
            self.binary_debug.write('---markers = [-2, 1, 0]---\n')
        data = self._read_record()
        if len(data) == 8:
            subtable_name = unpack(b'8s', data)
            if self.debug:
                self.binary_debug.write('  recordi = [%r]\n'  % subtable_name)
                self.binary_debug.write('  subtable_name=%r\n' % subtable_name)
        elif len(data) == 28:
            subtable_name, month, day, year, zero, one = unpack(b'8s5i', data)
            if self.debug:
                self.binary_debug.write('  recordi = [%r, %i, %i, %i, %i, %i]\n'  % (subtable_name, month, day, year, zero, one))
                self.binary_debug.write('  subtable_name=%r\n' % subtable_name)
            self._print_month(month, day, year, zero, one)
        else:
            strings, ints, floats = self.show_data(data)
            msg = 'len(data) = %i\n' % len(data)
            msg += 'strings  = %r\n' % strings
            msg += 'ints     = %r\n' % str(ints)
            msg += 'floats   = %r' % str(floats)
            raise NotImplementedError(msg)
        self._read_subtables()

    def _print_month(self, month, day, year, zero, one):
        """
        Creates the self.date attribute from the 2-digit year.

        :param month: the month (integer <= 12)
        :param day:  the day (integer <= 31)
        :param year: the day (integer <= 99)
        :param zero: a dummy integer (???)
        :param one:  a dummy integer (???)
        """
        month, day, year = self._set_op2_date(month, day, year)

        #self.log.debug("%s/%s/%4i zero=%s one=%s" % (month, day, year, zero, one))
        #if self.debug:
        self.binary_debug.write('  [subtable_name, month=%i, day=%i, year=%i, zero=%i, one=%i]\n\n' % (month, day, year, zero, one))
        #assert zero == 0  # is this the RTABLE indicator???
        assert one == 1

    def finish(self):
        """
        Clears out the data members contained within the self.words variable.
        This prevents mixups when working on the next table, but otherwise
        has no effect.
        """
        for word in self.words:
            if word != '???' and hasattr(self, word):
                if word not in ['Title', 'reference_point']:
                    delattr(self, word)
        self.obj = None


class Matrix(object):
    def __init__(self, name):
        self.name = name
        self.data = None


def main():
    """testing pickling"""
    from pickle import dumps, dump, load, loads
    txt_filename = 'solid_shell_bar.txt'
    f = open(txt_filename, 'wb')
    op2_filename = 'solid_shell_bar.op2'
    op2 = OP2_Scalar()
    op2.read_op2(op2_filename)
    print(op2.displacements[1])
    dump(op2, f)
    f.close()

    f = open(txt_filename, 'r')
    op2 = load(f)
    f.close()
    print(op2.displacements[1])


    #import sys
    #op2_filename = sys.argv[1]

    #o = OP2_Scalar()
    #o.read_op2(op2_filename)
    #(model, ext) = os.path.splitext(op2_filename)
    #f06_outname = model + '.test_op2.f06'
    #o.write_f06(f06_outname)


if __name__ == '__main__':  # pragma: no conver
    main()
