from varglas          import *
from scipy            import random
from fenics           import *
from dolfin_adjoint   import *
import sys

# set the relavent directories :
var_dir = 'dump/vars_low/'  # directory from gen_vars.py
out_dir = 'dump/low/'            # base directory to save

# create HDF5 files for saving and loading data :
fmeshes = HDF5File(mpi_comm_world(), var_dir + 'submeshes.h5',     'r')
fdata   = HDF5File(mpi_comm_world(), var_dir + 'state.h5',         'r')

# create 3D model for stokes solves :
d3model = D3Model(fdata, out_dir)

# init subdomains and boundary meshes :
d3model.set_subdomains(fdata)
d3model.set_srf_mesh(fmeshes)
d3model.set_bed_mesh(fmeshes)

## setup full-stokes functionspaces with 'mini' enriched elements :
#d3model.generate_stokes_function_spaces(kind='mini')

# initialize the 3D model vars :
d3model.init_S(fdata)
d3model.init_B(fdata)
d3model.init_mask(fdata)
d3model.init_q_geo(d3model.ghf)
d3model.init_T_surface(fdata)
d3model.init_S_ring(fdata)
d3model.init_U_ob(fdata, fdata)
d3model.init_U_mask(fdata)
d3model.init_time_step(1e-6)
d3model.init_E(1.0)

fUin = HDF5File(mpi_comm_world(), out_dir + 'U3.h5', 'r')
d3model.init_U(fUin)

#===============================================================================
# 2D model for for balance velocity :

bedmodel = D2Model(d3model.bedmesh, out_dir)

bedmodel.assign_submesh_variable(bedmodel.S,      d3model.S)
bedmodel.assign_submesh_variable(bedmodel.B,      d3model.B)
bedmodel.assign_submesh_variable(bedmodel.S_ring,   d3model.S_ring)

# solve the balance velocity :
bv = BalanceVelocity(bedmodel, kappa=5.0)
bv.solve(annotate=False)

# assign the balance velocity to the 3D model's bed :
d3model.assign_submesh_variable(d3model.d_x,  bedmodel.d_x)
d3model.assign_submesh_variable(d3model.d_y,  bedmodel.d_y)
d3model.assign_submesh_variable(d3model.Ubar, bedmodel.Ubar)

# extrude the bed values up the column : 
d_x_e  = d3model.vert_extrude(d3model.d_x,  d='up')
d_y_e  = d3model.vert_extrude(d3model.d_y,  d='up')
Ubar_e = d3model.vert_extrude(d3model.Ubar, d='up')

# set the appropriate variable to be the function extruded :
d3model.init_d_x(d_x_e)
d3model.init_d_y(d_y_e)
d3model.init_Ubar(Ubar_e)

#===============================================================================
# create boundary function spaces for saving variables :
Qb  = FunctionSpace(d3model.bedmesh, 'CG', 1)
Qs  = FunctionSpace(d3model.srfmesh, 'CG', 1)
Q3s = MixedFunctionSpace([Qs]*3)

# functions over appropriate surfaces for saving :
beta   = Function(Qb,  name='beta_SIA')
U_ob   = Function(Qs,  name='U_ob')
Tb     = Function(Qb,  name='Tb')
Us     = Function(Q3s, name='Us')
Wb     = Function(Qb,  name='Wb')
Mb     = Function(Qb,  name='Mb')
betab  = Function(Qb,  name="beta_control")
alphab = Function(Qb,  name="alpha_control")

a_f    = XDMFFile(d3model.bedmesh.mpi_comm(),
                  d3model.out_dir + 'xdmf/alpha_control.xdmf')

# saving the regularization and cost functional values for convergence :
Rs  = []
Js  = []
J1s = []
J2s = []
Ms  = []

#===============================================================================
# generate initial traction field :
d3model.init_T(d3model.T_surface)
d3model.init_beta_SIA()
#d3model.init_beta(1e4)
#bedmodel.init_beta_SIA()
#bedmodel.init_T(bedmodel.T_surface)

nparams = {'newton_solver' : {'linear_solver'            : 'cg',
                              'preconditioner'           : 'hypre_amg',
                              'relative_tolerance'       : 1e-9,
                              'relaxation_parameter'     : 1.0,
                              'maximum_iterations'       : 3,
                              'error_on_nonconvergence'  : False}}
#nparams = {'newton_solver' : {'linear_solver'            : 'cg',
#                              'preconditioner'           : 'hypre_amg',
#                              'relative_tolerance'       : 1e-9,
#                              'relaxation_parameter'     : 0.7,
#                              'maximum_iterations'       : 30,
#                              'error_on_nonconvergence'  : False}}
#nparams = {'newton_solver' : {'linear_solver'            : 'mumps',
#                              'relative_tolerance'       : 1e-9,
#                              'relaxation_parameter'     : 0.7,
#                              'maximum_iterations'       : 30,
#                              'error_on_nonconvergence'  : False}}
m_params  = {'solver'               : nparams,
             'solve_vert_velocity'  : True,
             'solve_pressure'       : False,
             'vert_solve_method'    : 'mumps'}

#mom = MomentumDukowiczStokes(d3model, m_params, isothermal=False)
#mom = MomentumDukowiczBrinkerhoffStokes(d3model, m_params, isothermal=False)
#mom = MomentumDukowiczStokesReduced(d3model, m_params, isothermal=False)
mom = MomentumDukowiczBP(d3model, m_params, linear=True, isothermal=False)
#mom = MomentumDukowiczBP(d3model, m_params, linear=False, isothermal=False)
#mom = MomentumBP(d3model, m_params, isothermal=False)
nrg = Enthalpy(d3model, transient=False, use_lat_bc=True, 
               epsdot_ftn=mom.strain_rate_tensor)

#===============================================================================
## derivative of objective function callback function : 
#d3model.set_out_dir(out_dir + 'u_inversion/')
#
#def deriv_cb(I, dI, beta):
#  # calculate the L_inf norm of misfit :
#  mom.calc_misfit(d3model.GAMMA_U_GND)
#  d3model.assign_submesh_variable(beta_b, beta)
#  d3model.save_xdmf(beta_b, 'beta_control')
#
## post-adjoint-iteration callback function :
#def adj_post_cb_ftn():
#  mom.solve_params['solve_vert_velocity'] = True
#  mom.solve(annotate=False)
#
#  # save the optimal velocity and beta fields for viewing with paraview :
#  d3model.assign_submesh_variable(Us,     d3model.u)
#  d3model.assign_submesh_variable(beta_b, d3model.beta)
#  d3model.save_xdmf(Us,     'U_opt')
#  d3model.save_xdmf(beta_b, 'beta_opt')
#
## after every completed adjoining, save the state of these functions :
#adj_save_vars = [d3model.beta, d3model.u]
#
## form the cost functional :
#mom.form_obj_ftn(integral=d3model.dSrf_gu, kind='log_L2_hybrid', 
#                 g1=0.01, g2=5000)
#
## form the regularization functional :
#mom.form_reg_ftn(d3model.beta, integral=d3model.dBed_g, kind='TV', 
#                 alpha=1.0)
#
### post-thermo-solve callback function :
##def tmc_cb_ftn():
##  nrg.solve_basal_melt_rate()
##  d3model.assign_submesh_variable(Tb,   d3model.T)
##  d3model.assign_submesh_variable(Us,   d3model.u)
##  d3model.assign_submesh_variable(Wb,   d3model.W)
##  d3model.assign_submesh_variable(Mb,   d3model.Mb)
##  d3model.save_xdmf(Tb,   'Tb')
##  d3model.save_xdmf(Us,   'Us')
##  d3model.save_xdmf(Wb,   'Wb')
##  d3model.save_xdmf(Mb,   'Mb')
##  d3model.save_xdmf(d3model.T, 'T')
##  d3model.save_xdmf(d3model.W, 'W')
##
##d3model.thermo_solve(mom, nrg, callback=tmc_cb_ftn)
#mom.linearize_viscosity()
#
## optimize for beta :
#mom.optimize_u_ob(control           = d3model.beta,
#                  bounds            = (1e-5, 1e7),
#                  method            = 'ipopt',
#                  adj_iter          = 20,
#                  adj_save_vars     = adj_save_vars,
#                  adj_callback      = deriv_cb,
#                  post_adj_callback = adj_post_cb_ftn)
#
#sys.exit(0)

#===============================================================================
#d3model.thermo_solve(mom, nrg, callback=None, max_iter=1)
#fU   = HDF5File(mpi_comm_world(), out_dir + 'U3.h5', 'w')
#d3model.save_hdf5(d3model.u, fU)
#fU.close()
#sys.exit(0)
#nrg.solve_divide(annotate=False)
#d3model.save_xdmf(d3model.theta_app, 'theta_app')

#===============================================================================
d3model.set_out_dir(out_dir + 'W_L_curve_TV_reg_L2_obj/')

# number of digits for saving variables :
iterations = 500
gamma      = 2.5e7
n_i        = len(str(iterations))

# derivative of objective function callback function : 
def deriv_cb(I, dI, alpha):
  d3model.assign_submesh_variable(a_b, alpha)
  d3model.save_xdmf(a_b, 'alpha_control')
      
# objective gradient callback function :
def post_cb():
  nrg.partition_energy()
  d3model.save_xdmf(d3model.alpha, 'alpha_opt')
  d3model.save_xdmf(d3model.theta, 'theta_opt')
  d3model.save_xdmf(d3model.T,     'T_opt')
  d3model.save_xdmf(d3model.W,     'W_opt')

adj_kwargs = {'iterations'   : iterations,
              'gamma'        : gamma,
              'reg_kind'     : 'TV',
              'method'       : 'ipopt',
              'adj_callback' : deriv_cb}

#alphas = [1e5, 2.5e5, 5e5, 7.5e5, 1e6, 2.5e6]  # TV obj
alphas = [1e5, 1e6, 1e7, 2.5e7, 5e7, 7.5e7]

Lc_kwargs = {'alphas'        : alphas,
             'physics'       : nrg,
             'control'       : d3model.alpha,
             'int_domain'    : d3model.dBed_g,
             'adj_ftn'       : nrg.optimize_water_flux,
             'adj_kwargs'    : adj_kwargs,
             'reg_kind'      : 'TV',
             'pre_callback'  : None,
             'post_callback' : post_cb}

nrg.form_obj_ftn(kind='L2')
 
d3model.L_curve(**Lc_kwargs)

#nrg.optimize_water_flux(**adj_kwargs)

sys.exit(0)

#===============================================================================
#d3model.set_out_dir(out_dir + 'u_L_curve/')
#
## derivative of objective function callback function : 
#def deriv_cb(I, dI, beta):
#  # calculate the L_inf norm of misfit :
#  mom.calc_misfit(d3model.GAMMA_U_GND)
#  d3model.assign_submesh_variable(beta_b, beta)
#  d3model.save_xdmf(beta_b, 'beta_control')
#
## post-adjoint-iteration callback function :
#def post_cb():
#  # re-solve the momentum equations with vertical velocity and optimal beta :
#  m_params['solve_vert_velocity'] = True
#  mom.solve(annotate=False)
#
#  # save the optimal velocity and beta fields for viewing with paraview :
#  d3model.save_xdmf(d3model.u,   'U_opt')
#  d3model.save_xdmf(d3model.beta, 'beta_opt')
#
## form the cost functional :
#mom.form_obj_ftn(integral=d3model.dSrf_gu, kind='log_L2_hybrid', 
#                 g1=0.01, g2=5000)
#
## number of digits for saving variables :
#iterations = 2
#gamma      = 1e10
#n_i        = len(str(iterations))
#
## after every completed adjoining, save the state of these functions :
#adj_save_vars = [d3model.beta, d3model.u]
#
#uop_kwargs = {'control'           : d3model.beta,
#              'bounds'            : (1e-5, 1e7),
#              'method'            : 'ipopt',
#              'adj_iter'          : 10,
#              'adj_save_vars'     : adj_save_vars,
#              'adj_callback'      : deriv_cb,
#              'post_adj_callback' : post_cb}
#      
#alphas = [0.5, 1.0, 1.5]
#
#Lc_kwargs = {'alphas'        : alphas,
#             'physics'       : mom,
#             'control'       : d3model.beta,
#             'int_domain'    : d3model.dBed_g,
#             'adj_ftn'       : mom.optimize_u_ob,
#             'adj_kwargs'    : uop_kwargs,
#             'reg_kind'      : 'TV',
#             'pre_callback'  : None,
#             'post_callback' : None}
#
#d3model.L_curve(**Lc_kwargs)
#
#sys.exit(0)

#===============================================================================
d3model.set_out_dir(out_dir + 'tmc_inversion/')

# thermo-solve callback function :
def tmc_cb_ftn():
  nrg.solve_basal_melt_rate()
  d3model.assign_submesh_variable(Tb,     d3model.T)
  d3model.assign_submesh_variable(Wb,     d3model.W)
  d3model.assign_submesh_variable(Mb,     d3model.Mb)
  d3model.assign_submesh_variable(alphab, d3model.alpha)
  d3model.save_xdmf(Tb,     'Tb')
  d3model.save_xdmf(Wb,     'Wb')
  d3model.save_xdmf(Mb,     'Mb')
  d3model.save_xdmf(alphab, 'alphab')

# derivative of objective functional callback function : 
def deriv_cb(I, dI, beta):
  d3model.assign_submesh_variable(beta_b, beta)
  d3model.save_xdmf(beta_b, 'beta_control')

# post-adjoint-iteration callback function :
def adj_post_cb_ftn():
  # re-solve the momentum equations with vertical velocity and optimal beta :
  m_params['solve_vert_velocity'] = True
  mom.solve(annotate=False)

  # save the optimal velocity and beta fields for viewing with paraview :
  d3model.assign_submesh_variable(Us,     d3model.u)
  d3model.assign_submesh_variable(beta_b, d3model.beta)
  d3model.save_xdmf(Us,    'U_opt')
  d3model.save_xdmf(betab, 'beta_opt')

# after every completed adjoining, save the state of these functions :
adj_save_vars = [d3model.beta,
                 d3model.u,
                 d3model.T,
                 d3model.W,
                 d3model.theta,
                 d3model.alpha,
                 d3model.Mb]

# the initial step saves everything :
ini_save_vars = adj_save_vars + [d3model.Ubar, d3model.U_ob]

# form the objective functional for water-flux optimization :
nrg.form_obj_ftn(kind='L2')

# form the regularization functional :
nrg.form_reg_ftn(d3model.alpha, integral=d3model.dBed_g, kind='TV', alpha=2.5e7)

# form the velocity cost functional :
mom.form_obj_ftn(integral=d3model.dSrf_gu, kind='log_L2_hybrid', 
                 g1=0.01, g2=5000)

# form the regularization functional :
mom.form_reg_ftn(d3model.beta, integral=d3model.dBed_g, kind='TV', alpha=1.0)

tmc_kwargs = {'momentum'          : mom,
              'energy'            : nrg,
              'callback'          : tmc_cb_ftn, 
              'atol'              : 1e2,
              'rtol'              : 1e0,
              'max_iter'          : 50}

uop_kwargs = {'control'           : d3model.beta,
              'bounds'            : (1e-5, 1e7),
              'method'            : 'ipopt',
              'adj_iter'          : 10,
              'adj_save_vars'     : None,
              'adj_callback'      : deriv_cb,
              'post_adj_callback' : adj_post_cb_ftn}

ass_kwargs = {'iterations'        : 10,
              'tmc_kwargs'        : tmc_kwargs,
              'uop_kwargs'        : uop_kwargs,
              'incomplete'        : True,
              'ini_save_vars'     : ini_save_vars,
              'post_save_vars'    : adj_save_vars,
              'post_ini_callback' : None}

# assimilate ! :
d3model.assimilate_U_ob(**ass_kwargs) 


 
