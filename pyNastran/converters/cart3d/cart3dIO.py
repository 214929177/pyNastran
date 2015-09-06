from __future__ import print_function
from six import iteritems
from six.moves import range

import os
from numpy import arange, mean, amax, amin, vstack, zeros, unique, where

import vtk
from vtk import vtkTriangle, vtkHexahedron

from pyNastran.gui.qt_files.result import Result
from pyNastran.converters.cart3d.cart3d_reader import Cart3DReader
from pyNastran.converters.cart3d.input_c3d_reader import InputC3dReader
from pyNastran.converters.cart3d.input_cntl_reader import InputCntlReader

class Cart3dGeometry(Result):
    def __init__(self, nodes, elements, regions, uname='Cart3dGeometry', labels=None):
        self.uname = uname
        self.n = 2
        self.nodes = nodes # 0
        self.elements = elements # 1
        self.regions = regions # 2
        self.labels = labels
        self.data_formats = ['%i', '%i', '%i']
        self.titles = ['NodeID', 'ElementID', 'Region']


    def get_methods(self, i):
        if i == 1:
            return ['centroid']
        return ['node']

    def get_data(self, i, method):
        print('method = %r' % method)
        ii, name = i
        if name == 'NodeID':
            return self.nodes
        elif name == 'ElementID':
            return self.elements
        elif name == 'Region':
            return self.regions
        raise NotImplementedError('i=%s' % str(i))

    def __repr__(self):
        msg = 'Cart3dGeometry\n'
        msg += '    uname=%r\n' % self.uname
        msg += '    n=%r' % self.n
        return msg


class Cart3dResult(Result):
    def __init__(self, rho, rhoU, rhoV, rhoW, rhoE, uname='Cart3dResult', labels=None):
        self.uname = uname
        self.labels = labels
        self.n = 5
        #Result.__init__(self)
        self.rho = rho # 0
        self.rhoU = rhoU # 1
        self.rhoV = rhoV # 2
        self.rhoW = rhoW # 3
        self.rhoE = rhoE # 4
        self.data_formats = ['%.3g', '%.3g', '%.3g', '%.3g', '%.3g']
        self.titles = ['rho', 'rhoU' 'rhoV', 'rhoW', 'rhoE']

    def get_methods(self, i):
        return ['node']

    def get_data(self, i, method):
        print('method = %r' % method)
        ii, name = i
        if name == 'rho':
            return self.rho
        elif name == 'rhoU':
            return self.rhoU
        elif name == 'rhoV':
            return self.rhoV
        elif name == 'rhoW':
            return self.rhoW
        elif name == 'rhoE':
            return self.rhoE
        raise NotImplementedError('i=%s' % i)

    def __repr__(self):
        msg = 'Cart3dResult\n'
        msg += '  i | Title\n'
        msg += '----+----------\n'
        #msg += '  0 | NodeID\n'
        #msg += '  1 | ElementID\n'
        msg += '  0 | Rho\n'
        msg += '  1 | RhoU\n'
        msg += '  2 | RhoV\n'
        msg += '  3 | RhoW\n'
        msg += '  4 | RhoE\n'
        msg += '----+----------\n'
        return msg


class Cart3dIO(object):
    def __init__(self):
        pass

    def get_cart3d_wildcard_geometry_results_functions(self):
        data = ('Cart3d',
                'Cart3d (*.tri; *.triq)', self.load_cart3d_geometry,
                'Cart3d (*.triq)', self.load_cart3d_results)
        return data

    def removeOldGeometry(self, filename):
        self._remove_old_cart3d_geometry(filename)

    def _remove_old_cart3d_geometry(self, filename):
        self.eidMap = {}
        self.nidMap = {}
        if filename is None:
            #self.emptyResult = vtk.vtkFloatArray()
            #self.vectorResult = vtk.vtkFloatArray()
            self.scalarBar.VisibilityOff()
            skip_reading = True
        else:
            self.TurnTextOff()
            self.grid.Reset()
            #self.gridResult.Reset()
            #self.gridResult.Modified()

            self.result_cases = {}
            self.nCases = 0
            try:
                del self.caseKeys
                del self.iCase
                del self.iSubcaseNameMap
            except:
                print("cant delete geo")
                pass

            #print(dir(self))
            skip_reading = False
        #self.scalarBar.VisibilityOff()
        self.scalarBar.Modified()
        return skip_reading

    def load_cart3d_geometry(self, cart3d_filename, dirname, plot=True):
        #key = self.caseKeys[self.iCase]
        #case = self.resultCases[key]

        skip_reading = self._remove_old_cart3d_geometry(cart3d_filename)
        if skip_reading:
            return

        model = Cart3DReader(log=self.log, debug=False)
        self.modelType = 'cart3d'
        #self.modelType = model.modelType
        (nodes, elements, regions, loads) = model.read_cart3d(cart3d_filename)
        self.nNodes = model.nPoints
        self.nElements = model.nElementsRead

        #print("nNodes = ",self.nNodes)
        #print("nElements = ", self.nElements)

        self.grid.Allocate(self.nElements, 1000)
        #self.gridResult.SetNumberOfComponents(self.nElements)

        points = vtk.vtkPoints()
        points.SetNumberOfPoints(self.nNodes)
        #self.gridResult.Allocate(self.nNodes, 1000)
        #vectorReselt.SetNumberOfComponents(3)
        self.nidMap = {}
        #elem.SetNumberOfPoints(nNodes)
        if 0:
            fraction = 1. / self.nNodes  # so you can color the nodes by ID
            for nid, node in sorted(iteritems(nodes)):
                points.InsertPoint(nid - 1, *node)
                self.gridResult.InsertNextValue(nid * fraction)
                #print(str(element))

                #elem = vtk.vtkVertex()
                #elem.GetPointIds().SetId(0, i)
                #self.aQuadGrid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())
                #vectorResult.InsertTuple3(0, 0.0, 0.0, 1.0)

        assert nodes is not None
        nnodes = nodes.shape[0]

        nid = 0
        #print("nnodes=%s" % nnodes)
        mmax = amax(nodes, axis=0)
        mmin = amin(nodes, axis=0)
        dim_max = (mmax - mmin).max()
        self.update_axes_length(dim_max)

        for i in range(nnodes):
            points.InsertPoint(nid, nodes[i, :])
            nid += 1

        nelements = elements.shape[0]
        elements -= 1
        for eid in range(nelements):
            elem = vtkTriangle()
            node_ids = elements[eid, :]
            elem.GetPointIds().SetId(0, node_ids[0])
            elem.GetPointIds().SetId(1, node_ids[1])
            elem.GetPointIds().SetId(2, node_ids[2])
            self.grid.InsertNextCell(5, elem.GetPointIds())  #elem.GetCellType() = 5  # vtkTriangle

        self.grid.SetPoints(points)
        #self.grid.GetPointData().SetScalars(self.gridResult)
        #print(dir(self.grid) #.SetNumberOfComponents(0))
        #self.grid.GetCellData().SetNumberOfTuples(1);
        #self.grid.GetCellData().SetScalars(self.gridResult)
        self.grid.Modified()
        if hasattr(self.grid, 'Update'):
            self.grid.Update()

        self._create_cart3d_free_edegs(model, nodes, elements)


        # loadCart3dResults - regions/loads
        self.TurnTextOn()
        self.scalarBar.VisibilityOn()
        self.scalarBar.Modified()

        assert loads is not None
        if 'Mach' in loads:
            avgMach = mean(loads['Mach'])
            note = ':  avg(Mach)=%g' % avgMach
        else:
            note = ''
        self.iSubcaseNameMap = {1: ['Cart3d%s' % note, '']}
        cases = {}
        ID = 1

        form, cases, icase = self._fill_cart3d_case(cases, ID, nodes, elements, regions, loads, model)
        self._create_box(cart3d_filename, ID, form, cases, icase, regions)
        self._finish_results_io2(form, cases)

    def _create_box(self, cart3d_filename, ID, form, cases, icase, regions):
        stack = True
        dirname = os.path.dirname(os.path.abspath(cart3d_filename))
        input_c3d_filename = os.path.join(dirname, 'input.c3d')
        input_cntl_filename = os.path.join(dirname, 'input.cntl')
        if os.path.exists(input_cntl_filename):
            cntl = InputCntlReader()
            cntl.read_input_cntl(input_cntl_filename)
            bcs = cntl.get_boundary_conditions()
            bc_xmin, bc_xmax, bc_ymin, bc_ymax, bc_xmin, bc_xmax, surfbcs = bcs
            stack = False

            if surfbcs:
                bc_form = [
                    ('Rho', icase, []),
                    ('xVelocity', icase + 1, []),
                    ('yVelocity', icase + 2, []),
                    ('zVelocity', icase + 3, []),
                    ('Pressure', icase + 4, []),
                ]
                icase += 5
                nelements = self.nElements
                rho = zeros(nelements, dtype='float32')
                xvel = zeros(nelements, dtype='float32')
                yvel = zeros(nelements, dtype='float32')
                zvel = zeros(nelements, dtype='float32')
                pressure = zeros(nelements, dtype='float32')

                uregions = set(unique(regions))
                surf_bc_regions = set(surfbcs.keys())
                invalid_regions = surf_bc_regions - uregions
                if len(invalid_regions) != 0:
                    assert len(invalid_regions) == 0, invalid_regions

                for bc_id, bc_values in sorted(iteritems(surfbcs)):
                    rhoi, xveli, yveli, zveli, pressi = bc_values
                    i = where(regions == bc_id)[0]
                    rho[i] = rhoi
                    xvel[i] = xveli
                    yvel[i] = yveli
                    zvel[i] = zveli
                    pressure[i] = pressi
                cases[(ID, icase, 'Rho', 1, 'centroid', '%.3f')] = rho
                cases[(ID, icase + 1, 'xVelocity', 1, 'centroid', '%.3f')] = xvel
                cases[(ID, icase + 2, 'yVelocity', 1, 'centroid', '%.3f')] = yvel
                cases[(ID, icase + 3, 'zVelocity', 1, 'centroid', '%.3f')] = zvel
                cases[(ID, icase + 4, 'Pressure', 1, 'centroid', '%.3f')] = pressure
                form.append(('Boundary Conditions', None, bc_form))


        if os.path.exists(input_c3d_filename):
            c3d = InputC3dReader()
            nodes, elements = c3d.read_input_c3d(input_c3d_filename, stack=stack)

            # Planes
            # ----------
            # xmin, xmax
            # ymin, ymax
            # zmin, zmax

            if stack:
                red = (1., 0., 0.)
                color = red
                self.set_quad_grid('box', nodes, elements, color, line_width=1, opacity=1.)
            else:
                red = (1., 0., 0.)
                inflow_nodes = []
                inflow_elements = []

                green = (0., 1., 0.)
                symmetry_nodes = []
                symmetry_elements = []

                colori = (1., 1., 0.)
                outflow_nodes = []
                outflow_elements = []

                blue = (0., 0., 1.)
                farfield_nodes = []
                farfield_elements = []

                ifarfield = 0
                isymmetry = 0
                iinflow = 0
                ioutflow = 0

                nfarfield_nodes = 0
                nsymmetry_nodes = 0
                ninflow_nodes = 0
                noutflow_nodes = 0
                for bc, nodesi, elementsi in zip(bcs, nodes, elements):
                    # 0 = FAR FIELD
                    # 1 = SYMMETRY
                    # 2 = INFLOW  (specify all)
                    # 3 = OUTFLOW (simple extrap)
                    print('bc =', bc)
                    nnodes = nodesi.shape[0]
                    if bc == 0:
                        farfield_nodes.append(nodesi)
                        farfield_elements.append(elementsi + nfarfield_nodes)
                        nfarfield_nodes += nnodes
                        ifarfield += 1
                    elif bc == 1:
                        symmetry_nodes.append(nodesi)
                        symmetry_elements.append(elementsi + nsymmetry_nodes)
                        nsymmetry_nodes += nnodes
                        isymmetry += 1
                    elif bc == 2:
                        inflow_nodes.append(nodesi)
                        inflow_elements.append(elementsi + ninflow_nodes)
                        ninflow_nodes += nnodes
                        iinflow += 1
                    elif bc == 3:
                        outflow_nodes.append(nodesi)
                        outflow_elements.append(elementsi + noutflow_nodes)
                        noutflow_nodes += nnodes
                        ioutflow += 1
                    else:
                        raise NotImplementedError(bc)

                if ifarfield:
                    color = blue
                    nodes = vstack(farfield_nodes)
                    elements = vstack(farfield_elements)
                    self.set_quad_grid('farfield', nodes, elements, color, line_width=1, opacity=1.)

                if isymmetry:
                    color = green
                    nodes = vstack(symmetry_nodes)
                    elements = vstack(symmetry_elements)
                    self.set_quad_grid('symmetry', nodes, elements, color, line_width=1, opacity=1.)

                if iinflow:
                    color = red
                    nodes = vstack(inflow_nodes)
                    elements = vstack(inflow_elements)
                    self.set_quad_grid('inflow', nodes, elements, color, line_width=1, opacity=1.)

                if ioutflow:
                    color = colori
                    nodes = vstack(outflow_nodes)
                    elements = vstack(outflow_elements)
                    self.set_quad_grid('outflow', nodes, elements, color, line_width=1, opacity=1.)

                #i = 0
                #for nodesi, elementsi in zip(nodes, elements):
                    #self.set_quad_grid('box_%i' % i, nodesi, elementsi, color, line_width=1, opacity=1.)
                    #i += 1

    def _create_cart3d_free_edegs(self, model, nodes, elements):
        free_edges = model.get_free_edges(elements)
        nfree_edges = len(free_edges)
        if nfree_edges:
            # yellow = (1., 1., 0.)
            pink = (0.98, 0.4, 0.93)
            npoints = 2 * nfree_edges
            if 'free_edges' not in self.alt_grids:
                self.create_alternate_vtk_grid('free_edges', color=pink, line_width=3, opacity=1.0)

            j = 0
            points = vtk.vtkPoints()
            points.SetNumberOfPoints(npoints)

            self.alt_grids['free_edges'].Allocate(nfree_edges, 1000)

            elem = vtk.vtkLine()
            # elem.GetPointIds().SetId(0, nidMap[nodeIDs[0]])
            # elem.GetPointIds().SetId(1, nidMap[nodeIDs[1]])

            eType = vtk.vtkLine().GetCellType()
            for free_edge in free_edges:
                # (p1, p2) = free_edge
                for ipoint, node_id in enumerate(free_edge):
                    point = nodes[node_id, :]
                    points.InsertPoint(j + ipoint, *point)

                elem = vtk.vtkLine()
                elem.GetPointIds().SetId(0, j)
                elem.GetPointIds().SetId(1, j + 1)
                self.alt_grids['free_edges'].InsertNextCell(eType, elem.GetPointIds())
                j += 2
            self.alt_grids['free_edges'].SetPoints(points)

        else:
            # TODO: clear free edges
            pass

        if 'free_edges' in self.alt_grids:
            self._add_alt_actors(self.alt_grids)
            self.geometry_actors['free_edges'].Modified()
            if hasattr(self.geometry_actors['free_edges'], 'Update'):
                self.geometry_actors['free_edges'].Update()


    def clear_cart3d(self):
        pass

    def load_cart3d_results(self, cart3d_filename, dirname):
        model = Cart3DReader(log=self.log, debug=False)
        self.load_cart3d_geometry(cart3d_filename, dirname)

    def _fill_cart3d_case2(self, cases, ID, nodes, elements, regions, loads, model):
        print('_fill_cart3d_case2')
        nelements = elements.shape[0]
        nnodes = nodes.shape[0]

        eids = arange(1, nelements + 1)
        nids = arange(1, nnodes + 1)
        cart3d_geo = Cart3dGeometry(nids, eids, regions, uname='Cart3dGeometry', labels=None)
        cases = {
            0 : (cart3d_geo, (0, 'NodeID')),
            1 : (cart3d_geo, (0, 'ElementID')),
            2 : (cart3d_geo, (0, 'Region')),
        }
        geometry_form = [
            ('NodeID', 0, []),
            ('ElementID', 1, []),
            ('Region', 2, []),
        ]

        form = [
            ('Geometry', None, geometry_form),
        ]
        return form, cases

    def _fill_cart3d_case(self, cases, ID, nodes, elements, regions, loads, model):
        result_names = ['Cp', 'Mach', 'U', 'V', 'W', 'E', 'rho',
                        'rhoU', 'rhoV', 'rhoW', 'rhoE']
        nelements = elements.shape[0]
        nnodes = nodes.shape[0]

        cases_new = []
        new = False
        is_normals = True

        results_form = []
        geometry_form = [
            ('NodeID', 0, []),
            ('ElementID', 1, []),
            ('Region', 2, []),
        ]

        eids = arange(1, nelements + 1)
        nids = arange(1, nnodes + 1)

        if new:
            cases_new[0] = (ID, nids, 'NodeID', 'node', '%i')
            cases_new[1] = (ID, eids, 'ElementID', 'centroid', '%i')
            cases_new[2] = (ID, regions, 'Region', 'centroid', '%i')
        else:
            cases[(ID, 0, 'NodeID', 1, 'node', '%i')] = nids
            cases[(ID, 1, 'ElementID', 1, 'centroid', '%i')] = eids
            cases[(ID, 2, 'Region', 1, 'centroid', '%i')] = regions

        i = 3

        if is_normals:
            geometry_form.append(('Normal X', i, []))
            geometry_form.append(('Normal Y', i + 1, []))
            geometry_form.append(('Normal Z', i + 2, []))

            cnormals = model.get_normals(nodes, elements, shift_nodes=False)
            cnnodes = cnormals.shape[0]
            assert cnnodes == nelements, len(cnnodes)

            if new:
                cases_new[i] = (ID, cnormals[:, 0], 'Normal X', 'centroid', '%.3f')
                cases_new[i + 1] = (ID, cnormals[:, 1], 'Normal Y', 'centroid', '%.3f')
                cases_new[i + 2] = (ID, cnormals[:, 2], 'Normal Z', 'centroid', '%.3f')
            else:
                cases[(ID, i, 'Normal X', 1, 'centroid', '%.3f')] = cnormals[:, 0]
                cases[(ID, i + 1, 'Normal Y', 1, 'centroid', '%.3f')] = cnormals[:, 1]
                cases[(ID, i + 2, 'Normal Z', 1, 'centroid', '%.3f')] = cnormals[:, 2]
            i += 3

        #if is_normals:
            #geometry_form.append(('Normal X', 1, []))
            #geometry_form.append(('Normal Y', 2, []))
            #geometry_form.append(('Normal Z', 3, []))

            #cnormals = model.get_normals(nodes, elements, shift_nodes=False)
            #nnormals = model.get_normals_at_nodes(nodes, elements, cnormals, shift_nodes=False)

            #if new:
                #cases_new[i] = (ID, nnormals[:, 0], 'Normal X', 'node', '%.3f')
                #cases_new[i + 1] = (ID, nnormals[:, 1], 'Normal Y', 'node', '%.3f')
                #cases_new[i + 2] = (ID, nnormals[:, 2], 'Normal Z', 'node', '%.3f')
            #else:
                #cases[(ID, i, 'Normal X', 1, 'node', '%.3f')] = nnormals[:, 0]
                #cases[(ID, i + 1, 'Normal Y', 1, 'node', '%.3f')] = nnormals[:, 1]
                #cases[(ID, i + 2, 'Normal Z', 1, 'node', '%.3f')] = nnormals[:, 2]
            #i += 3

        for result_name in result_names:
            if result_name in loads:
                nodal_data = loads[result_name]
                if new:
                    cases_new[i] = (result, result_name, 1, 'node', '%.3f')
                else:
                    cases[(ID, i, result_name, 1, 'node', '%.3f')] = nodal_data
                results_form.append((result_name, i, []))
                i += 1

        form = [
            ('Geometry', None, geometry_form),
        ]
        if len(results_form):
            form.append(('Results', None, results_form))
        return form, cases, i