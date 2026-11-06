import numpy
import inspect
mod = numpy.lib._function_base_impl
f = mod._compute_virtual_index
import ast
tree = ast.parse(inspect.getsource(f))
for node in tree.body:
    if isinstance(node, ast.Return):
        print(ast.unparse(node.value))
