from __future__ import print_function
from six import iteritems

import os
from struct import unpack
from collections import defaultdict

from numpy import array, vstack, hstack, where, unique, savetxt
from pyNastran.op2.fortran_format import FortranFormat
from pyNastran.utils.log import get_logger

def merge_tecplot_files(tecplot_filenames, tecplot_filename_out=None, log=None):
    print('merging...')
    assert isinstance(tecplot_filenames, (list, tuple)), type(tecplot_filenames)
    assert len(tecplot_filenames) > 1, tecplot_filenames

    xyz = []
    elements = []
    results = []
    nnodes = 0

    model = TecplotReader(log=log)
    for tecplot_filename in tecplot_filenames:
        print('reading %s' % tecplot_filename)
        model.read_tecplot(tecplot_filename)
        xyz.append(model.xyz)
        elements.append(model.elements + nnodes)
        results.append(model.results)
        nnodes += model.nnodes

    model.xyz = vstack(xyz)
    model.elements = vstack(elements)
    model.results = vstack(results)
    if tecplot_filename_out is not None:
        model.write_tecplot(tecplot_filename_out)
    return model

class TecplotReader(FortranFormat):
    """
    Parses a hexa binary Tecplot 360 file.
    Writes an ASCII Tecplot 10 file (no transient support).
    """
    def __init__(self, log=None, debug=False):
        FortranFormat.__init__(self)
        self.endian = b'<'
        self.log = get_logger(log, 'debug' if debug else 'info')
        self.debug = debug
        self.xyz = array([], dtype='float32')
        self.elements = array([], dtype='int32')
        self.results = array([], dtype='float32')
        self.tecplot_filename = ''

    #def show(self, n, types='', endian=''):
        #pass

    #def show_data(self, data, types='', endian=''):
        #pass

    @property
    def nnodes(self):
        return self.xyz.shape[0]

    @property
    def nelements(self):
        return self.elements.shape[0]

    def read_tecplot(self, tecplot_filename, nnodes=None, nelements=None):
        self.tecplot_filename = tecplot_filename
        assert os.path.exists(tecplot_filename), tecplot_filename
        tecplot_file = open(tecplot_filename, 'rb')
        self.f = tecplot_file
        self.n = 0

        data = self.f.read(8)
        self.n += 8
        word, = unpack(b'8s', data)
        #print('word = ', word)

        values = []
        ii = 0
        for ii in range(100):
            datai = self.f.read(4)
            val, = unpack(b'i', datai)
            self.n += 4
            values.append(val)
            if val == 9999:
                break
        assert ii < 100, ii
        #print(values)

        nbytes = 3 * 4
        data = self.f.read(nbytes)
        self.n += nbytes

        nbytes = 1 * 4
        data = self.f.read(nbytes)
        self.n += nbytes
        zone_type, = unpack(b'i', data)
        #self.show(100, endian='<')

        nbytes = 11 * 4
        data = self.f.read(nbytes)
        self.n += nbytes
        self.show_data(data, types='i', endian='<') # 'if'?
        #assert self.n == 360, self.n
        #print('----------')

        nbytes = 2 * 4
        data = self.f.read(nbytes)
        self.n += nbytes
        nnodes2, nelements2 = unpack('2i', data)
        if nnodes and nelements:
            print('nnodes=%s nelements=%s' % (nnodes, nelements))
            print('nnodes2=%s nelements2=%s' % (nnodes2, nelements2))
        else:
            nnodes = nnodes2
            nelements = nelements2
        assert nnodes == nnodes2
        assert nelements == nelements2
        #assert nnodes2 < 10000, nnodes
        #assert nelements2 < 10000, nelements

        nbytes = 35 * 4
        data = self.f.read(nbytes)
        self.n += nbytes
        #self.show_data(data, types='ifs', endian='<')
        #print('----------')

        nbytes = 30 * 4
        data = self.f.read(nbytes)
        self.n += nbytes

        #self.show_data(data, types='ifs', endian='<')
        assert zone_type in [5], zone_type

        # p.98
        # zone_title
        # zone_type
        #   0=ORDERED, 1=FELINESEG, 2=FETRIANGLE,
        #   3=FEQUADRILATERAL, 4=FETETRAHEDRON, 5=FEBRICK
        # i_max_or_num_points
        # j_max_or_num_elements
        # k_max
        # i_cell_max
        # j_cell_max
        # k_cell_max
        # solution_time
        # strand_id
        # parent_zone
        # is_block (0=POINT, 1=BLOCK)
        # num_face_connections
        # face_neighbor_mode
        # passive_var_list
        # value_location (0=cell-centered; 1=node-centered)
        # share_var_from_zone
        # share_connectivity_from_zone

        # http://www.hgs.k12.va.us/tecplot/documentation/tp_data_format_guide.pdf


        #print('----------')
        # the variables: [x, y, z]
        nvars = 3
        #nnodes = 3807
        ni = nnodes * nvars
        nbytes = ni * 4
        data = self.f.read(nbytes)
        self.n += nbytes
        xyzvals = unpack(b'%sf' % ni, data)
        xyz = array(xyzvals, dtype='float32').reshape(3, nnodes).T

        # the variables: [rho, u, v, w, p]
        nvars = 5
        dunno = 0    # what's with this...
        ni = nnodes * nvars + dunno
        nbytes = ni * 4
        data = self.f.read(nbytes)
        self.n += nbytes
        resvals = unpack(b'%sf' % ni, data)
        results = array(resvals, dtype='float32').reshape(nvars, nnodes).T

        #
        # 7443 elements
        nnodes_per_element = 8 # 8 nodes/elements
        #nelements = 7443
        nvals = nnodes_per_element * nelements
        nbytes = nvals * 4
        node_ids = unpack(b'%ii' % nvals, self.f.read(nbytes))
        self.n += nbytes

        elements = array(node_ids).reshape(nelements, nnodes_per_element)
        #print(elements)

        #self.show_data(data, types='ifs', endian='<')
        #print(vals)

        #self.show(100, endian='<')
        self.elements = elements
        tecplot_file.close()

        self.xyz = xyz
        self.results = results

    def write_tecplot(self, tecplot_filename):
        tecplot_file = open(tecplot_filename, 'w')
        is_results = bool(len(self.results))
        msg = 'TITLE     = "tecplot geometry and solution file"\n'
        msg += 'VARIABLES = "x"\n'
        msg += '"y"\n'
        msg += '"z"\n'
        if is_results:
            msg += '"rho"\n'
            msg += '"u"\n'
            msg += '"v"\n'
            msg += '"w"\n'
            msg += '"p"\n'
        msg += 'ZONE T="%s"\n' % r'\"processor 1\"'

        #is_points = not is_results
        is_points = False
        nnodes = self.nnodes
        if is_points:
            msg += ' n=%i, e=%i, ZONETYPE=FEBrick, DATAPACKING=POINT\n' % (nnodes, self.nelements)
        else:
            msg += ' n=%i, e=%i, ZONETYPE=FEBrick, DATAPACKING=BLOCK\n' % (nnodes, self.nelements)
        tecplot_file.write(msg)

        # xyz
        if is_points:
            if self.results:
                data = hstack([self.xyz, self.results])
                nresults = self.results.shape[1]
                fmt = ' %15.9E' * nresults# + '\n'
            else:
                data = self.xyz
                fmt = ' %15.9E %15.9E %15.9E'
            #vals = self.xyz[:, ivar].ravel()
            # for vals in enumerate(data):
                # tecplot_file.write(fmt % tuple(vals))
            savetxt(tecplot_file, data, fmt=fmt)
        else:
            #nvalues_per_line = 5
            for ivar in range(3):
                #tecplot_file.write('# ivar=%i\n' % ivar)
                #print('xyz.shape =', self.xyz.shape)
                vals = self.xyz[:, ivar].ravel()
                msg = ''
                for ival, val in enumerate(vals):
                    msg += ' %15.9E' % val
                    if (ival + 1) % 5 == 0:
                        tecplot_file.write(msg)
                        msg = '\n'
                tecplot_file.write(msg.rstrip() + '\n')

            if is_results:
                for ivar in range(5):
                    #tecplot_file.write('# ivar=%i\n' % ivar)
                    #print('xyz.shape =', self.xyz.shape)
                    vals = self.results[:, ivar].ravel()
                    msg = ''
                    for ival, val in enumerate(vals):
                        msg += ' %15.9E' % val
                        if (ival + 1) % 5 == 0:
                            tecplot_file.write(msg)
                            msg = '\n'
                    tecplot_file.write(msg.rstrip() + '\n')

        # elements
        efmt = ' %i %i %i %i %i %i %i %i\n'
        elements = self.elements + 1
        print('inode_min =', elements.min())
        print('inode_max =', elements.max())
        assert elements.min() == 1, elements.min()
        assert elements.max() == nnodes, elements.max()
        for element in elements:
            tecplot_file.write(efmt % tuple(element))
        tecplot_file.close()

    def get_free_faces(self):
        self.log.info('start get_free_faces')
        sort_face_to_element_map = defaultdict(list)
        sort_face_to_face = {}
        for ie, element in enumerate(self.elements):
            btm = [element[0], element[1], element[2], element[3]]
            top = [element[4], element[5], element[6], element[7]]
            left = [element[0], element[3], element[7], element[4]]
            right = [element[1], element[2], element[6], element[5]]
            front = [element[0], element[1], element[5], element[4]]
            back = [element[3], element[2], element[6], element[7]]
            for face in [btm, top, left, right, front, back]:
                if len(unique(face)) >= 3:
                    sort_face = tuple(sorted(face))
                    sort_face_to_element_map[sort_face].append(ie)
                    sort_face_to_face[sort_face] = face

        free_faces = []
        for sort_face, eids in iteritems(sort_face_to_element_map):
            if len(eids) == 1:
                free_faces.append(sort_face_to_face[sort_face])
        self.log.info('finished get_free_faces')
        return free_faces

    def extract_y_slice(self, y0, tol=0.01, slice_filename=None):
        """
        doesn't work...
        """
        print('slicing...')
        y = self.xyz[:, 1]
        nodes = self.xyz
        assert tol > 0.0, tol
        elements = self.elements
        results = self.results

        iy = where((y0 - tol <= y) & (y <= y0 + tol))[0]

        print(y[iy])
        print(nodes[iy, 1].min(), nodes[iy, 1].max())
        #iy = where(y <= y0 + tol)[0]
        assert len(iy) > 0, iy
        #inode = iy + 1


        # find all elements that have iy within tolerance
        #slots = where(elements == iy)
        #slots = where(element for element in elements
                      #if any(iy in element))
        #slots = where(iy == elements.ravel())[0]
        ielements = unique([ie for ie, elem in enumerate(elements)
                            for i in range(8)
                            if i in iy])
        #print(slots)
        #asdf
        #ri, ci = slots
        #ri = unique(hstack([where(element == iy)[0] for element in elements]))
        #ri = [ie for ie, element in enumerate(elements)
              #if [n for n in element
                  #if n in iy]]
        #ri = [where(element == iy)[0] for element in elements if where(element == iy)[0]]
        #print(ri)
        #ielements = unique(ri)
        print(ielements)
        assert len(ielements) > 0, ielements

        # find nodes
        elements2 = elements[ielements, :]
        inodes = unique(elements2)
        assert len(inodes) > 0, inodes

        # renumber the nodes
        nidmap = {}
        for inode, nid in enumerate(inodes):
            nidmap[nid] = inode
        elements3 = array(
            [[nidmap[nid] for nid in element]
             for element in elements2],
            dtype='int32')

        print(inodes)
        nodes2 = nodes[inodes, :]
        results2 = results[inodes, :]
        model = TecplotReader()
        model.xyz = nodes2
        model.results = results2
        model.elements = elements3

        if slice_filename:
            model.write_tecplot(slice_filename)
        return model

def main():
    plt = TecplotReader()
    fnames = os.listdir(r'Z:\Temporary_Transfers\steve\output\time20000')


    datai = [
        'n=3807, e=7443',
        'n=3633, e=7106',
        'n=3847, e=7332',
        'n=3873, e=6947',
        'n=4594, e=8131',
        'n=4341, e=7160',
        'n=4116, e=8061',
        'n=4441, e=8105',
        'n=4141, e=8126',
        'n=4085, e=8053',
        'n=4047, e=8215',
        'n=4143, e=8123',
        'n=4242, e=7758',
        'n=3830, e=7535',
        'n=3847, e=7936',
        'n=3981, e=7807',
        'n=3688, e=7415',
        'n=4222, e=8073',
        'n=4164, e=7327',
        'n=3845, e=8354',
        'n=4037, e=6786',
        'n=3941, e=8942',
        'n=4069, e=7345',
        'n=4443, e=8001',
        'n=3895, e=7459',
        'n=4145, e=7754',
        'n=4224, e=8152',
        'n=4172, e=7878',
        'n=4138, e=8864',
        'n=3801, e=7431',
        'n=3984, e=6992',
        'n=4195, e=7967',
        'n=4132, e=7992',
        'n=4259, e=7396',
        'n=4118, e=7520',
        'n=4176, e=7933',
        'n=4047, e=8098',
        'n=4064, e=8540',
        'n=4144, e=8402',
        'n=4144, e=7979',
        'n=3991, e=6984',
        'n=4080, e=8465',
        'n=3900, e=7981',
        'n=3709, e=8838',
        'n=4693, e=8055',
        'n=4022, e=7240',
        'n=4028, e=8227',
        'n=3780, e=7551',
        'n=3993, e=8671',
        'n=4241, e=7277',
        'n=4084, e=6495',
        'n=4103, e=8165',
        'n=4496, e=5967',
        'n=3548, e=8561',
        'n=4143, e=7749',
        'n=4136, e=8358',
        'n=4096, e=7319',
        'n=4209, e=8036',
        'n=3885, e=7814',
        'n=3800, e=8232',
        'n=3841, e=7837',
        'n=3874, e=7571',
        'n=3887, e=8079',
        'n=3980, e=7834',
        'n=3763, e=7039',
        'n=4287, e=7130',
        'n=4110, e=8336',
        'n=3958, e=7195',
        'n=4730, e=7628',
        'n=4087, e=8149',
        'n=4045, e=8561',
        'n=3960, e=7320',
        'n=3901, e=8286',
        'n=4065, e=7013',
        'n=4160, e=7906',
        'n=3628, e=7140',
        'n=4256, e=8168',
        'n=3972, e=8296',
        'n=3661, e=7879',
        'n=3922, e=8093',
        'n=3972, e=6997',
        'n=3884, e=7603',
        'n=3609, e=6856',
        'n=4168, e=7147',
        'n=4206, e=8232',
        'n=4631, e=8222',
        'n=3970, e=7569',
        'n=3998, e=7617',
        'n=3855, e=7971',
        'n=4092, e=7486',
        'n=4407, e=7847',
        'n=3976, e=7627',
        'n=3911, e=8483',
        'n=4144, e=7919',
        'n=4033, e=8129',
        'n=3976, e=7495',
        'n=3912, e=7739',
        'n=4278, e=8522',
        'n=4703, e=8186',
        'n=4230, e=7811',
        'n=3971, e=7699',
        'n=4081, e=8242',
        'n=4045, e=7524',
        'n=4532, e=5728',
        'n=4299, e=8560',
        'n=3885, e=7531',
        'n=4452, e=8405',
        'n=4090, e=7661',
        'n=3937, e=7739',
        'n=4336, e=7612',
        'n=4101, e=7461',
        'n=3980, e=8632',
        'n=4523, e=7761',
        'n=4237, e=8463',
        'n=4013, e=7856',
        'n=4219, e=8013',
        'n=4248, e=8328',
        'n=4529, e=8757',
        'n=4109, e=7496',
        'n=3969, e=8026',
        'n=4093, e=8506',
        'n=3635, e=7965',
        'n=4347, e=8123',
        'n=4703, e=7752',
        'n=3867, e=8124',
        'n=3930, e=7919',
        'n=4247, e=7154',
        'n=4065, e=8125',
    ]
    fnames = [os.path.join(r'Z:\Temporary_Transfers\steve\output\time20000', fname)
              for fname in fnames]
    tecplot_filename_out = None
    #tecplot_filename_out = 'tecplot_joined.plt'
    model = merge_tecplot_files(fnames, tecplot_filename_out)

    y0 = 0.0
    model.extract_y_slice(y0, tol=0.014, slice_filename='slice.plt')

    return
    for iprocessor, fname in enumerate(fnames):
        nnodes, nelements = datai[iprocessor].split(',')
        nnodes = int(nnodes.split('=')[1])
        nelements = int(nelements.split('=')[1])

        ip = iprocessor + 1
        tecplot_filename = 'model_final_meters_part%i_tec_volume_timestep20000.plt' % ip
        print(tecplot_filename)
        try:
            plt.read_tecplot(tecplot_filename, nnodes=nnodes, nelements=nelements)
            plt.write_tecplot('processor%i.plt' % ip)
        except:
            raise
        #break

if __name__ == '__main__':
    main()

