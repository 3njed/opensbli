#!/usr/bin/env python

# Import all the functions from opensbli
from opensbli import *
import copy

# Problem dimension
ndim = 2

# Define the compresible Navier-Stokes equations in Einstein notation, by default the scheme is Central no need to
# Specify the schemes
mass = "Eq(Der(rho,t), - Skew(rho*u_j,x_j))"
momentum = "Eq(Der(rhou_i,t) , - Skew(rhou_i*u_j, x_j) - Der(p,x_i)  + Der(tau_i_j,x_j))"
energy = "Eq(Der(rhoE,t), - Skew(rhoE*u_j,x_j) - Conservative(p*u_j,x_j) + Der(q_j,x_j) + Der(u_i*tau_i_j ,x_j))"

# Substitutions used in the equations
stress_tensor = "Eq(tau_i_j, (1.0/Re)*(Der(u_i,x_j)+ Der(u_j,x_i)- (2/3)* KD(_i,_j)* Der(u_k,x_k)))"
heat_flux = "Eq(q_j, (1.0/((gama-1)*Minf*Minf*Pr*Re))*Der(T,x_j))"

substitutions = [stress_tensor, heat_flux]

# Constants that are used
constants = ["Re", "Pr", "gama", "Minf", "mu"]

# symbol for the coordinate system in the equations 
coordinate_symbol = "x"

# Constituent relations used in the system
velocity = "Eq(u_i, rhou_i/rho)"
pressure = "Eq(p, (gama-1)*(rhoE - rho*(1/2)*(KD(_i,_j)*u_i*u_j)))"
temperature = "Eq(T, p*gama*Minf*Minf/(rho))"

# Instantiate EinsteinEquation class for expanding the Einstein indices in the equations
einstein_eq = EinsteinEquation()

# Expand the simulation equations, for this create a simulation equations class
simulation_eq = SimulationEquations()

# Expand mass and add the expanded equations to the simulation equations
eqns = einstein_eq.expand(mass, ndim, coordinate_symbol, substitutions, constants)
simulation_eq.add_equations(eqns)

# Expand momentum add the expanded equations to the simulation equations
eqns = einstein_eq.expand(momentum, ndim, coordinate_symbol, substitutions, constants)
simulation_eq.add_equations(eqns)

# Expand energy equation add the expanded equations to the simulation equations
eqns = einstein_eq.expand(energy, ndim, coordinate_symbol, substitutions, constants)
simulation_eq.add_equations(eqns)

# Expand the constituent relations and them to the constituent relations class
constituent = ConstituentRelations() # Instantiate constituent relations object

# Expand momentum add the expanded equations to the constituent relations
eqns = einstein_eq.expand(velocity, ndim, coordinate_symbol, substitutions, constants)
constituent.add_equations(eqns)

# Expand pressure add the expanded equations to the constituent relations
eqns = einstein_eq.expand(pressure, ndim, coordinate_symbol, substitutions, constants)
constituent.add_equations(eqns)

# Expand temperature add the expanded equations to the constituent relations
eqns = einstein_eq.expand(temperature, ndim, coordinate_symbol, substitutions, constants)
constituent.add_equations(eqns)

# Write the expanded equations to a Latex file with a given name and titile
latex = LatexWriter()
latex.open('equations.tex', "Einstein Expansion of the simulation equations")
latex.write_string("Simulation equations\n")
for index, eq in enumerate(flatten(simulation_eq.equations)):
    latex.write_expression(eq)

latex.write_string("Constituent relations\n")
for index, eq in enumerate(flatten(constituent.equations)):
    latex.write_expression(eq)

latex.close()

# Create a simulation block
block = SimulationBlock(ndim, block_number=0)

# Local dictionary for parsing the expressions
local_dict = {"block": block, "GridVariable": GridVariable, "DataObject": DataObject}

# Initial conditions as strings
x0 = "Eq(DataObject(x0), block.deltas[0]*block.grid_indexes[0])"
x1 = "Eq(DataObject(x1), block.deltas[1]*block.grid_indexes[1])"

# Laminar initial condition
# xl = 2.0*pi
# yl = 2.0
x0l = "Eq(GridVariable(x0l), 2.0*pi)"
x1l = "Eq(GridVariable(x1l), 2.0)"

# u0 = "Eq(GridVariable(u0), 45*(1-(DataObject(x1)-1.0)**2))"
u0 = "Eq(GridVariable(u0), 0)"
u1 = "Eq(GridVariable(u1), 0)"
p = "Eq(GridVariable(p), 1.0/(gama*Minf*Minf))"
r = "Eq(GridVariable(r), 1.0/(1.0+0.01944*(1-(DataObject(x1)-1)**4)))"

rho = "Eq(DataObject(rho), r)"
rhou0 = "Eq(DataObject(rhou0), r*u0)"
rhou1 = "Eq(DataObject(rhou1), r*u1)"
rhoE = "Eq(DataObject(rhoE), p/(gama-1) + 0.5* r*(u0**2 + u1**2))"
eqns = [x0, x1, u0, u1, p, r, rho, rhou0, rhou1, rhoE]

# parse the initial conditions
initial_equations = [parse_expr(eq, local_dict=local_dict) for eq in eqns]
pprint(initial_equations)
initial = GridBasedInitialisation()
initial.add_equations(initial_equations)

# Create a schemes dictionary to be used for discretisation
schemes = {}
# Central scheme for spatial discretisation and add to the schemes dictionary
cent = Central(4)
schemes[cent.name] = cent
# RungeKutta scheme for temporal discretisation and add to the schemes dictionary
rk = RungeKutta(3)
schemes[rk.name] = rk

boundaries = []
# Periodic boundaries in x0 direction
direction = 0
boundaries += [PeriodicBoundaryConditionBlock(direction, 0)]
boundaries += [PeriodicBoundaryConditionBlock(direction, 1)]

# Isothermal wall in x1 direction
direction = 1
rhoEd = "Eq(DataObject(rhoE), DataObject(rho)/((gama-1)*gama*Minf*Minf))"
rhoEd = parse_expr(rhoEd, local_dict=local_dict)
upper_wall_eq = [rhoEd]
lower_wall_eq = [rhoEd]
boundaries += [IsothermalWallBoundaryConditionBlock(direction, 0, upper_wall_eq, local_dict)]
boundaries += [IsothermalWallBoundaryConditionBlock(direction, 1, lower_wall_eq, local_dict)]

# set the boundaries for the block
block.set_block_boundaries(boundaries)
# set the equations to be solved on the block
block.set_equations([copy.deepcopy(constituent), copy.deepcopy(simulation_eq), initial])
# set the discretisation schemes 
block.set_discretisation_schemes(schemes)

# Discretise the equations on the block
block.discretise()

# create an algorithm from the discretised computations
alg = TraditionalAlgorithmRK(block)

# set the simulation data type, for more information on the datatypes see opensbli.core.datatypes
SimulationDataType.set_datatype(Double)

# Write the code for the algorithm
OPSC(alg)

