#!/usr/bin/env python
"""
You find the usual econfig for all elements in the periodic table.
"""
# TOD
# FLEUR econfig=[core states|valence states] 
econfiguration = {
    1: {'mass': 1.00794, 'name': 'Hydrogen', 'symbol': 'H', 'econfig': '1s' },
    2: {'mass': 4.002602, 'name': 'Helium', 'symbol': 'He', 'econfig': ''},
    3: {'mass': 6.941, 'name': 'Lithium', 'symbol': 'Li', 'econfig': ''},
    4: {'mass': 9.012182, 'name': 'Beryllium', 'symbol': 'Be', 'econfig': ''},
    5: {'mass': 10.811, 'name': 'Boron', 'symbol': 'B', 'econfig': ''},
    6: {'mass': 12.0107, 'name': 'Carbon', 'symbol': 'C', 'econfig': ''},
    7: {'mass': 14.0067, 'name': 'Nitrogen', 'symbol': 'N', 'econfig': ''},
    8: {'mass': 15.9994, 'name': 'Oxygen', 'symbol': 'O', 'econfig': ''},
    9: {'mass': 18.9984032, 'name': 'Fluorine', 'symbol': 'F', 'econfig': ''},
    10: {'mass': 20.1797, 'name': 'Neon', 'symbol': 'Ne', 'econfig': ''},
    11: {'mass': 22.98977, 'name': 'Sodium', 'symbol': 'Na', 'econfig': ''},
    12: {'mass': 24.305, 'name': 'Magnesium', 'symbol': 'Mg', 'econfig': ''},
    13: {'mass': 26.981538, 'name': 'Aluminium', 'symbol': 'Al', 'econfig': ''},
    14: {'mass': 28.0855, 'name': 'Silicon', 'symbol': 'Si', 'econfig': ''},
    15: {'mass': 30.973761, 'name': 'Phosphorus', 'symbol': 'P', 'econfig': ''},
    16: {'mass': 32.065, 'name': 'Sulfur', 'symbol': 'S', 'econfig': ''},
    17: {'mass': 35.453, 'name': 'Chlorine', 'symbol': 'Cl', 'econfig': ''},
    18: {'mass': 39.948, 'name': 'Argon', 'symbol': 'Ar', 'econfig': ''},
    19: {'mass': 39.0983, 'name': 'Potassium', 'symbol': 'K', 'econfig': ''},
    20: {'mass': 40.078, 'name': 'Calcium', 'symbol': 'Ca', 'econfig': ''},
    21: {'mass': 44.955912, 'name': 'Scandium', 'symbol': 'Sc', 'econfig': ''},
    22: {'mass': 47.867, 'name': 'Titanium', 'symbol': 'Ti', 'econfig': ''},
    23: {'mass': 50.9415, 'name': 'Vanadium', 'symbol': 'V', 'econfig': ''},
    24: {'mass': 51.9961, 'name': 'Chromium', 'symbol': 'Cr', 'econfig': ''},
    25: {'mass': 54.938045, 'name': 'Manganese', 'symbol': 'Mn', 'econfig': ''},
    26: {'mass': 55.845, 'name': 'Iron', 'symbol': 'Fe', 'econfig': ''},
    27: {'mass': 58.933195, 'name': 'Cobalt', 'symbol': 'Co', 'econfig': ''},
    28: {'mass': 58.6934, 'name': 'Nickel', 'symbol': 'Ni', 'econfig': ''},
    29: {'mass': 63.546, 'name': 'Copper', 'symbol': 'Cu', 'econfig': ''},
    30: {'mass': 65.38, 'name': 'Zinc', 'symbol': 'Zn', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2'},
    31: {'mass': 69.723, 'name': 'Gallium', 'symbol': 'Ga', 'econfig': ''},
    32: {'mass': 72.64, 'name': 'Germanium', 'symbol': 'Ge', 'econfig': ''},
    33: {'mass': 74.9216, 'name': 'Arsenic', 'symbol': 'As', 'econfig': ''},
    34: {'mass': 78.96, 'name': 'Selenium', 'symbol': 'Se', 'econfig': ''},
    35: {'mass': 79.904, 'name': 'Bromine', 'symbol': 'Br', 'econfig': ''},
    36: {'mass': 83.798, 'name': 'Krypton', 'symbol': 'Kr', 'econfig': ''},
    37: {'mass': 85.4678, 'name': 'Rubidium', 'symbol': 'Rb', 'econfig': ''},
    38: {'mass': 87.62, 'name': 'Strontium', 'symbol': 'Sr', 'econfig': ''},
    39: {'mass': 88.90585, 'name': 'Yttrium', 'symbol': 'Y', 'econfig': ''},
    40: {'mass': 91.224, 'name': 'Zirconium', 'symbol': 'Zr', 'econfig': ''},
    41: {'mass': 92.90638, 'name': 'Niobium', 'symbol': 'Nb', 'econfig': ''},
    42: {'mass': 95.96, 'name': 'Molybdenum', 'symbol': 'Mo', 'econfig': ''},
    43: {'mass': 98.0, 'name': 'Technetium', 'symbol': 'Tc', 'econfig': ''},
    44: {'mass': 101.07, 'name': 'Ruthenium', 'symbol': 'Ru', 'econfig': ''},
    45: {'mass': 102.9055, 'name': 'Rhodium', 'symbol': 'Rh', 'econfig': ''},
    46: {'mass': 106.42, 'name': 'Palladium', 'symbol': 'Pd', 'econfig': ''},
    47: {'mass': 107.8682, 'name': 'Silver', 'symbol': 'Ag', 'econfig': ''},
    48: {'mass': 112.411, 'name': 'Cadmium', 'symbol': 'Cd', 'econfig': '[Ar] 4s2 3d10 4p6 | 4d10 5s2'},
    49: {'mass': 114.818, 'name': 'Indium', 'symbol': 'In', 'econfig': ''},
    50: {'mass': 118.71, 'name': 'Tin', 'symbol': 'Sn', 'econfig': ''},
    51: {'mass': 121.76, 'name': 'Antimony', 'symbol': 'Sb', 'econfig': ''},
    52: {'mass': 127.6, 'name': 'Tellurium', 'symbol': 'Te', 'econfig': ''},
    53: {'mass': 126.90447, 'name': 'Iodine', 'symbol': 'I', 'econfig': ''},
    54: {'mass': 131.293, 'name': 'Xenon', 'symbol': 'Xe', 'econfig': ''},
    55: {'mass': 132.9054519, 'name': 'Caesium', 'symbol': 'Cs', 'econfig': ''},
    56: {'mass': 137.327, 'name': 'Barium', 'symbol': 'Ba', 'econfig': ''},
    57: {'mass': 138.90547, 'name': 'Lanthanum', 'symbol': 'La', 'econfig': ''},
    58: {'mass': 140.116, 'name': 'Cerium', 'symbol': 'Ce', 'econfig': ''},
    59: {'mass': 140.90765, 'name': 'Praseodymium', 'symbol': 'Pr', 'econfig': ''},
    60: {'mass': 144.242, 'name': 'Neodymium', 'symbol': 'Nd', 'econfig': ''},
    61: {'mass': 145.0, 'name': 'Promethium', 'symbol': 'Pm', 'econfig': ''},
    62: {'mass': 150.36, 'name': 'Samarium', 'symbol': 'Sm', 'econfig': ''},
    63: {'mass': 151.964, 'name': 'Europium', 'symbol': 'Eu', 'econfig' : '[Kr] 4d10 | 4f7 5s2 5p6 6s2'},
    64: {'mass': 157.25, 'name': 'Gadolinium', 'symbol': 'Gd', 'econfig': ''},
    65: {'mass': 158.92535, 'name': 'Terbium', 'symbol': 'Tb', 'econfig': ''},
    66: {'mass': 162.5, 'name': 'Dysprosium', 'symbol': 'Dy', 'econfig': ''},
    67: {'mass': 164.93032, 'name': 'Holmium', 'symbol': 'Ho', 'econfig': ''},
    68: {'mass': 167.259, 'name': 'Erbium', 'symbol': 'Er', 'econfig': ''},
    69: {'mass': 168.93421, 'name': 'Thulium', 'symbol': 'Tm', 'econfig': ''},
    70: {'mass': 173.054, 'name': 'Ytterbium', 'symbol': 'Yb', 'econfig': ''},
    71: {'mass': 174.9668, 'name': 'Lutetium', 'symbol': 'Lu', 'econfig': '[Kr] 4d10 | 4f14 5s2 5p6 5d1 6s2'},
    72: {'mass': 178.49, 'name': 'Hafnium', 'symbol': 'Hf', 'econfig': ''},
    73: {'mass': 180.94788, 'name': 'Tantalum', 'symbol': 'Ta', 'econfig': ''},
    74: {'mass': 183.84, 'name': 'Tungsten', 'symbol': 'W', 'econfig' : '[Kr] 4d10 4f7 5p6 | 5s2 6s2 5d4'},
    75: {'mass': 186.207, 'name': 'Rhenium', 'symbol': 'Re', 'econfig': ''},
    76: {'mass': 190.23, 'name': 'Osmium', 'symbol': 'Os', 'econfig': ''},
    77: {'mass': 192.217, 'name': 'Iridium', 'symbol': 'Ir', 'econfig': ''},
    78: {'mass': 195.084, 'name': 'Platinum', 'symbol': 'Pt', 'econfig': ''},
    79: {'mass': 196.966569, 'name': 'Gold', 'symbol': 'Au', 'econfig': ''},
    80: {'mass': 200.59, 'name': 'Mercury', 'symbol': 'Hg', 'econfig': '[Kr] 5s2 4d10 4f14 | 5p6 5d10 6s2'},
    81: {'mass': 204.3833, 'name': 'Thallium', 'symbol': 'Tl', 'econfig': ''},
    82: {'mass': 207.2, 'name': 'Lead', 'symbol': 'Pb', 'econfig': ''},
    83: {'mass': 208.9804, 'name': 'Bismuth', 'symbol': 'Bi', 'econfig': ''},
    84: {'mass': 209.0, 'name': 'Polonium', 'symbol': 'Po', 'econfig': '[Xe] 4f14 | 5d10 6s2 6p4'},
    85: {'mass': 210.0, 'name': 'Astatine', 'symbol': 'At', 'econfig': ''},
    86: {'mass': 222.0, 'name': 'Radon', 'symbol': 'Rn', 'econfig': ''},
    87: {'mass': 223.0, 'name': 'Francium', 'symbol': 'Fr', 'econfig': ''},
    88: {'mass': 226.0, 'name': 'Radium', 'symbol': 'Ra', 'econfig': ''},
    89: {'mass': 227.0, 'name': 'Actinium', 'symbol': 'Ac', 'econfig': ''},
    90: {'mass': 232.03806, 'name': 'Thorium', 'symbol': 'Th', 'econfig': ''},
    91: {'mass': 231.03588, 'name': 'Protactinium', 'symbol': 'Pa', 'econfig': ''},
    92: {'mass': 238.02891, 'name': 'Uranium', 'symbol': 'U', 'econfig': ''},
    93: {'mass': 237.0, 'name': 'Neptunium', 'symbol': 'Np', 'econfig': ''},
    94: {'mass': 244.0, 'name': 'Plutonium', 'symbol': 'Pu', 'econfig': ''},
    95: {'mass': 243.0, 'name': 'Americium', 'symbol': 'Am', 'econfig': ''},
    96: {'mass': 247.0, 'name': 'Curium', 'symbol': 'Cm', 'econfig': ''},
    97: {'mass': 247.0, 'name': 'Berkelium', 'symbol': 'Bk', 'econfig': ''},
    98: {'mass': 251.0, 'name': 'Californium', 'symbol': 'Cf', 'econfig': ''},
    99: {'mass': 252.0, 'name': 'Einsteinium', 'symbol': 'Es', 'econfig': ''},
    100: {'mass': 257.0, 'name': 'Fermium', 'symbol': 'Fm', 'econfig': ''},
    101: {'mass': 258.0, 'name': 'Mendelevium', 'symbol': 'Md', 'econfig': ''},
    102: {'mass': 259.0, 'name': 'Nobelium', 'symbol': 'No', 'econfig': ''},
    103: {'mass': 262.0, 'name': 'Lawrencium', 'symbol': 'Lr', 'econfig': ''},
    104: {'mass': 267.0, 'name': 'Rutherfordium', 'symbol': 'Rf', 'econfig': ''},
    105: {'mass': 268.0, 'name': 'Dubnium', 'symbol': 'Db', 'econfig': ''},
    106: {'mass': 271.0, 'name': 'Seaborgium', 'symbol': 'Sg', 'econfig': ''},
    107: {'mass': 272.0, 'name': 'Bohrium', 'symbol': 'Bh', 'econfig': ''},
    108: {'mass': 270.0, 'name': 'Hassium', 'symbol': 'Hs', 'econfig': ''},
    109: {'mass': 276.0, 'name': 'Meitnerium', 'symbol': 'Mt', 'econfig': ''},
    110: {'mass': 281.0, 'name': 'Darmstadtium', 'symbol': 'Ds', 'econfig': ''},
    111: {'mass': 280.0, 'name': 'Roentgenium', 'symbol': 'Rg', 'econfig': ''},
    112: {'mass': 285.0, 'name': 'Copernicium', 'symbol': 'Cn', 'econfig': ''},
    114: {'mass': 289.0, 'name': 'Flerovium', 'symbol': 'Fl', 'econfig': ''},
    116: {'mass': 293.0, 'name': 'Livermorium', 'symbol': 'Lv', 'econfig': ''},
}

element_delta_defaults = {} # for workflow purposes

element_max_para = {} # for workflow purposes


def get_econfig(element):
    if isinstance(element, int):
        econ = econfiguration.get(element, {}).get('econfig', None)
        return econ
    elif isinstance(element, str):
         atomic_names = {data['symbol']: num for num,
                         data in econfiguration.iteritems()}
         element_num = atomic_names.get(element, None)
         econ = econfiguration.get(element_num, {}).get('econfig', None)
        return econ
    else:
        print('INPUTERROR: element has to be and int or string')
        return None 