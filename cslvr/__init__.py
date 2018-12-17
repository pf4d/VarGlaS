from __future__ import absolute_import
__version__    = '2017.2.0'
__author__     = 'Evan Cummings, Douglas Brinkerhoff, Jesse Johnson, Aaron St. George'
__license__    = 'LGPL-3'
__maintainer__ = 'Evan Cummings'
__email__      = 'cummings.evan@gmail.com'

__all__ = []

import pkgutil
import inspect
import matplotlib as mpl
mpl.rcParams['font.family']          = 'serif'
mpl.rcParams['legend.fontsize']      = 'medium'
mpl.rcParams['text.usetex']          = True
mpl.rcParams['text.latex.preamble']  = ['\usepackage[mathscr]{euscript}']
#mpl.rcParams['contour.negative_linestyle']   = 'solid'

# conditional fix (issue #107) :
import ufl
ufl.algorithms.apply_derivatives.CONDITIONAL_WORKAROUND = True

for loader, name, is_pkg in pkgutil.walk_packages(__path__):
	module = loader.find_module(name).load_module(name)
	for name, value in inspect.getmembers(module):
		if name.startswith('__'):
			continue

		globals()[name] = value
		__all__.append(name)

# use the namespace of ``dolfin_adjoint`` :
from dolfin              import *
from dolfin_adjoint      import *

# cslvr classes :
from .age                 import *
from .balancevelocity     import *
from .d1model             import *
from .d2model             import *
from .d3model             import *
from .datafactory         import *
from .energy              import *
from .helper              import *
from .inputoutput         import *
from .mass                import *
from .meshing             import *
from .model               import *
from .momentumbp          import *
from .momentumfirn        import *
from .momentumhybrid      import *
from .momentumplanestrain import *
from .momentumstokes      import *
from .momentum            import *
from .physics             import *
from .stressbalance       import *
from .surfacemassbalance  import *
