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
    In this module you find the workflow 'FleurRelaxWorkChain' for geometry optimization.
"""
from __future__ import absolute_import
from __future__ import print_function
import copy
import numpy as np
import six

from aiida.engine import WorkChain, ToContext, while_, if_
from aiida.engine import calcfunction as cf
from aiida.orm import load_node
from aiida.orm import StructureData, Dict
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.calculation.fleur import FleurCalculation as FleurCalc
from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.common.constants import BOHR_A
from aiida_fleur.tools.StructureData_util import break_symmetry_wf
from aiida_fleur.tools.common_fleur_wf import find_nested_process


class FleurRelaxTorqueWorkChain(WorkChain):
    """
    This workflow performs structure optimization.
    """

    _workflowversion = '0.0.1'

    _default_wf_para = {
        'relax_iter': 5,  # Stop if not converged after so many relaxation steps
        'torque_criterion': 0.001,  # Converge the force until lower this value in atomic units
        'run_final_scf': False,  # Run a final scf on the final relaxed structure
        'relax_alpha': 0.1,
        'break_symmetry': False,

    }

    _default_options = FleurScfWorkChain._default_options

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain, namespace='scf')
        spec.expose_inputs(FleurScfWorkChain,
                           namespace='final_scf',
                           exclude=('structure', 'fleur', 'fleurinp', 'remote_data'),
                           namespace_options={
                               'required': False,
                           })
        spec.input('wf_parameters', valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            if_(cls.should_relax)(cls.converge_scf, cls.check_failure, while_(cls.condition)(
                cls.generate_new_fleurinp,
                cls.converge_scf,
                cls.check_failure,
            )),
            cls.get_results_relax,
            if_(cls.should_run_final_scf)(cls.run_final_scf, cls.get_results_final_scf),
            cls.return_results,
        )

        spec.output('output_relax_wc_para', valid_type=Dict)
        spec.output('optimized_structure', valid_type=StructureData)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INPGEN_MISSING', message='If you want to run a final scf inpgen has to be there.')
        spec.exit_code(350, 'ERROR_DID_NOT_RELAX', message='Optimization cycle did not lead to convergence of forces.')
        spec.exit_code(351, 'ERROR_SCF_FAILED', message='SCF Workchains failed for some reason.')

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain, validate inputs
        """
        self.report('INFO: Started structure relaxation workflow version {}\n'.format(self._workflowversion))

        self.ctx.info = []  # Collects Hints
        self.ctx.warnings = []  # Collects Warnings
        self.ctx.errors = []  # Collects Errors

        # Pre-initialization of some variables
        self.ctx.loop_count = 0  # Counts relax restarts
        self.ctx.max_torques = []  # Collects forces
        self.ctx.reached_relax = False  # Bool if is relaxed
        self.ctx.scf_res = None  # Last scf results
        self.ctx.total_magnetic_moment = None

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        extra_keys = []
        for key in wf_dict.keys():
            if key not in wf_default.keys():
                extra_keys.append(key)
        if extra_keys:
            error = 'ERROR: input wf_parameters for Relax contains extra keys: {}'.format(extra_keys)
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        # Check if final scf can be run
        run_final = wf_dict.get('run_final_scf', False)
        if run_final:
            # We need inpgen to be there
            input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

            # policy, reuse as much as possible from scf namespace
            input_final_scf = input_scf
            if 'remote_data' in input_final_scf:
                del input_final_scf.remote_data
            if 'structure' in input_final_scf:
                del input_final_scf.structure
            if 'fleurinp' in input_final_scf:
                del input_final_scf.fleurinp
            if 'wf_parameters' in input_final_scf:
                del input_final_scf.wf_parameters

            if 'final_scf' in self.inputs:
                # Will defaults of namespace override other given options?
                input_final_scf_given = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='final_scf'))
                for key, val in input_final_scf_given.items():
                    input_final_scf[key] = val

            self.ctx.input_final_scf = input_final_scf
            if 'inpgen' not in input_scf and 'inpgen' not in input_final_scf:
                self.report('Error: Wrong input: inpgen missing for final scf.')
                return self.exit_codes.ERROR_INPGEN_MISSING

        # initialize contents to avoid access failures
        self.ctx.total_energy_last = None  #total_energy
        self.ctx.total_energy_units = None  #total_energy_units
        self.ctx.final_cell = None
        self.ctx.final_atom_positions = None  #atom_positions
        self.ctx.atomtype_info = None

    def should_relax(self):
        """
        Should we run a relaxation or only a final scf
        This allows to call the workchain to run an scf only and makes
        logic of other higher workflows a lot easier
        """
        relaxtype = self.ctx.wf_dict.get('relaxation_type', 'spins')
        if relaxtype is None:
            self.ctx.reached_relax = True
            return False
        else:
            return True

    def converge_scf(self):
        """
        Submits :class:`aiida_fleur.workflows.scf.FleurScfWorkChain`.
        """
        inputs = {}
        if self.ctx.loop_count:
            inputs = self.get_inputs_scf()
        else:
            inputs = self.get_inputs_first_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(scf_res=res)

    def get_inputs_first_scf(self):
        """
        Initialize inputs for the first iteration.
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        input_scf.metadata.label = 'SCF_torques'
        input_scf.metadata.description = 'The SCF workchain converging torques, part of the RelaxTorques'

        if self.ctx.wf_dict['break_symmetry']:
            calc_para = None
            if 'calc_parameters' in input_scf:
                calc_para = input_scf.calc_parameters
            # currently we always break the full symmetry
            break_dict = Dict(dict={'atoms': ['all']})  # for provenance
            broken_sys = break_symmetry_wf(input_scf.structure, wf_para=break_dict, parameterdata=calc_para)
            input_scf.structure = broken_sys['new_structure']
            input_scf.calc_parameters = broken_sys['new_parameters']

        if 'wf_parameters' not in input_scf:
            scf_wf_dict = {}
        else:
            scf_wf_dict = input_scf.wf_parameters.get_dict()

        if 'inpxml_changes' not in scf_wf_dict:
            scf_wf_dict['inpxml_changes'] = []

        scf_wf_dict['mode'] = 'torque'

        input_scf.wf_parameters = Dict(dict=scf_wf_dict)

        return input_scf

    def get_inputs_scf(self):
        """
        Initializes inputs for further iterations.
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        if 'structure' in input_scf:
            del input_scf.structure
            del input_scf.inpgen
            del input_scf.calc_parameters

        if 'wf_parameters' not in input_scf:
            scf_wf_dict = {}
        else:
            scf_wf_dict = input_scf.wf_parameters.get_dict()
            if 'inpxml_changes' in scf_wf_dict:
                old_changes = scf_wf_dict['inpxml_changes']
                new_changes = []
                for change in old_changes:
                    if 'shift_value' not in change[0] and '':
                        new_changes.append(change)
                scf_wf_dict['inpxml_changes'] = new_changes

        scf_wf_dict['mode'] = 'torque'
        input_scf.wf_parameters = Dict(dict=scf_wf_dict)

        scf_wc = self.ctx.scf_res
        last_calc = load_node(scf_wc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid'])

        input_scf.remote_data = last_calc.outputs.remote_folder
        if self.ctx.new_fleurinp:
            input_scf.fleurinp = self.ctx.new_fleurinp

        return input_scf

    def check_failure(self):
        """
        Throws an exit code if scf failed
        """
        try:
            scf_wc = self.ctx.scf_res
        except AttributeError:
            message = 'ERROR: Something went wrong I do not have new atom positions calculation'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_NO_SCF_OUTPUT

        if not scf_wc.is_finished_ok:
            exit_statuses = FleurScfWorkChain.get_exit_statuses(['ERROR_FLEUR_CALCULATION_FAILED'])
            if scf_wc.exit_status == exit_statuses[0]:
                fleur_calc = load_node(scf_wc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid'])
                if fleur_calc.exit_status == FleurCalc.get_exit_statuses(['ERROR_VACUUM_SPILL_RELAX'])[0]:
                    self.control_end_wc('ERROR: Failed due to atom and vacuum overlap')
                    return self.exit_codes.ERROR_VACUUM_SPILL_RELAX
                elif fleur_calc.exit_status == FleurCalc.get_exit_statuses(['ERROR_MT_RADII_RELAX'])[0]:
                    self.control_end_wc('ERROR: Failed due to MT overlap')
                    return self.exit_codes.ERROR_MT_RADII_RELAX
            return self.exit_codes.ERROR_SCF_FAILED

    def condition(self):
        """
        Checks if relaxation criteria is achieved.

        :return: True if structure is optimized and False otherwise
        """
        scf_wc = self.ctx.scf_res

        try:
            x_torques = scf_wc.outputs.output_scf_wc_para['last_x_torques']
            y_torques = scf_wc.outputs.output_scf_wc_para['last_y_torques']

        except (NotExistent, AttributeError):
            # TODO: throw exit code
            # message = 'ERROR: Did not manage to read the largest force'
            # self.control_end_wc(message)
            # return self.exit_codes.ERROR_RELAX_FAILED
            return False
        else:
            self.ctx.max_torques.append(max(x_torques + y_torques))

        largest_now = self.ctx.max_torques[-1]

        if largest_now < self.ctx.wf_dict['torque_criterion']:
            self.report('INFO: Structure is converged to the largest torque ' '{}'.format(self.ctx.max_torques[-1]))
            self.ctx.reached_relax = True
            return False

        self.ctx.loop_count = self.ctx.loop_count + 1
        if self.ctx.loop_count == self.ctx.wf_dict['relax_iter']:
            self.report('INFO: Reached optimization iteration number {}. Largest torque is {}, '
                        'torque criterion is {}'.format(self.ctx.loop_count + 1, largest_now,
                                                       self.ctx.wf_dict['torque_criterion']))
            return False

        self.report('INFO: submit optimization iteration number {}. Largest torque is {}, '
                    'torque criterion is {}'.format(self.ctx.loop_count + 1, largest_now,
                                                   self.ctx.wf_dict['torque_criterion']))

        return True

    def generate_new_fleurinp(self):
        """
        This function fetches relax.xml from the previous iteration and calls
        :meth:`~aiida_fleur.workflows.relax.FleurRelaxWorkChain.analyse_relax()`.
        New FleurinpData is stored in the context.
        """
        from aiida_fleur.data.fleurinpmodifier import  FleurinpModifier

        relax_alpha = self.ctx.wf_dict['relax_alpha']
        scf_wc = self.ctx.scf_res
        x_torques = scf_wc.outputs.output_scf_wc_para.get_dict()['last_x_torques']
        y_torques = scf_wc.outputs.output_scf_wc_para.get_dict()['last_y_torques']
        alphas = scf_wc.outputs.output_scf_wc_para.get_dict()['alphas']
        betas = scf_wc.outputs.output_scf_wc_para.get_dict()['betas']

        new_angles = self.analyse_relax(alphas, betas, x_torques, y_torques, relax_alpha)

        first_fleurcalc = find_nested_process(scf_wc, FleurCalc)
        old_fleurinp = min(first_fleurcalc, key=lambda x: x.pk).inputs.fleurinpdata

        fm = FleurinpModifier(old_fleurinp)
        for i, angle in enumerate(zip(new_angles['alphas'], new_angles['betas'])):
            fm.set_atomgroup(attributedict={'nocoParams': {'beta': angle[1], 'alpha': angle[0]}}, position=i+1)

        new_fleurinpdata = fm.freeze()

        self.ctx.new_fleurinp = new_fleurinpdata

    @staticmethod
    def analyse_relax(alphas, betas, x_torques, y_torques, relax_alpha):
        """
        This function generates a new fleurinp analysing parsed relax.xml from the previous
        calculation.

        :param relax_dict: parsed relax.xml from the previous calculation
        :return new_fleurinp: new FleurinpData object that will be used for next relax iteration
        """
        from numpy import cos, sin

        def rotation_matrix(alpha, beta):
            'This matrix converts local spin directions to the global frame'
            return np.array([[cos(alpha) * cos(beta), -sin(alpha), cos(alpha) * sin(beta)],
                            [sin(alpha) * cos(beta), cos(alpha), sin(alpha) * sin(beta)],
                            [-sin(beta),             0,           cos(beta)]])

        def convert_to_xyz(alpha, beta):
            x = sin(beta) * cos(alpha)
            y = sin(beta) * sin(alpha)
            z = cos(beta)
            return np.array([x, y, z])

        def convert_to_angles(vector):
            alpha = np.arctan2(vector[1], vector[0])
            beta = np.arccos(vector[2]/np.linalg.norm(vector))

            return alpha, beta

        torques = []
        for alpha, beta, x_torque, y_torque in zip(alphas, betas, x_torques, y_torques):
            torque = np.dot(rotation_matrix(alpha, beta), np.array([x_torque, y_torque, 0]))
            torque = np.array(torque)
            if np.linalg.norm(torque) > np.pi / 90:
                torque = torque / np.linalg.norm(torque) * np.pi / 90
            torques.append(np.array(torque))

        spin_coordinates = [np.array(convert_to_xyz(alpha, beta)) for alpha, beta in zip(alphas, betas)]

        new_spin_coordinates = [spin + relax_alpha * torque for spin, torque in zip(spin_coordinates, torques)]
        new_alpha_beta = [convert_to_angles(vector) for vector in new_spin_coordinates]
        new_alpha_beta = {'alphas': [x[0] for x in new_alpha_beta], 'betas': [x[1] for x in new_alpha_beta]}

        return new_alpha_beta

    def should_run_final_scf(self):
        """
        Check if a final scf should be run on the optimized structure
        """
        # Since we run the final scf on the relaxed structure
        return all([self.ctx.wf_dict.get('run_final_scf', False), self.ctx.reached_relax])

    def get_inputs_final_scf(self):
        """
        Initializes inputs for final scf on relaxed structure.
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        input_final_scf = self.ctx.input_final_scf

        if 'wf_parameters' not in input_final_scf:
            # use parameters wf para of relax or defaults
            if 'wf_parameters' not in input_scf:
                scf_wf_dict = {}
            else:
                scf_wf_dict = input_scf.wf_parameters.get_dict()
                if 'inpxml_changes' in scf_wf_dict:
                    old_changes = scf_wf_dict['inpxml_changes']
                    new_changes = []
                    for change in old_changes:
                        if 'shift_value' not in change[0]:
                            new_changes.append(change)
                    scf_wf_dict['inpxml_changes'] = new_changes

            scf_wf_dict['mode'] = 'density'
            input_final_scf.wf_parameters = Dict(dict=scf_wf_dict)
        structure = self.ctx.final_structure
        formula = structure.get_formula()
        input_final_scf.structure = structure
        input_final_scf.fleur = input_scf.fleur
        input_final_scf.metadata.label = 'SCF_final_{}'.format(formula)
        input_final_scf.metadata.description = ('Final SCF workchain running on optimized structure {}, '
                                                'part of relax workchain'.format(formula))

        return input_final_scf

    def run_final_scf(self):
        """
        Run a final scf for charge convergence on the optimized structure
        """
        self.report('INFO: Running final SCF after relaxation.')
        inputs = {}
        inputs = self.get_inputs_final_scf()
        res = self.submit(FleurScfWorkChain, **inputs)

        return ToContext(scf_final_res=res)

    def get_results_relax(self):
        """
        Generates results of the workchain.
        """

        if self.ctx.wf_dict.get('relaxation_type', 'spins') is None:
            input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
            if 'structure' in input_scf:
                structure = input_scf.structure
            elif 'fleurinp' in input_scf:
                structure = input_scf.fleurinp.get_structuredata_ncf()
            else:
                pass
            self.ctx.final_structure = structure
            self.ctx.final_cell = structure.cell
            # The others are already put to None
            return

        try:
            relax_out = self.ctx.scf_res.outputs.output_scf_wc_para
        except NotExistent:
            return self.exit_codes.ERROR_NO_SCF_OUTPUT

        relax_out = relax_out.get_dict()

        try:
            total_energy = relax_out['total_energy']
            total_energy_units = relax_out['total_energy_units']
            last_x_torques = relax_out['last_x_torques']
            last_y_torques = relax_out['last_y_torques']
            alphas = relax_out['alphas']
            betas = relax_out['betas']
        except KeyError:
            return self.exit_codes.ERROR_NO_RELAX_OUTPUT

        self.ctx.total_energy_last = total_energy
        self.ctx.total_energy_units = total_energy_units
        self.ctx.torques_x = last_x_torques
        self.ctx.torques_y = last_y_torques
        self.ctx.alphas = alphas
        self.ctx.betas = betas

    def get_results_final_scf(self):
        """
        Parser some results of final scf
        """

        try:
            scf_out = self.ctx.scf_final_res.outputs.last_fleur_calc_output
        except NotExistent:
            return self.exit_codes.ERROR_NO_SCF_OUTPUT

        scf_out_d = scf_out.get_dict()
        try:
            total_energy = scf_out_d['energy']
            total_energy_units = scf_out_d['energy_units']
        except KeyError:
            self.report('ERROR: Could not parse total energy of final scf run')
            #return self.exit_codes.ERROR_NO_RELAX_OUTPUT

        self.ctx.total_energy_last = total_energy
        self.ctx.total_energy_units = total_energy_units

        if self.ctx.wf_dict.get('relaxation_type', 'spins') is None:
            # we need this for run through
            self.ctx.scf_res = self.ctx.scf_final_res

        #if jspin ==2
        try:
            total_mag = scf_out_d['total_magnetic_moment_cell']
            self.ctx.total_magnetic_moment = total_mag
        except KeyError:
            self.report('ERROR: Could not parse total magnetic moment cell of final scf run')

    def return_results(self):
        """
        This function stores results of the workchain into the output nodes.
        """
        #TODO maybe we want to have a more detailed array output node with the force and
        # position history of all atoms?
        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'energy': self.ctx.total_energy_last,
            'energy_units': self.ctx.total_energy_units,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors,
            'relax_iter_done': self.ctx.loop_count,
            'alphas': self.ctx.alphas,
            'betas': self.ctx.betas,
            'x_torques': self.ctx.torques_x,
            'y_torques': self.ctx.torques_y,
            'total_magnetic_moment_cell': self.ctx.total_magnetic_moment,
            'total_magnetic_moment_cell_units': 'muBohr'
        }
        outnode = Dict(dict=out)

        con_nodes = {}
        try:
            relax_out = self.ctx.scf_res.outputs.last_fleur_calc_output
        except NotExistent:
            relax_out = None
        if relax_out is not None:
            con_nodes['last_fleur_calc_output'] = relax_out

        if all([self.ctx.wf_dict.get('run_final_scf', False), self.ctx.reached_relax]):
            try:
                scf_out = self.ctx.scf_final_res.outputs.last_fleur_calc_output
            except NotExistent:
                scf_out = None
            if relax_out is not None:
                con_nodes['last_scf__output'] = scf_out

        # TODO: for a trajectory output node all corresponding nodes have to go into
        # con_nodes

        if self.ctx.final_structure is not None:
            outdict = create_relax_result_node(output_relax_wc_para=outnode,
                                               optimized_structure=self.ctx.final_structure,
                                               **con_nodes)
        else:
            outdict = create_relax_result_node(output_relax_wc_para=outnode, **con_nodes)

        # return output nodes
        for link_name, node in six.iteritems(outdict):
            self.out(link_name, node)

        if self.ctx.switch_bfgs:
            return self.exit_codes.ERROR_SWITCH_BFGS
        if not self.ctx.reached_relax:
            return self.exit_codes.ERROR_DID_NOT_RELAX

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. It will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards.
        """
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_relax_result_node(**kwargs):
    """
    This calcfunction assures the right provenance (additional links)
    for ALL result nodes it takes any nodes as input
    and return a special set of nodes.
    All other inputs will be connected in the DB to these ourput nodes
    """
    outdict = {}
    for key, val in six.iteritems(kwargs):
        if key == 'output_relax_wc_para':  # should always be present
            outnode = val.clone()  # dublicate node instead of circle (keep DAG)
            outnode.label = 'output_relax_wc_para'
            outnode.description = ('Contains results and information of an FleurRelaxWorkChain run.')
            outdict['output_relax_wc_para'] = outnode

        if key == 'optimized_structure':
            structure = val.clone()  # dublicate node instead of circle (keep DAG)
            structure.label = 'optimized_structure'
            structure.description = ('Relaxed structure result of an FleurRelaxWorkChain run.')
            outdict['optimized_structure'] = structure

    return outdict
