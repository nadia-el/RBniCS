# Copyright (C) 2015-2017 by the RBniCS authors
#
# This file is part of RBniCS.
#
# RBniCS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RBniCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with RBniCS. If not, see <http://www.gnu.org/licenses/>.
#

from dolfin import *
set_log_level(PROGRESS)
from rbnics import *
from problems import *
from reduction_methods import *

class NavierStokes(NavierStokesProblem):
    
    ## Default initialization of members
    def __init__(self, V, **kwargs):
        # Call the standard initialization
        NavierStokesProblem.__init__(self, V, **kwargs)
        # ... and also store FEniCS data structures for assembly
        assert "subdomains" in kwargs
        assert "boundaries" in kwargs
        self.subdomains, self.boundaries = kwargs["subdomains"], kwargs["boundaries"]
        dup = TrialFunction(V)
        (self.du, self.dp) = split(dup)
        (self.u, self.p) = split(self._solution)
        vq = TestFunction(V)
        (self.v, self.q) = split(vq)
        self.s = TrialFunction(V.sub(0).collapse())
        self.r = TestFunction(V.sub(0).collapse())
        self.dx = Measure("dx")(subdomain_data=self.subdomains)
        self.ds = Measure("ds")(subdomain_data=self.boundaries)
        #
        self.inlet = Expression(("1./2.25*(x[1] - 2)*(5 - x[1])", "0."), degree=2)
        self.f = Constant((0.0, 0.0))
        self.g = Constant(0.0)
        # Customize nonlinear solver parameters
        self._nonlinear_solver_parameters = {
            "linear_solver": "mumps",
            "maximum_iterations": 20,
            "report": True,
            "line_search": "bt",
            "error_on_nonconvergence": False
        }
        
    ## Return theta multiplicative terms of the affine expansion of the problem.
    def compute_theta(self, term):
        mu = self.mu
        mu1 = mu[0]
        if term == "a":
            theta_a0 = 1.
            return (theta_a0,)
        elif term in ("b", "bt", "bt_restricted"):
            theta_b0 = 1.
            return (theta_b0,)
        elif term in ("c", "dc"):
            theta_c0 = 1.
            return (theta_c0,)
        elif term == "f":
            theta_f0 = 1.
            return (theta_f0,)
        elif term == "g":
            theta_g0 = 1.
            return (theta_g0,)
        elif term == "dirichlet_bc_u":
            theta_bc00 = mu1
            return (theta_bc00,)
        else:
            raise ValueError("Invalid term for compute_theta().")
                
    ## Return forms resulting from the discretization of the affine expansion of the problem operators.
    def assemble_operator(self, term):
        dx = self.dx
        if term == "a":
            u = self.du
            v = self.v
            a0 = 0
            for s in range(2):
                a0 += inner(grad(u) + transpose(grad(u)), grad(v))*dx(s + 1) #####transpose(grad(u)) ci serve?
            if term == "a":
                return (a0,)
        elif term == "b":
            u = self.du
            q = self.q
            b0 = 0
            for s in range(2):
                b0 += - q*div(u)*dx(s + 1)
            return (b0,)
        elif term in ("bt", "bt_restricted"):
            p = self.dp
            if term == "bt":
                v = self.v
            elif term == "bt_restricted":
                v = self.r
            bt0 = 0
            for s in range(2):
                bt0 += - p*div(v)*dx(s + 1)
            return (bt0,)
        elif term in ("c", "dc"):
            u = self.u
            v = self.v
            c0 = 0
            for s in range(2):
                c0 += inner(grad(u)*u, v)*dx(s + 1)
            if term == "c":
                return (c0,)
            else:
                du = self.du
                return (derivative(c0, u, du),)
        elif term == "f":
            v = self.v
            f0 = 0
            for s in range(2):
                f0 += inner(self.f, v)*dx(s + 1)
            return (f0,)
        elif term == "g":
            q = self.q
            g0 = 0
            for s in range(2):
                g0 += self.g*q*dx(s + 1)
            return (g0,)
        elif term == "dirichlet_bc_u":
            bc0 = [DirichletBC(self.V.sub(0), self.inlet,           self.boundaries, 1),
                   DirichletBC(self.V.sub(0), Constant((0.0, 0.0)), self.boundaries, 2)]
            return (bc0,)
        elif term == "dirichlet_bc_s":
            bc0 = [DirichletBC(self.V.sub(0).collapse(), Constant((0.0, 0.0)), self.boundaries, 1),
                   DirichletBC(self.V.sub(0).collapse(), Constant((0.0, 0.0)), self.boundaries, 2)]
            return (bc0,)
        elif term == "inner_product_u" or term == "inner_product_s":
            if term == "inner_product_u":
                du = self.du
                v = self.v
            elif term == "inner_product_s":
                du = self.s
                v = self.r
            x0 = inner(grad(du),grad(v))*dx
            return (x0,)
        elif term == "inner_product_p":
            dp = self.dp
            q = self.q
            x0 = inner(dp, q)*dx
            return (x0,)
        else:
            raise ValueError("Invalid term for assemble_operator().")
        
# Customize the resulting reduced problem
@CustomizeReducedProblemFor(NavierStokesProblem)
def CustomizeReducedNavierStokes(ReducedNavierStokes_Base):
    class ReducedNavierStokes(ReducedNavierStokes_Base):
        def __init__(self, truth_problem, **kwargs):
            ReducedNavierStokes_Base.__init__(self, truth_problem, **kwargs)
            self._nonlinear_solver_parameters["report"] = True
            
    return ReducedNavierStokes

# 1. Read the mesh for this problem
mesh = Mesh("data/backward_facing_step.xml")
subdomains = MeshFunction("size_t", mesh, "data/backward_facing_step_physical_region.xml")
boundaries = MeshFunction("size_t", mesh, "data/backward_facing_step_facet_region.xml")

# 2. Create Finite Element space (Taylor-Hood P2-P1)
element_u = VectorElement("Lagrange", mesh.ufl_cell(), 2)
element_p = FiniteElement("Lagrange", mesh.ufl_cell(), 1)
element   = MixedElement(element_u, element_p)
V = FunctionSpace(mesh, element, components=[["u", "s"], "p"])

# 3. Allocate an object of the Elastic Block class
stokes_problem = NavierStokes(V, subdomains=subdomains, boundaries=boundaries)
mu_range = [(1.,100.)]
stokes_problem.set_mu_range(mu_range)

# 4. Prepare reduction with a POD-Galerkin method
pod_galerkin_method = PODGalerkin(stokes_problem)
pod_galerkin_method.set_Nmax(2)

# 5. Perform the offline phase
lifting_mu = [1.0]
stokes_problem.set_mu(lifting_mu)
pod_galerkin_method.initialize_training_set(3, sampling=EquispacedDistribution())
reduced_stokes_problem = pod_galerkin_method.offline()

# 6. Perform an online solve
online_mu = [80.0]
stokes_problem.set_mu(online_mu)
stokes_problem.solve()
stokes_problem.export_solution("NavierStokes", "offline_solution")
reduced_stokes_problem.set_mu(online_mu)
reduced_stokes_problem.solve()
print reduced_stokes_problem.compute_relative_error()
reduced_stokes_problem.export_solution("NavierStokes", "online_solution")

# 7. Perform an error analysis
pod_galerkin_method.initialize_testing_set(100)
pod_galerkin_method.error_analysis()

# 8. Perform a speedup analysis
pod_galerkin_method.speedup_analysis()