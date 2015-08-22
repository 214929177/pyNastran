from __future__ import print_function
from six import iteritems
from pyNastran.utils.log import get_logger


class GeometryProperty(object):
    def __init__(self):
        pass
    def SetRepresentationToPoints(self):
        pass
    def SetPointSize(self, size):
        assert isinstance(size, int), type(size)


class GeometryActor(object):
    def __init__(self):
        self._prop = GeometryProperty()
    def GetProperty(self):
        return self._prop
    def VisibilityOn(self):
        pass
    def VisibilityOff(self):
        pass
    def Modified(self):
        pass


class Grid(object):
    def Reset(self):
        pass
    def Allocate(self, nelements, delta):
        pass
    def InsertNextCell(self, *cell):
        pass
    def SetPoints(self, *cell):
        pass
    def Modified(self):
        pass
    def Update(self):
        pass


class ScalarBar(object):
    def VisibilityOff(self):
        pass
    def VisibilityOn(self):
        pass
    def Modified(self):
        pass


class GUIMethods(object):
    def __init__(self):
        self.debug = False
        self.form = []
        self.result_cases = {}
        self._finish_results_io = self.passer1
        self._finish_results_io2 = self.passer2
        self.geometry_actors = {
            'main' : GeometryActor(),
        }
        self.grid = Grid()
        self.scalarBar = ScalarBar()
        self.alt_geometry_actor = ScalarBar()
        self.alt_grids = {
            'main' : self.grid,
            'caero' : Grid(),
            'caero_sub' : Grid(),
        }
        self.geometry_properties = {
            #'main' : None,
            #'caero' : None,
            #'caero_sub' : None,
        }
        #self._add_alt_actors = _add_alt_actors

        level = 'debug' if self.debug else 'info'
        self.log = get_logger(log=None, level=level)

    def removeOldGeometry(self, filename):
        skip_reading = False
        return skip_reading
    def cycleResults(self):
        pass
    def TurnTextOn(self):
        pass
    def TurnTextOff(self):
        pass
    def update_axes_length(self, value):
        pass
    def passer(self):
        pass
    def passer1(self, a):
        pass
    def passer2(self, a, b):
        pass
    def create_alternate_vtk_grid(self, name, color=None, line_width=None, opacity=None):
        self.alt_grids[name] = Grid()
    def _add_alt_actors(self, alt_grids):
        for name, grid in iteritems(alt_grids):
            self.geometry_actors[name] = GeometryActor()
    def log_info(self, msg):
        if self.debug:
            print('INFO:  ', msg)

    def log_error(self, msg):
        if self.debug:
            print('ERROR:  ', msg)

    #test.log_error = log_error
    #test.log_info = print
    #test.log_info = log_info
    #test.cycleResults = cycleResults
    #test.TurnTextOn = TurnTextOn
    #test.TurnTextOff = TurnTextOff
    #test.update_axes_length = update_axes_length
    #test.cycleResults_explicit = passer

