from varglas import *
from fenics  import *

out_dir  = 'dump/vars_low/'
thklim   = 1.0
measures = DataFactory.get_ant_measures(res=900)
bedmap1  = DataFactory.get_bedmap1(thklim=thklim)
bedmap2  = DataFactory.get_bedmap2(thklim=thklim)

mesh = Mesh('dump/meshes/ant_mesh_low_new.xml.gz')

dm = DataInput(measures, mesh=mesh)
d1 = DataInput(bedmap1,  mesh=mesh)
d2 = DataInput(bedmap2,  mesh=mesh)

S     = d2.get_expression("S",      near=True)
B     = d2.get_expression("B",      near=True)
M     = d2.get_expression("mask",   near=True)
S_ring  = d1.get_expression("acca",   near=False)
T_s   = d1.get_expression("temp",   near=False)
q_geo = d1.get_expression("ghfsr",  near=False)
u_ob  = dm.get_expression("vx",     near=False)
v_ob  = dm.get_expression("vy",     near=False)
U_msk = dm.get_expression("mask",   near=True)

model = D3Model(mesh=mesh, out_dir=out_dir, save_state=True)
model.deform_mesh_to_geometry(S, B)
model.calculate_boundaries(mask=M, S_ring=S_ring, U_mask=U_msk, mark_divide=False)

model.init_T_surface(T_s)
model.init_q_geo(q_geo)
model.init_U_ob(u_ob, v_ob)

model.save_xdmf(model.ff, 'ff')
model.state.close()



