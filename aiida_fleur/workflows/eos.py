# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

"""
In this module you find the workflow 'FleurEosWorkChain' for the calculation of
of an equation of state
"""
# TODO: print more user info
# allow different inputs, make things optional(don't know yet how)
# half number of iteration if you are close to be converged. (therefore
# one can start with 18 iterations, and if thats not enough run again 9 or something)
from __future__ import absolute_import
from __future__ import print_function
import numpy as np

import six
from six.moves import range

from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.orm import Float, StructureData, Dict
from aiida.engine import WorkChain, ToContext  # ,Outputs
from aiida.engine import calcfunction as cf

from aiida_fleur.tools.StructureData_util import rescale, rescale_nowf, is_structure
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf_util import check_eos_energies

# pylint: disable=invalid-name
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name


class FleurEosWorkChain(WorkChain):
    """
    This workflow calculates the equation of states of a structure.
    Calculates several unit cells with different volumes.
    A Birch_Murnaghan  equation of states fit determines the Bulk modulus and the
    groundstate volume of the cell.

    :params wf_parameters: Dict node, optional 'wf_parameters', protocol specifying parameter dict
    :params structure: StructureData node, 'structure' crystal structure
    :params calc_parameters: Dict node, optional 'calc_parameters' parameters for inpgen
    :params inpgen: Code node,
    :params fleur: Code node,


    :return output_eos_wc_para: Dict node, contains relevant output information.
                                about general succeed, fit results and so on.
    """
    def __init__(self, inputs=None, logger=None, runner=None, enable_persistence=True):

        super().__init__(inputs, logger, runner, enable_persistence)
        self._workflowversion = "0.3.4"

        self._default_options = {
            'resources': {"num_machines": 1},
            'max_wallclock_seconds': 6 * 60 * 60,
            'queue_name': '',
            'custom_scheduler_commands': '',
            'import_sys_environment': False,
            'environment_variables': {}
            }

        self._wf_default = {
            'fleur_runmax': 4,
            'density_converged': 0.02,
            'serial': False,
            'itmax_per_run': 30,
            'inpxml_changes': [],
            'points': 9,
            'step': 0.002,
            'guess': 1.00
            }

        self._scf_keys = ['fleur_runmax', 'density_converged', 'serial',
                          'itmax_per_run', 'inpxml_changes']

    @classmethod
    def define(cls, spec):
        super(FleurEosWorkChain, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False)
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=Dict, required=False)
        spec.input("settings", valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            cls.structures,
            cls.converge_scf,
            cls.return_results
        )

        spec.output('output_eos_wc_para', valid_type=Dict)
        spec.output('output_eos_wc_structure', valid_type=StructureData)

        #exit codes
        spec.exit_code(331, 'ERROR_INVALID_CODE_PROVIDED',
                       message="Invalid code node specified, check inpgen and fleur code nodes.")

    def start(self):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        self.report("Started eos workflow version {}".format(self._workflowversion))


        self.ctx.last_calc2 = None
        self.ctx.calcs = []
        self.ctx.calcs_future = []
        self.ctx.structures = []
        self.ctx.temp_calc = None
        self.ctx.structurs_uuids = []
        self.ctx.scalelist = []
        self.ctx.volume = []
        self.ctx.volume_peratom = {}
        self.ctx.org_volume = -1  # avoid div 0
        self.ctx.labels = []
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        # TODO get all successfull from convergence, if all True this

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = self._wf_default
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        self.ctx.points = wf_dict.get('points', 9)
        self.ctx.step = wf_dict.get('step', 0.002)
        self.ctx.guess = wf_dict.get('guess', 1.00)
        self.ctx.serial = wf_dict.get('serial', False)  # True
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)

        # initialize the dictionary using defaults if no options are given
        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        # Check if user gave valid inpgen and fleur executables
        inputs = self.inputs
        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

    def structures(self):
        """
        Creates structure data nodes with different Volume (lattice constants)
        """
        points = self.ctx.points
        step = self.ctx.step
        guess = self.ctx.guess
        startscale = guess - (points - 1) / 2 * step

        for point in range(points):
            self.ctx.scalelist.append(startscale + point * step)

        self.report('scaling factors which will be calculated:{}'.format(self.ctx.scalelist))
        self.ctx.org_volume = self.inputs.structure.get_cell_volume()
        self.ctx.structurs = eos_structures(self.inputs.structure, self.ctx.scalelist)

    def converge_scf(self):
        """
        Launch fleur_scfs from the generated structures
        """
        calcs = {}

        for i, struc in enumerate(self.ctx.structurs):
            inputs = self.get_inputs_scf()
            inputs['structure'] = struc
            natoms = len(struc.sites)
            label = str(self.ctx.scalelist[i])
            label_c = '|eos| fleur_scf_wc'
            description = '|FleurEosWorkChain|fleur_scf_wc|scale {}, {}'.format(label, i)
            # inputs['label'] = label_c
            # inputs['description'] = description

            self.ctx.volume.append(struc.get_cell_volume())
            self.ctx.volume_peratom[label] = struc.get_cell_volume() / natoms
            self.ctx.structurs_uuids.append(struc.uuid)

            result = self.submit(FleurScfWorkChain, **inputs)
            self.ctx.labels.append(label)
            calcs[label] = result

        return ToContext(**calcs)

    def get_inputs_scf(self):
        """
        get and 'produce' the inputs for a scf-cycle
        """
        inputs = {}

        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)
        inputs['wf_parameters'] = scf_wf_param

        inputs['options'] = self.ctx.options

        try:
            calc_para = self.inputs.calc_parameters.get_dict()
        except AttributeError:
            calc_para = {}
        inputs['calc_parameters'] = calc_para

        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur

        inputs['options'] = Dict(dict=inputs['options'])
        inputs['wf_parameters'] = Dict(dict=inputs['wf_parameters'])
        inputs['calc_parameters'] = Dict(dict=inputs['calc_parameters'])

        return inputs

    def return_results(self):
        """
        return the results of the calculations  (scf workchains) and do a
        Birch-Murnaghan fit for the equation of states
        """
        distancelist = []
        t_energylist = []
        t_energylist_peratom = []
        vol_peratom_success = []
        outnodedict = {}
        natoms = len(self.inputs.structure.sites)
        htr_to_ev = 27.21138602

        for label in self.ctx.labels:
            calc = self.ctx[label]

            if not calc.is_finished_ok:
                message = ('One SCF workflow was not successful: {}'.format(label))
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                continue

            try:
                _ = calc.outputs.output_scf_wc_para
            except KeyError:
                message = (
                    'One SCF workflow failed, no scf output node: {}.'
                    ' I skip this one.'.format(label))
                self.ctx.errors.append(message)
                self.ctx.successful = False
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()

            t_e = outpara.get('total_energy', float('nan'))
            e_u = outpara.get('total_energy_units', 'eV')
            if e_u == 'Htr' or 'htr':
                t_e = t_e * htr_to_ev
            dis = outpara.get('distance_charge', float('nan'))
            dis_u = outpara.get('distance_charge_units')
            t_energylist.append(t_e)
            t_energylist_peratom.append(t_e / natoms)
            vol_peratom_success.append(self.ctx.volume_peratom[label])
            distancelist.append(dis)

        not_ok, an_index = check_eos_energies(t_energylist_peratom)

        if not_ok:
            message = ('Abnormality in Total energy list detected. Check '
                       'entr(ies) {}.'.format(an_index))
            hint = ('Consider refining your basis set.')
            self.ctx.info.append(hint)
            self.ctx.warnings.append(message)

        en_array = np.array(t_energylist_peratom)
        vol_array = np.array(vol_peratom_success)

        # TODO: different fits
        if len(en_array): # for some reason just en_array does not work
            volume, bulk_modulus, bulk_deriv, residuals = birch_murnaghan_fit(en_array, vol_array)

            volumes = self.ctx.volume
            gs_scale = volume * natoms / self.ctx.org_volume
            if (volume * natoms < volumes[0]) or (volume * natoms > volumes[-1]):
                warn = ('Groundstate volume was not in the scaling range.')
                hint = ('Consider rerunning around point {}'.format(gs_scale))
                self.ctx.info.append(hint)
                self.ctx.warnings.append(warn)
                # TODO maybe make it a feature to rerun with centered around the gs.
        else:
            volumes = None
            gs_scale = None
            residuals = None
            volume = 0
            bulk_modulus = None
            bulk_deriv = None

        out = {'workflow_name': self.__class__.__name__,
               'workflow_version': self._workflowversion,
               'scaling': self.ctx.scalelist,
               'scaling_gs': gs_scale,
               'initial_structure': self.inputs.structure.uuid,
               'volume_gs': volume * natoms,
               'volumes': volumes,
               'volume_units': 'A^3',
               'natoms': natoms,
               'total_energy': t_energylist,
               'total_energy_units': e_u,
               'structures': self.ctx.structurs_uuids,
               'calculations': [],  # self.ctx.calcs1,
               'scf_wfs': [],  # self.converge_scf_uuids,
               'distance_charge': distancelist,
               'distance_charge_units': dis_u,
               'nsteps': self.ctx.points,
               'guess': self.ctx.guess,
               'stepsize': self.ctx.step,
               # 'fitresults' : [a, latticeconstant, c],
               # 'fit' : fit_new,
               'residuals': residuals,
               'bulk_deriv': bulk_deriv,
               'bulk_modulus': bulk_modulus * 160.217733,  # * echarge * 1.0e21,#GPa
               'bulk_modulus_units': 'GPa',
               'info': self.ctx.info,
               'warnings': self.ctx.warnings,
               'errors': self.ctx.errors
              }

        if self.ctx.successful:
            self.report('Done, Equation of states calculation complete')
        else:
            self.report(
                'Done, but something went wrong.... Probably some individual calculation failed or'
                ' a scf-cycle did not reach the desired distance.')

        outnode = Dict(dict=out)
        outnodedict['results_node'] = outnode

        # create links between all these nodes...
        outputnode_dict = create_eos_result_node(**outnodedict)
        outputnode = outputnode_dict.get('output_eos_wc_para')
        outputnode.label = 'output_eos_wc_para'
        outputnode.description = ('Contains equation of states results and information of an '
                                  'FleurEosWorkChain run.')

        returndict = {}
        returndict['output_eos_wc_para'] = outputnode

        outputstructure = outputnode_dict.get('gs_structure', None)
        if outputstructure:
            outputstructure.label = 'output_eos_wc_structure'
            outputstructure.description = ('Structure with the scaling/volume of the lowest total '
                                           'energy extracted from FleurEosWorkChain')
            outputstructure = save_structure(outputstructure)
            returndict['output_eos_wc_structure'] = outputstructure

        # create link to workchain node
        for link_name, node in six.iteritems(returndict):
            self.out(link_name, node)

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. It will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()

        return

@cf
def create_eos_result_node(**kwargs):
    """
    This is a pseudo wf, to create the right graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_eos_wc_para'] = outpara.clone()
    # copy, because we rather produce the same node twice
    # then have a circle in the database for now...
    outputdict = outpara.get_dict()
    structure = load_node(outputdict.get('initial_structure'))
    gs_scaling = outputdict.get('scaling_gs', 0)
    if gs_scaling:
        gs_structure = rescale_nowf(structure, Float(gs_scaling))
        outdict['gs_structure'] = gs_structure

    return outdict

@cf
def save_structure(structure):
    """
    Saves a structure data node
    """
    structure_return = structure.clone()
    return structure_return


def eos_structures(inp_structure, scalelist):
    """
    Creates many rescalled StructureData nodes out of a crystal structure.
    Keeps the provenance in the database.

    :param StructureData, a StructureData node (pk, sor uuid)
    :param scalelist, list of floats, scaling factors for the cell

    :returns: list of New StructureData nodes with rescalled structure, which are linked to input
              Structure
    """
    structure = is_structure(inp_structure)
    if not structure:
        # TODO: log something (test if it gets here at all)
        return None
    re_structures = []

    for scale in scalelist:
        structure_rescaled = rescale(structure, Float(scale))  # this is a wf
        re_structures.append(structure_rescaled)

    return re_structures

# pylint: disable=invalid-name
def birch_murnaghan_fit(energies, volumes):
    """
    least squares fit of a Birch-Murnaghan equation of state curve. From delta project
    containing in its columns the volumes in A^3/atom and energies in eV/atom
    # The following code is based on the source code of eos.py from the Atomic
    # Simulation Environment (ASE) <https://wiki.fysik.dtu.dk/ase/>.
    :params energies: list (numpy arrays!) of total energies eV/atom
    :params volumes: list (numpy arrays!) of volumes in A^3/atom

    #volume, bulk_modulus, bulk_deriv, residuals = Birch_Murnaghan_fit(data)
    """
    fitdata = np.polyfit(volumes[:]**(-2. / 3.), energies[:], 3, full=True)
    ssr = fitdata[1]
    sst = np.sum((energies[:] - np.average(energies[:]))**2.)

    residuals0 = ssr / sst
    deriv0 = np.poly1d(fitdata[0])
    deriv1 = np.polyder(deriv0, 1)
    deriv2 = np.polyder(deriv1, 1)
    deriv3 = np.polyder(deriv2, 1)

    volume0 = 0
    x = 0
    for x in np.roots(deriv1):
        if x > 0 and deriv2(x) > 0:
            volume0 = x**(-3. / 2.)
            break

    if volume0 == 0:
        print('Error: No minimum could be found')
        exit()

    derivV2 = 4. / 9. * x**5. * deriv2(x)
    derivV3 = (-20. / 9. * x**(13. / 2.) * deriv2(x) -
               8. / 27. * x**(15. / 2.) * deriv3(x))
    bulk_modulus0 = derivV2 / x**(3. / 2.)
    bulk_deriv0 = -1 - x**(-3. / 2.) * derivV3 / derivV2

    return volume0, bulk_modulus0, bulk_deriv0, residuals0


def birch_murnaghan(volumes, volume0, bulk_modulus0, bulk_deriv0):
    """
    This evaluates the Birch Murnaghan equation of states
    """
    PV = []
    EV = []
    v0 = volume0
    bm = bulk_modulus0
    dbm = bulk_deriv0

    for vol in volumes:
        pv_val = 3 * bm / 2. * ((v0 / vol)**(7 / 3.) - (v0 / vol)**(5 / 3.)) * \
            (1 + 3 / 4. * (dbm - 4) * ((v0 / vol)**(2 / 3.) - 1))
        PV.append(pv_val)
        ev_val = 9 * bm * v0 / 16. * ((dbm * (v0 / vol)**(2 / 3.) - 1)**(3) *
                                      ((v0 / vol)**(2 / 3.) - 1)**2 * (6 - 4 * (v0 / vol)**(2 / 3.)))
        EV.append(ev_val)
    return EV, PV
