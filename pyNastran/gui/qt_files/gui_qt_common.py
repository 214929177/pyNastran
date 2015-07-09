# -*- coding: utf-8 -*-
# pylint: disable=C0111
from __future__ import print_function
from six import iteritems
from copy import deepcopy

from numpy import ndarray, asarray, hstack, searchsorted, ones, full
import vtk
from vtk.util.numpy_support import numpy_to_vtk


class NamesStorage(object):
    def __init__(self):
        self.loaded_names = {}

    #def __contains__(self, name):
        #"""finds out if the approximate key is in the loaded_names dictionary"""
        ##name = (vector_size, subcase_id, result_type, label, min_value, max_value)
        #key = name[:4]
        #value = name[4:]
        #assert len(key) == 4, key
        #assert len(value) == 2, value
        #if key in self.loaded_names:
            #value2 = self.loaded_names[key]
            #if value == value2:
                #return True
        #return False
        #return  in self.loaded_names

    def add(self, name):
        """
        adds the approximate name and value to the loaded_names dictionary
        """
        key = name[:4]
        value = name[4:]
        assert len(key) == 4, key
        assert len(value) == 2, value
        assert key not in self.loaded_names
        self.loaded_names[key] = value
        #self.loaded_names.add(name)

    def remove(self, name):
        """removes the approximate name from the loaded_names dictionary"""
        key = name[:4]
        del self.loaded_names[key]

    def get_name_string(self, name):
        """Gets the approximate name as a string"""
        key = name[:4]
        value = name[4:]
        return '_'.join([str(k) for k in key])

    def has_close_name(self, name):
        """checks to see if the approximate key is in loaded_names"""
        key = name[:4]
        return key in self.loaded_names

    def has_exact_name(self, name):
        """
        checks to see if the approximate key is in loaded_names
        and the value is the expected value
        """
        key = name[:4]
        value = name[4:]
        return key in self.loaded_names and self.loaded_names[key] == value

class GuiCommon(object):
    def __init__(self):
        self.nvalues = 9
        self.groups = set([])
        self._group_elements = {}
        self._group_coords = {}
        self._group_shown = {}
        self._names_storage = NamesStorage()

        self.dim_max = 1.0
        self.vtk_version = [int(i) for i in vtk.VTK_VERSION.split('.')[:1]]
        print('vtk_version = %s' % (self.vtk_version))

    def nCells(self):
        try:
            cell_data = self.grid.GetCellData()
            return cell_data.GetNumberOfCells()
        except AttributeError:
            return 0

    def nPoints(self):
        try:
            point_data = self.grid.GetPointData()
            return point_data.GetNumberOfPoints()
        except AttributeError:
            return 0

    def _is_int_result(self, data_format):
        if 'i' in data_format:
            return True
        return False

    def update_axes_length(self, dim_max):
        """
        scale coordinate system based on model length
        """
        self.dim_max = dim_max
        dim_max *= 0.10
        if hasattr(self, 'axes'):
            for cid, axes in iteritems(self.axes):
                axes.SetTotalLength(dim_max, dim_max, dim_max)

    def update_text_actors(self, subcase_id, subtitle, min_value, max_value, label):
        self.textActors[0].SetInput('Max:  %g' % max_value)  # max
        self.textActors[1].SetInput('Min:  %g' % min_value)  # min
        self.textActors[2].SetInput('Subcase: %s Subtitle: %s' % (subcase_id, subtitle))  # info

        if label:
            self.textActors[3].SetInput('Label: %s' % label)  # info
            self.textActors[3].VisibilityOn()
        else:
            self.textActors[3].VisibilityOff()

    def cycleResults(self, result_name=None):
        if self.nCases <= 1:
            self.log.warning('cycleResults(result_name=%r); nCases=%i' % (result_name, self.nCases))
            if self.nCases == 0:
                self.scalarBar.SetVisibility(False)
            return
        result_type = self.cycleResults_explicit(result_name, explicit=False)
        self.log_command('cycleResults(result_name=%r)' % result_type)

    def get_subtitle_label(self, subcase_id):
        try:
            subtitle, label = self.iSubcaseNameMap[subcase_id]
        except KeyError:
            subtitle = 'case=NA'
            label = 'label=NA'
        return subtitle, label

    def cycleResults_explicit(self, result_name=None, explicit=True):
        #if explicit:
            #self.log_command('cycleResults(result_name=%r)' % result_name)
        print("is_nodal=%s is_centroidal=%s" % (self.is_nodal, self.is_centroidal))

        found_cases = self.incrementCycle(result_name)
        if found_cases:
            result_type = self._set_case(result_name, self.iCase, explicit=explicit, cycle=True)
        else:
            result_type = None
        #else:
            #self.log_command(""didn't find case...")
        return result_type

    def _set_case(self, result_name, icase, explicit=False, cycle=False):
        if not cycle and icase == self.iCase:
            # don't click the button twice
            return

        try:
            key = self.caseKeys[icase]
        except:
            print('icase=%s caseKeys=%s' % (icase, str(self.caseKeys)))
            raise
        self.iCase = icase
        case = self.resultCases[key]
        label2 = ''
        if len(key) == 5:
            (subcase_id, result_type, vector_size, location, data_format) = key
        elif len(key) == 6:
            (subcase_id, j, result_type, vector_size, location, data_format) = key
        else:
            (subcase_id, j, result_type, vector_size, location, data_format, label2) = key

        subtitle, label = self.get_subtitle_label(subcase_id)
        label += label2
        print("subcase_id=%s result_type=%r subtitle=%r label=%r"
              % (subcase_id, result_type, subtitle, label))

        #================================================
        if isinstance(case, ndarray):
            max_value = case.max()
            min_value = case.min()
        else:
            raise RuntimeError('list-based results have been removed; use numpy.array')

        name = (vector_size, subcase_id, result_type, label, min_value, max_value)
        # flips sign to make colors go from blue -> red
        norm_value = float(max_value - min_value)

        if self._names_storage.has_exact_name(name):
            grid_result = None
        else:
            grid_result = self.set_grid_values(name, case, vector_size,
                                               min_value, max_value, norm_value)

        self.update_text_actors(subcase_id, subtitle,
                                min_value, max_value, label)

        # TODO: results can only go from centroid->node and not back to centroid
        self.final_grid_update(name, grid_result, key, subtitle, label)

        self.UpdateScalarBar(result_type, min_value, max_value, norm_value,
                             data_format, is_blue_to_red=True, is_horizontal=self.is_horizontal_scalar_bar)

        location = self.get_case_location(key)
        self.res_widget.update_method(location)
        if explicit:
            self.log_command('cycleResults(result_name=%r)' % result_type)
        return result_type

    def set_grid_values(self, name, case, vector_size, min_value, max_value, norm_value,
                        is_blue_to_red=True):
        """
        https://pyscience.wordpress.com/2014/09/06/numpy-to-vtk-converting-your-numpy-arrays-to-vtk-arrays-and-files/
        """
        if self._names_storage.has_exact_name(name):
            return

        if 0: # nan testing
            from numpy import float32, int32
            if case.dtype.name == 'float32':
                case[50] = float32(1) / float32(0)
            else:
                case[50] = int32(1) / int32(0)

        if vector_size == 1:
            if is_blue_to_red:
                if norm_value == 0:
                    #for i, value in enumerate(case):
                        #grid_result.InsertNextValue(1 - min_value)
                    nvalues = len(case)
                    case2 = full((nvalues), 1.0 - min_value, dtype='float32')
                    #case2 = 1 - ones(nvalues) * min_value
                else:
                    #for i, value in enumerate(case):
                        #grid_result.InsertNextValue(1.0 - (value - min_value) / norm_value)
                    case2 = 1.0 - (case - min_value) / norm_value
            else:
                if norm_value == 0:
                    # how do you even get a constant nodal result on a surface?
                    # nodal normals on a constant surface, but that's a bit of an edge case
                    #for i, value in enumerate(case):
                        #grid_result.InsertNextValue(min_value)
                    case2 = full((nvalues), min_value, dtype='float32')
                    #case2 = case
                else:
                    #for i, value in enumerate(case):
                        #grid_result.InsertNextValue((value - min_value) / norm_value)
                    case2 = (case - min_value) / norm_value

            #case2 = case
            #print('max =', case2.max())

            grid_result = numpy_to_vtk(
                num_array=case2,
                deep=True,
                array_type=vtk.VTK_FLOAT
            )
            #print('max2 =', grid_result.GetRange())
        else:
            # vector_size=3
            #for value in case:
                #grid_result.InsertNextTuple3(*value)  # x, y, z
            #if case.flags.contiguous:
                #case2 = case
                #deep = False
            #else:
                #case2 = deepcopy(case)
                #deep = True
            deep = True
            grid_result = numpy_to_vtk(
                num_array=case2,
                deep=deep,
                array_type=vtk.VTK_FLOAT
            )
        return grid_result

    def final_grid_update(self, name, grid_result, key, subtitle, label):
        if len(key) == 5:
            (subcase_id, result_type, vector_size, location, data_format) = key
        elif len(key) == 6:
            (subcase_id, j, result_type, vector_size, location, data_format) = key
        else:
            (subcase_id, j, result_type, vector_size, location, data_format, label2) = key

        name_str = self._names_storage.get_name_string(name)
        if not self._names_storage.has_exact_name(name):
            grid_result.SetName(name_str)
            self._names_storage.add(name)

            if location == 'centroid':
                cell_data = self.grid.GetCellData()
                if self._names_storage.has_close_name(name):
                    cell_data.RemoveArray(name_str)
                    self._names_storage.remove(name)

                cell_data.AddArray(grid_result)
                self.log_info("centroidal plotting vector=%s - subcase_id=%s result_type=%s subtitle=%s label=%s"
                              % (vector_size, subcase_id, result_type, subtitle, label))
            elif location == 'node':
                point_data = self.grid.GetPointData()
                if self._names_storage.has_close_name(name):
                    point_data.RemoveArray(name_str)
                    self._names_storage.remove(name)

                if vector_size == 1:
                    self.log_info("node plotting vector=%s - subcase_id=%s result_type=%s subtitle=%s label=%s"
                                  % (vector_size, subcase_id, result_type, subtitle, label))
                    point_data.AddArray(grid_result)
                elif vector_size == 3:
                    self.log_info("node plotting vector=%s - subcase_id=%s result_type=%s subtitle=%s label=%s"
                                  % (vector_size, subcase_id, result_type, subtitle, label))
                    point_data.AddVector(grid_result)
                else:
                    raise RuntimeError(vector_size)
            else:
                raise RuntimeError(location)

        if location == 'centroid':
            cell_data = self.grid.GetCellData()
            cell_data.SetActiveScalars(name_str)

            point_data = self.grid.GetPointData()
            point_data.SetActiveScalars(None)
        elif location == 'node':
            cell_data = self.grid.GetCellData()
            cell_data.SetActiveScalars(None)

            point_data = self.grid.GetPointData()
            if vector_size == 1:
                point_data.SetActiveScalars(name_str)
            elif vector_size == 3:
                point_data.SetActiveVectors(name_str)
            else:
                raise RuntimeError(vector_size)
        else:
            raise RuntimeError(location)

        self.grid.Modified()
        self.vtk_interactor.Render()

        self.hide_labels(show_msg=False)
        self.show_labels(result_names=[result_type], show_msg=False)

    def _get_icase(self, result_name):
        found_case = False
        print(self.resultCases.keys())
        i = 0
        for icase, cases in sorted(iteritems(self.resultCases)):
            if result_name == icase[1]:
                found_case = True
                iCase = i
                break
            i += 1
        assert found_case == True, 'result_name=%r' % result_name
        return iCase

    def incrementCycle(self, result_name=False):
        found_case = False
        if result_name is not False and result_name is not None:
            for icase, cases in sorted(iteritems(self.resultCases)):
                if result_name == cases[1]:
                    found_case = True
                    self.iCase = icase  # no idea why this works...if it does...

        if not found_case:
            if self.iCase is not self.nCases:
                self.iCase += 1
            else:
                self.iCase = 0
        if self.iCase == len(self.caseKeys):
            self.iCase = 0

        if len(self.caseKeys) > 0:
            try:
                key = self.caseKeys[self.iCase]
            except IndexError:
                found_cases = False
                return found_cases

            location = self.get_case_location(key)
            print("key = %s" % str(key))
            #if key[2] == 3:  # vector size=3 -> vector, skipping ???
                #self.incrementCycle()
            found_cases = True
        else:
            result_type = 'centroidal' if location == 'centroid' else 'nodal'
            self.log_error("No Results found.  Many results are not supported in the GUI.\nTry using %s results."
                           % result_type)
            self.scalarBar.SetVisibility(False)
            found_cases = False
        #print("next iCase=%s key=%s" % (self.iCase, key))
        return found_cases

    def get_case_location(self, key):
        if len(key) == 5:
            (subcase_id, result_type, vector_size, location, data_format) = key
        elif len(key) == 6:
            (subcase_id, i, result_type, vector_size, location, data_format) = key
        else:
            (subcase_id, i, result_type, vector_size, location, data_format, label2) = key
        return location

    def UpdateScalarBar(self, title, min_value, max_value, norm_value,
                        data_format, is_blue_to_red=True, is_horizontal=True):
        """
        :param title:       the scalar bar title
        :param min_value:   the blue value
        :param max_value:   the red value
        :param data_format: '%g','%f','%i', etc.
        :param is_blue_to_red:  flips the order of the RGB points
        """
        print("UpdateScalarBar min=%s max=%s norm=%s" % (min_value, max_value, norm_value))
        self.colorFunction.RemoveAllPoints()

        if is_blue_to_red:
            self.colorFunction.AddRGBPoint(min_value, 0.0, 0.0, 1.0)  # blue
            self.colorFunction.AddRGBPoint(max_value, 1.0, 0.0, 0.0)  # red
        else:
            self.colorFunction.AddRGBPoint(min_value, 1.0, 0.0, 0.0)  # red
            self.colorFunction.AddRGBPoint(max_value, 0.0, 0.0, 1.0)  # blue

        if is_horizontal:
            # put the scalar bar at the top
            self.scalarBar.SetOrientationToHorizontal()
            width = 0.95
            height = 0.15
            x = (1 - width) / 2.
            y = 1 - 0.02 - height
        else:
            # put the scalar bar at the right side
            self.scalarBar.SetOrientationToVertical()
            width = 0.2
            height = 0.9
            x = 1 - 0.01 - width
            y = (1 - height) / 2.
        self.scalarBar.SetHeight(height)
        self.scalarBar.SetWidth(width)
        self.scalarBar.SetPosition(x, y)

        if 0:
            self.colorFunction.SetRange(min_value, max_value)
            #self.colorFunction.Update()

            #scalar_range = self.grid.GetScalarRange()
            #print('scalar_range', scalar_range)
            #self.aQuadMapper.SetScalarRange(scalar_range)
            #self.aQuadMapper.SetScalarRange(min_value, max_value)
            self.aQuadMapper.SetScalarRange(max_value, min_value)
            self.aQuadMapper.Update()

        #self.scalarBar.SetLookupTable(self.colorFunction)
        self.scalarBar.SetTitle(title)

        nvalues = 11
        data_format_display = data_format
        if data_format == '%i':
            data_format_display = '%.0f'
            nvalues = int(max_value - min_value) + 1
            if nvalues < 7:
                nvalues = 7
            elif nvalues > 30:
                nvalues = 11
        self.scalarBar.SetLabelFormat(data_format_display)

        #if title in ['ElementID', 'Eids', 'Region'] and norm_value < 11:
            #nvalues = int(max_value - min_value) + 1
            #print("need to adjust axes...max_value=%s" % max_value)

        if self.nvalues is not None:
            if not self._is_int_result(data_format):
                # don't change nvalues for int results
                nvalues = self.nvalues

        self.scalarBar.SetNumberOfLabels(nvalues)
        self.scalarBar.SetMaximumNumberOfColors(nvalues)
        self.scalarBar.Modified()


