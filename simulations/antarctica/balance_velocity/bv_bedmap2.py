import varglas.solvers            as solvers
import varglas.model              as model
from varglas.helper               import default_config
from varglas.data.data_factory    import DataFactory
from varglas.mesh.mesh_factory    import MeshFactory
from varglas.io                   import DataInput, DataOutput
from fenics                       import *
from time                         import time
from termcolor                    import colored

thklim = 10.0

# collect the raw data :
bm1 = DataFactory.get_bedmap1(thklim = thklim)
bm2 = DataFactory.get_bedmap2(thklim = thklim)

# load a mesh :
mesh  = MeshFactory.get_antarctica_2D_medium()

# create data objects to use with varglas :
d1     = DataInput(bm1, mesh=mesh)
d2     = DataInput(bm2, mesh=mesh)

# get projections for use with FEniCS :
S     = d2.get_expression("S",        near=True)
B     = d2.get_expression("B",        near=True)
adot  = d1.get_expression("acca",     near=True)

config = default_config()
config['output_path']               = 'results/'
config['balance_velocity']['kappa'] = 5.0
config['model_order']               = 'SSA'

model = model.Model(config)
model.set_mesh(mesh)
model.set_geometry(S, B, deform=False)
model.initialize_variables()

model.init_adot(adot)

F = solvers.BalanceVelocitySolver(model, config)

t0 = time()
F.solve()
tf = time()

model.save_xml(model.Ubar, 'Ubar')

#do = DataOutput(out_dir)
#do.write_matlab(bm1, model.Ubar, 'Ubar_5', val=0.0)

# calculate total time to compute
s = tf - t0
m = s / 60.0
h = m / 60.0
s = s % 60
m = m % 60
if model.MPI_rank == 0:
  s    = "Total time to compute: %02d:%02d:%02d" % (h,m,s)
  text = colored(s, 'red', attrs=['bold'])
  print text





