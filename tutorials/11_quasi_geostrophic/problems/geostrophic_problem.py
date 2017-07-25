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

from rbnics.problems.base import LinearProblem, ParametrizedDifferentialProblem
from rbnics.backends import product, sum
from rbnics.utils.decorators import Extends, override

GeostrophicProblem_Base = LinearProblem(ParametrizedDifferentialProblem)

@Extends(GeostrophicProblem_Base)
class GeostrophicProblem(GeostrophicProblem_Base):
    ## Default initialization of members
    @override
    def __init__(self, V, **kwargs):
        # Call to parent
        GeostrophicProblem_Base.__init__(self, V, **kwargs)
        
        # Form names for geostrophic problems
        self.terms = ["a", "f"]
        self.terms_order = {"a": 2, "f": 1}
        self.components = ["psi", "q"]
        
    ## Perform a truth solve
    class ProblemSolver(GeostrophicProblem_Base.ProblemSolver):
        def matrix_eval(self):
            problem = self.problem
            return sum(product(problem.compute_theta("a"), problem.operator["a"]))
            
        def vector_eval(self):
            problem = self.problem
            return sum(product(problem.compute_theta("f"), problem.operator["f"]))
            
