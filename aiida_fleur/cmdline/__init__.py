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
'''
Module for the command line interface of AiiDA-FLEUR
'''
import click
import click_completion
import difflib

from aiida_fleur import __version__
from aiida.cmdline.params import options, types
try:
    #This class was added in AiiDA 2.1.0 and is needed to correctly
    #access the AiiDA profile in these versions
    from aiida.cmdline.groups import VerdiCommandGroup
    command_cls = VerdiCommandGroup
except ImportError:
    command_cls = click.Group

from .launch import cmd_launch
from .data import cmd_data
from .workflows import cmd_workflow
from .visualization import cmd_plot
from .util import options as options_af
from .util import cmd_defaults

# Activate the completion of parameter types provided by the click_completion package
# for bash: eval "$(_AIIDA_FLEUR_COMPLETE=source aiida-fleur)"
click_completion.init()

# Instead of using entrypoints and directly injecting verdi commands into aiida-core
# we created our own separete CLI because verdi will prob change and become
# less material science specific


# Uncomment this for now, has problems with sphinx-click
@click.command('aiida-fleur', cls=command_cls, context_settings={'help_option_names': ['-h', '--help']})
@options.PROFILE(type=types.ProfileParamType(load_profile=True))
# Note, __version__ should always be passed explicitly here,
# because click does not retrieve a dynamic version when installed in editable mode
@click.version_option(__version__, '-v', '--version', message='AiiDA-FLEUR version %(version)s')
def cmd_root(profile):  # pylint: disable=unused-argument
    """CLI for the `aiida-fleur` plugin."""


# To avoid circular imports all commands are not yet connected to the root
# but they have to be here because of bash completion on the other hand, this
# makes them not work with the difflib...
# see how aiida-core does it.

cmd_root.add_command(cmd_launch)
cmd_root.add_command(cmd_data)
cmd_root.add_command(cmd_workflow)
cmd_root.add_command(cmd_plot)

cmd_root.add_command(cmd_defaults)
