'fleur_runmax': 10,                         # needed for SCF
'density_converged' : 0.00005,              # needed for SCF
'serial' : False,                           # needed for SCF
'itmax_per_run' : 30,                       # needed for SCF
'beta' : {'all' : 1.57079},                 # see description below
'alpha_mix' : 0.015,                        # sets mixing parameter alpha
'sqas_theta' : [0.0, 1.57079, 1.57079],     # sets SOC theta values
'sqas_phi' : [0.0, 0.0, 1.57079],           # sets SOC phi values
'soc_off' : [],                             # switches off SOC on a given atom
'prop_dir' : [1.0, 0.0, 0.0],               # sets a propagation direction of a q-vector
'q_vectors': [[0.0, 0.0, 0.0],              # set a set of q-vectors to calculate DMI energies
                [0.125, 0.0, 0.0],
                [0.250, 0.0, 0.0],
                [0.375, 0.0, 0.0]],
'ref_qss' : [0.0, 0.0, 0.0],                # sets a q-vector for the reference calculation
'input_converged' : False,                  # True, if charge density from remote folder has to be converged
'inpxml_changes' : []