#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the worklfow 'lattice_constant' for the calculation of 
of a lattice constant"""

#TODO: print more user info
#  allow different inputs, make things optional(don't know yet how)
#  half number of iteration if you are close to be converged. (therefore one can start with 18 iterations, and if thats not enough run agian 9 or something)
#TODO do birch murnaghan equation of states fit
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
#import sys,os
from ase import *
import numpy as np
from sys import argv

from ase.lattice.surface import *
from ase.io import *
from aiida.orm import Code, CalculationFactory, DataFactory
from aiida.orm import Computer
from aiida.orm import load_node
from aiida.orm.data.singlefile import SinglefileData
from aiida.work.process_registry import ProcessRegistry
from aiida.work.workchain import Outputs, ToContext

#from aiida.work.workfunction import workfunction as wf
from aiida.work.workchain import WorkChain, while_
from aiida.work import async as asy
from aiida.work import submit
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.tools.StructureData_util import rescale, is_structure
#from convergence import fleur_convergence
#from convergence2 import fleur_convergence2
from aiida_fleur.workflows.scf import fleur_scf_wc



StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')


__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


class fleur_eos2_wc(WorkChain):
    """
    This workflow calculates a lattice constant

    :Params: a parameterData node,
    :returns: Success, last result node, list with convergence behavior
    """
    
    _workflowversion = "0.1.0"

    
    @classmethod
    def define(cls, spec):
        super(fleur_eos_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={'fleur_runmax': 4, 
                                       'points' : 9, 
                                       'step' : 0.002, 
                                       'guess' : 1.00,
                                       'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 12},
                                       'walltime_sec':  10*60,
                                       'queue_name' : ''}))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.outline(
            cls.start,
            cls.structures,
            while_(cls.should_run_scf)(
                cls.converge_scf,
                cls.parse_scf,
            ),            
            cls.return_results
        )
        #spec.dynamic_output()

    def start(self):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        self.report('started eos workflow version {}'.format(self._workflowversion))
        self.report("Workchain node identifiers: {}".format(ProcessRegistry().current_calc_node))  
        print('started eos workflow version {}'.format(self._workflowversion))
        print("Workchain node identifiers: {}".format(ProcessRegistry().current_calc_node))        
        ### input check ### ? or done automaticly, how optional?
        self.ctx.last_calc2 = None
        self.ctx.calcs = []
        self.ctx.calcs_future = []
        self.ctx.structures = []
        self.ctx.temp_calc = None
        self.ctx.structurs_uuids = []
        self.ctx.scalelist = []
        self.ctx.volume = []
        self.ctx.i = 0
        self.ctx.last_scf_wc = None
        self.ctx.successful = True#False # TODO get all succesfull from convergence, if all True this
        wf_dict = self.inputs.wf_parameters.get_dict()
        self.ctx.points = wf_dict.get('points', 2)#9
        self.ctx.step = wf_dict.get('step', 0.002)
        self.ctx.guess = wf_dict.get('guess', 1.00)
        self.ctx.serial = wf_dict.get('serial', False)#True
        # set values, or defaults, default: always converge charge density, crit < 0.00002, max 4 fleur runs
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)

    def structures(self):
        """
        Creates structure data nodes with different Volume (lattice constants)
        """
        points = self.ctx.points
        step = self.ctx.step
        guess = self.ctx.guess
        startscale = guess-(points-1)/2*step
        for point in range(points):
            self.ctx.scalelist.append(startscale + point*step)
        self.report('scaling factors which will be calculated:{}'.format(self.ctx.scalelist))
        print 'scaling factors which will be calculated:{}'.format(self.ctx.scalelist)
        self.ctx.structurs = eos_structures(self.inputs.structure, self.ctx.scalelist)
    '''
    # I do not know yet how to deal with several futures in one workflow step, therefore rewrite...
    def converge_scf(self):
        """
        start scf-cycle from Fleur calculation
        """
        #calcs = []
        # run a convergence worklfow# TODO better sumbit or async?
        for struc in self.ctx.structurs:
            inputs = self.get_inputs_scf()
            inputs['structure'] = struc
            self.ctx.volume.append(struc.get_cell_volume())
            self.ctx.structurs_uuids.append(struc.uuid)
            res = submit(fleur_scf_wc,
                      wf_parameters=inputs['wf_parameters'],
                      structure=inputs['structure'], 
                      calc_parameters=inputs['calc_parameters'], 
                      inpgen = inputs['inpgen'], 
                      fleur=inputs['fleur'])# asy async .run( submit()
            self.ctx.calcs_future.append(res)
            #self.ctx.calcs.append(res)
        for future in self.ctx.calcs_future:
            ToContext(temp_calc=future)
            self.ctx.calcs.append(self.ctx.temp_calc)
        return ToContext(temp_calc=res)           
            #print self.ctx.calcs
            #ResultToContext(self.ctx.calcs1.append(res))
            #calcs.append(res)
        #self.ctx.last_calc2 = res#.get('remote_folder', None)
        #return self.ctx.calcs1#ResultToContext(**calcs) #calcs.append(future),
    '''
    def should_run_scf(self):
        """
        Determine whether a calculation should still be run
        """
        return self.ctx.i < len(self.ctx.scalelist)    
    
    def converge_scf(self):
        """
        start scf-cycle from Fleur calculation
        """    
        #calcs = []
        # run a convergence worklfow# TODO better sumbit or async?
        i = self.ctx.i
        struc = self.ctx.structurs[i]
        inputs = self.get_inputs_scf()
        inputs['structure'] = struc
        self.ctx.volume.append(struc.get_cell_volume())
        self.ctx.structurs_uuids.append(struc.uuid)
        self.ctx.i += 1
        res = submit(fleur_scf_wc,
                     wf_parameters=inputs['wf_parameters'],
                     structure=inputs['structure'], 
                     calc_parameters=inputs['calc_parameters'], 
                     inpgen = inputs['inpgen'], 
                     fleur=inputs['fleur'])# asy async .run( submit()
        #    self.ctx.calcs_future.append(res)
        #self.ctx.calcs.append(res)
        #for future in self.ctx.calcs_future:
        #    ToContext(temp_calc=future)
        #    self.ctx.calcs.append(self.ctx.temp_calc)
            
        return ToContext(last_scf_wc=res)           
            #print self.ctx.calcs
            #ResultToContext(self.ctx.calcs1.append(res))
            #calcs.append(res)
        #self.ctx.last_calc2 = res#.get('remote_folder', None)
        #return self.ctx.calcs1#ResultToContext(**calcs) #calcs.append(future),    
 
    
    def get_inputs_scf(self):
        """
        get the inputs for a scf-cycle
        """
        inputs = {}
        # produce the inputs for a convergence worklfow
        # create input from that
        #print 'getting inputs for scf'
        wf_para_dict = self.inputs.wf_parameters.get_dict()
        inputs['wf_parameters'] = wf_para_dict.get('scf_para', None)
        #inputs['structure'] = self.inputs.structure
        if not inputs['wf_parameters']:
            para = {}
            para['resources'] = wf_para_dict.get('resources')
            para['walltime_sec'] = wf_para_dict.get('walltime_sec')
            para['queue_name'] = wf_para_dict.get('queue_name')
            para['serial'] = wf_para_dict.get('serial')
            inputs['wf_parameters'] = ParameterData(dict=para)        
        inputs['calc_parameters'] = self.inputs.calc_parameters
        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur

        return inputs

    def parse_scf(self):
        """
        parses the result of last scf cycle
        """
        print('#####')
        print self.ctx.last_scf_wc


    def return_results(self):
        """
        return the results of the calculations
        """
        # TODO create parameterNode with all results, all total energy and their, scaling
        #factor and lattice constant.
        # TODO: maybe create a standart plot?
        # node : {scaling: list, total_energy: list, structures : list, calculations_outputs : list,
        # convergence : list, nsteps : int, guess :float, stepsize : float, lattice_constant :float, lattice_constant_units : 'Angstroem'
        distancelist = []
        t_energylist = []
        latticeconstant = 0
        
        #print(self.ctx.calcs_future)
        print('#####')
        #print self.ctx.temp_calc        
        #print self.ctx.calcs
        #print(self.ctx.calcs_last)
        #for calc in self.ctx.calcs:
        #    if calc.get('successful', False):
        #        self.ctx.successful = False
        #        # TODO print something
        #    outpara = calc['output_scf_wc_para'].get_dict()
        #    #get total_energy, density distance
        #    #print outpara
        #    t_e = outpara.get('total_energy', -1)
        #    e_u = outpara.get('total_energy_units', 'eV')
        #    dis = outpara.get('distance_charge', -1)
        #    dis_u = outpara.get('distance_charge_units')
        #    t_energylist.append(t_e)
        #    distancelist.append(dis)
        # fit lattice constant
        #a, latticeconstant, c, fit = fit_latticeconstant(self.ctx.scalelist, t_energylist)
        volume, bulk_modulus, bulk_deriv, residuals = Birch_Murnaghan_fit(t_energylist, self.ctx.volume)
        # somehow problem, that fit is 'array'
        #fit_new = []
        #for val in fit:
        #    fit_new.append(val)
        #TODO optimal volume?
        out = {
               'workflow_name' : self.__class__.__name__,
               'scaling': self.ctx.scalelist,
               'initial_structure': self.inputs.structure.uuid,
               'volume' : volume,#self.ctx.volume,
               'volums' : self.ctx.volume,
               'volume_units' : 'A^3',
               'total_energy': t_energylist,
               'total_energy_units' : e_u,
               'structures' : self.ctx.structurs_uuids, 
               'calculations' : [],#self.ctx.calcs1,
               'scf_wfs' : [],#self.converge_scf_uuids,
               'distance_charge' : distancelist, 
               'distance_charge_units' : dis_u,
               'nsteps' : self.ctx.points,
               'guess' : self.ctx.guess , 
               'stepsize' : self.ctx.step,
               'lattice_constant' : latticeconstant, # miss leading, currently scaling
               'lattice_constant_units' : '',
               #'fitresults' : [a, latticeconstant, c], 
               #'fit' : fit_new, 
               'residuals' : residuals,
               'bulk_deriv' : bulk_deriv,
               'bulk_modulus' : bulk_modulus,
               'successful' : self.ctx.successful}
        
        print out
        
        if self.ctx.successful:
            self.report('Done, Equation of states calculation complete')
            print 'Done, Equation of states calculation complete'
        else:
            self.report('Done, but something went wrong.... Properly some individual calculation failed or a scf-cylcle did not reach the desired distance.')
            print 'Done, but something went wrong.... Properly some individual calculation failed or a scf-cylcle did not reach the desired distance.'
 
        # output must be aiida Data types.        
        outdict = {}
        outdict['output_eos_wc_para']  = ParameterData(dict=out)
        print outdict
        for link_name, node in outdict.iteritems():
            self.out(link_name, node)        # return success, and the last calculation outputs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='lattice constant calculation with Fleur. Do scf-cycles for a structure with different scalling.')
    parser.add_argument('--wf_para', type=ParameterData, dest='wf_parameters',
                        help='Parameter data node, specifing workflow parameters', required=False)
    parser.add_argument('--inpgen', type=Code, dest='inpgen',
                        help='The inpgen code node to use', required=True)
    parser.add_argument('--fleur', type=Code, dest='fleur',
                        help='The FLEUR code node to use', required=True)
    parser.add_argument('--structure', type=StructureData, dest='structure',
                        help='The crystal structure node', required=True)
    parser.add_argument('--calc_para', type=ParameterData, dest='calc_parameters',
                        help='Parameters for the FLEUR calculation', required=False)
    args = parser.parse_args()
    res = fleur_eos_wc.run(wf_parameters=args.wf_parameters, structure=args.structure, calc_parameters=args.calc_parameters, inpgen = args.inpgen, fleur=args.fleur)

def eos_structures(inp_structure, scalelist):
    """
    Creates many rescalled StrucutureData nodes out of a crystal structure.
    Keeps the provanance in the database.

    :param StructureData, a StructureData node (pk, sor uuid)
    :param scalelist, list of floats, scaling factors for the cell

    :returns: list of New StructureData nodes with rescalled structure, which are linked to input Structure
    """
    from aiida.orm.data.base import Float
    #test if structure:
    structure = is_structure(inp_structure)
    if not structure:
        #TODO: log something
        return None
    re_structures = []

    for scale in scalelist:
        s = rescale(structure, Float(scale))
        re_structures.append(s)
    return re_structures


def fit_latticeconstant(scale, eT):
    """
    Extract the lattice constant out of an parabola fit.
    
    scale : list of scales, or lattice constants
    eT: list of total energies
    """
    # TODO Fit teh real function Mun... not a parabola
    import numpy as np
    # call fitt pol2 # or something else
    #def func(x, a, b, c):
    #    return a*x**2 + b*x + c
    f1 = np.polyfit(scale,eT,2)
    a0 = f1[0]
    a1 = f1[1]
    a2 = f1[2]
    la = -0.5*a1/a0
    c = a2 - a1**2/a2
    return a0,la,c, f1

def parabola(x, a, b, c):
    return a*x**2 + b*x + c




def Birch_Murnaghan_fit(energies, volumes):
    """
    least squares fit of a Birch-Murnaghan equation of state curve. From delta project
    containing in its columns the volumes in A^3/atom and energies in eV/atom

    :params energies: list of total energies eV/atom
    :params volumes: list of volumes in A^3/atom
    
    #volume, bulk_modulus, bulk_deriv, residuals = Birch_Murnaghan_fit(data)
    """
    fitdata = np.polyfit(volumes[:]**(-2./3.), energies[:], 3, full=True)
    ssr = fitdata[1]
    sst = np.sum((energies[:] - np.average(energies[:]))**2.)
    residuals0 = ssr/sst
    deriv0 = np.poly1d(fitdata[0])
    deriv1 = np.polyder(deriv0, 1)
    deriv2 = np.polyder(deriv1, 1)
    deriv3 = np.polyder(deriv2, 1)

    volume0 = 0
    x = 0
    for x in np.roots(deriv1):
        if x > 0 and deriv2(x) > 0:
            volume0 = x**(-3./2.)
            break

    if volume0 == 0:
        print('Error: No minimum could be found')
        exit()
    
    derivV2 = 4./9. * x**5. * deriv2(x)
    derivV3 = (-20./9. * x**(13./2.) * deriv2(x) -
        8./27. * x**(15./2.) * deriv3(x))
    bulk_modulus0 = derivV2 / x**(3./2.)
    bulk_deriv0 = -1 - x**(-3./2.) * derivV3 / derivV2

    return volume0, bulk_modulus0, bulk_deriv0, residuals0


