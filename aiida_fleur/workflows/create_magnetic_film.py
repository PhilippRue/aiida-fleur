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
    In this module you find the workflow 'FleurCreateMagneticWorkChain' for creation of relaxed
    film deposited on a cubic substrate.
"""

from __future__ import absolute_import
import copy
import six

from aiida.engine import WorkChain, if_
from aiida.engine import calcfunction as cf
from aiida.plugins import DataFactory
from aiida.orm import StructureData, Dict
from aiida.common import AttributeDict

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.workflows.eos import FleurEosWorkChain
from aiida_fleur.workflows.base_relax import FleurBaseRelaxWorkChain

# pylint: disable=invalid-name
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name

class FleurCreateMagneticWorkChain(WorkChain):
    """
        This workflow creates relaxed magnetic film on a substrate.
    """

    _workflowversion = "0.1.0"

    _default_options = {
        'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        'max_wallclock_seconds': 2 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}}

    _wf_default = {
        'lattice': 'fcc',
        'miller': [[-1, 1, 0],
                   [0, 0, 1],
                   [1, 1, 0]],
        'host_symbol': 'Pt',
        'latticeconstant': 4.0,
        'size': (1, 1, 5),
        'replacements': {0: 'Fe', -1: 'Fe'},
        'decimals': 10,
        'pop_last_layers': 1,

        'total_number_layers': 4,
        'num_relaxed_layers': 2,

        'eos_needed': False,
        'relax_needed': True
    }

    @classmethod
    def define(cls, spec):
        super(FleurCreateMagneticWorkChain, cls).define(spec)
        spec.expose_inputs(FleurEosWorkChain, namespace='eos', exclude=('structure', ))
        spec.expose_inputs(FleurBaseRelaxWorkChain, namespace='relax', exclude=('structure', ))
        spec.input("wf_parameters", valid_type=Dict, required=False)
        spec.input("eos_output", valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            if_(cls.eos_needed)(
                cls.run_eos,
            ),
            if_(cls.relax_needed)(
                cls.run_relax,
            ),
            cls.make_magnetic
        )

        spec.output('magnetic_structure', valid_type=StructureData)

        # exit codes
        spec.exit_code(401, 'ERROR_NOT_SUPPORTED_LATTICE',
                       message="Specified substrate has to be bcc or fcc.")
        spec.exit_code(402, 'ERROR_NO_EOS_OUTPUT',
                       message="eos_output was not specified, however, 'eos_needed' was set to "
                               "True.")

    def eos_needed(self):
        """
        Returns True if EOS WorkChain should be submitted
        """
        return self.ctx.wf_dict['eos_needed']

    def prepare_eos(self):
        """
        Initialize inputs for eos workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = AttributeDict(self.exposed_inputs(FleurEosWorkChain, namespace='eos'))
        inputs.structure = self.create_substrate_bulk()

        if not isinstance(inputs.structure, StructureData):
            return inputs['structure'] # throws an exit code thrown in create_substrate_bulk

        return inputs

    def run_eos(self):
        """
        Optimize lattice parameter for substrate bulk structure.
        """
        inputs = {}
        inputs = self.prepare_eos()
        res = self.submit(FleurEosWorkChain, **inputs)
        self.to_context(eos_wc=res)

    def create_substrate_bulk(self):
        """
        Create a bulk structure of a substrate.
        """
        lattice = self.ctx.wf_dict['lattice']
        if lattice == 'fcc':
            from ase.lattice.cubic import FaceCenteredCubic
            structure_factory = FaceCenteredCubic
        elif lattice == 'bcc':
            from ase.lattice.cubic import BodyCenteredCubic
            structure_factory = BodyCenteredCubic
        else:
            return self.ctx.exit_codes.ERROR_NOT_SUPPORTED_LATTICE

        miller = [[1, 0, 0],
                  [0, 1, 0],
                  [0, 0, 1]]
        host_symbol = self.ctx.wf_dict['host_symbol']
        latticeconstant = self.ctx.wf_dict['latticeconstant']
        size = (1, 1, 1)
        structure = structure_factory(miller=miller, symbol=host_symbol, pbc=(1, 1, 1),
                                      latticeconstant=latticeconstant, size=size)

        return StructureData(ase=structure)

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Spin Stiffness calculation'
                    ' convergence calculation workflow version {}\n'.format(self._workflowversion))

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.energy_dict = []

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = copy.deepcopy(self._wf_default)
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        if not wf_dict['eos_needed'] and 'eos_output' not in self.inputs:
            return self.exit_codes.ERROR_NO_EOS_OUTPUT

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

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

    def relax_needed(self):
        """
        Returns true if interlayer relaxation should be performed.
        """
        return self.ctx.wf_dict['relax_needed']

    def run_relax(self):
        """
        Optimize interlayer distance.
        """
        inputs = {}
        inputs = self.prepare_relax()
        res = self.submit(FleurBaseRelaxWorkChain, **inputs)
        self.to_context(relax_wc=res)

    def prepare_relax(self):
        """
        Initialise inputs for Relax workchain
        """
        inputs = AttributeDict(self.exposed_inputs(FleurBaseRelaxWorkChain, namespace='relax'))
        inputs.structure = self.create_film_to_relax()

        if not isinstance(inputs.structure, StructureData):
            return inputs.structure # throws an exit code thrown in create_film_to_relax

        return inputs

    def create_film_to_relax(self):
        """
        Create a film structure those interlayers will be relaxed.
        """
        from aiida_fleur.tools.StructureData_util import create_manual_slab_ase, center_film

        miller = self.ctx.wf_dict['miller']
        host_symbol = self.ctx.wf_dict['host_symbol']
        if not self.ctx.wf_dict['eos_needed']:
            eos_output = self.inputs.eos_output
        else:
            eos_output = self.ctx.eos_wc.outputs.output_eos_wc_para
        scaling_parameter = eos_output.get_dict()['scaling_gs']
        latticeconstant = self.ctx.wf_dict['latticeconstant'] * scaling_parameter
        size = self.ctx.wf_dict['size']
        replacements = self.ctx.wf_dict['replacements']
        pop_last_layers = self.ctx.wf_dict['pop_last_layers']
        decimals = self.ctx.wf_dict['decimals']
        structure = create_manual_slab_ase(miller=miller, host_symbol=host_symbol,
                                           latticeconstant=latticeconstant, size=size,
                                           replacements=replacements, decimals=decimals,
                                           pop_last_layers=pop_last_layers)

        self.ctx.substrate = create_manual_slab_ase(miller=miller, host_symbol=host_symbol,
                                                    latticeconstant=latticeconstant, size=(1, 1, 1),
                                                    replacements=None, decimals=decimals)

        centered_structure = center_film(StructureData(ase=structure))

        return centered_structure

    def make_magnetic(self):
        """
        Analuses outputs of previous steps and generated the final
        structure suitable for magnetic film calculations.
        """
        from aiida_fleur.tools.StructureData_util import magnetic_slab_from_relaxed

        if self.ctx.wf_dict['relax_needed']:
            optimized_structure = self.ctx.relax_wc.outputs.optimized_structure
        else:
            optimized_structure = self.inputs.optimized_structure

        magnetic = magnetic_slab_from_relaxed(optimized_structure, self.ctx.substrate,
                                              self.ctx.wf_dict['total_number_layers'],
                                              self.ctx.wf_dict['num_relaxed_layers'])

        magnetic = save_structure(magnetic)

        self.out('magnetic_structure', magnetic)


@cf
def save_structure(structure):
    """
    Save a structure data node to provide correct provenance.
    """
    structure_return = structure.clone()
    return structure_return