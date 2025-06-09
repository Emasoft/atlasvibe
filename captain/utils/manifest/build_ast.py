# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import ast
from typing import Any, Callable, Literal, Optional, Tuple, cast

SELECTED_IMPORTS = ["atlasvibe", "typing", "pkgs.atlasvibe.atlasvibe"] # Assuming 'atlasvibe' is still the package name for DataContainer etc.
NO_OUTPUT_NODES = ["GOTO", "END"]


class AtlasvibeNodeTransformer(ast.NodeTransformer): # Consider renaming this class to AtlasVibeNodeTransformer if it becomes confusing
    def get_atlasvibe_decorator(self, node: ast.FunctionDef): # Name implies old decorator
        return [
            decorator
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Name)
            and (decorator.id == "atlasvibe_node" or decorator.id == "atlasvibe")
            or isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and (decorator.func.id == "atlasvibe_node" or decorator.func.id == "atlasvibe")
        ]

    def get_display_decorator(self, node: ast.FunctionDef):
        return [
            decorator
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Name)
            and decorator.id == "display"
            or isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == "display"
        ]

    def get_decorator(
        self, node: ast.FunctionDef, decorator_name: Literal["display", "atlasvibe_node", "atlasvibe"]
    ):
        return [
            decorator
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Name)
            and decorator.id == decorator_name
            or isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == decorator_name
        ]

    def visit_Module(self, node: ast.Module):
        node.body = [self.visit(n) for n in node.body]
        return node

    def visit_Import(self, node: ast.Import):
        if node.names[0].name in SELECTED_IMPORTS:
            return node
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module in SELECTED_IMPORTS:
            return node
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # The case where the node is used for overloading, will ignore all other decorators
        if has_decorator(node, "display"):
            node.decorator_list = cast(
                list[ast.expr], self.get_decorator(node, "display")
            )
        elif not has_decorator(node, "atlasvibe_node") and not has_decorator(node, "atlasvibe") and not has_decorator(
            node, "node_initialization"
        ):
            return None

        # TODO: make an error comment when a display decorator have another decorator
        # Keep only the '@atlasvibe_node' if there are multiple decorators.

        if (has_decorator(node, "atlasvibe_node") or has_decorator(node, "atlasvibe")) and len(node.decorator_list) > 1:
            # Keep only the '@atlasvibe_node' or '@atlasvibe' decorator if there are multiple decorators.
            # Some decorators, like '@run_in_venv', create virtual environments, which we
            # don't want to generate when creating the manifest.
            if has_decorator(node, "atlasvibe_node"):
                node.decorator_list = cast(
                    list[ast.expr], self.get_decorator(node, "atlasvibe_node")
                )
            else:
                node.decorator_list = cast(
                    list[ast.expr], self.get_decorator(node, "atlasvibe")
                )

        if node.body:
            new_body = (
                [node.body[0]]
                if isinstance(node.body[0], ast.Expr)
                else [
                    ast.Pass(
                        lineno=node.body[0].lineno, col_offset=node.body[0].col_offset
                    )
                ]
            )
        else:
            new_body = [ast.Pass(lineno=node.lineno, col_offset=node.col_offset)]

        node.body = cast(list[ast.stmt], new_body)

        return node

    def generic_visit(self, node: ast.Module):
        return None


def make_manifest_ast(
    path: str,
) -> Tuple[str, Optional[str], ast.Module, Optional[Any]]:
    with open(path) as f:
        tree = ast.parse(f.read())

    # Do an initial pass to remove everything that isn't an
    # import, dataclass or atlasvibe_node node
    transformer = AtlasvibeNodeTransformer() # Name of class can remain for now, or be changed too
    tree: ast.Module = transformer.visit(tree)

    overload: dict[Any] | None = dict()
    # This generates a dict with parameter: {display value: parameters to be displayed}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and has_decorator(node, "display"):
            param, value, display = extract_overload_arguments(node)
            overload.setdefault(param, {}).update({value: display})
    if not overload:
        overload = None

    atlasvibe_node = find(
        tree.body,
        lambda node: isinstance(node, ast.FunctionDef)
        and (has_decorator(node, "atlasvibe_node") or has_decorator(node, "atlasvibe")),
    )

    init_func = find(
        tree.body,
        lambda node: isinstance(node, ast.FunctionDef)
        and has_decorator(node, "node_initialization"),
    )

    if not atlasvibe_node:
        raise ValueError("No @atlasvibe_node or @atlasvibe decorated function found in file")

    node_name = atlasvibe_node.name
    init_func_name = init_func.name if init_func else None
    return_type = None

    if not atlasvibe_node.returns and node_name not in NO_OUTPUT_NODES:
        print(f"[Warning]: {node_name} has no return type hint, will have no output!")
    elif (
        isinstance(atlasvibe_node.returns, ast.Constant)
        and atlasvibe_node.returns.value is None
    ):
        pass
    else:
        # This handles the case where the return type is a union, we can ignore
        # all of the class defs in this case
        if (
            atlasvibe_node.returns
            and not isinstance(atlasvibe_node.returns, ast.BinOp)
            and not isinstance(atlasvibe_node.returns, ast.Subscript)
        ):
            return_type = atlasvibe_node.returns.id

    # Then get rid of all the other classes
    # that aren't the return type of the atlasvibe_node node
    # This also filters out all of the None values

    tree.body = [
        node
        for node in tree.body
        if node and (not isinstance(node, ast.ClassDef) or node.name == return_type)
    ]

    return (node_name, init_func_name, tree, overload)


def get_atlasvibe_decorator(tree: ast.Module) -> Optional[ast.Call]: # Name implies old decorator
    atlasvibe_node = find(
        tree.body,
        lambda node: isinstance(node, ast.FunctionDef)
        and (has_decorator(node, "atlasvibe_node") or has_decorator(node, "atlasvibe")),
    )
    if not atlasvibe_node:
        raise ValueError("No @atlasvibe_node or @atlasvibe decorated function found in file")

    # Differentiates between @atlasvibe_node/@atlasvibe and @atlasvibe_node(deps={...})/@atlasvibe(deps={...})
    return find(
        atlasvibe_node.decorator_list,
        lambda d: isinstance(d, ast.Call)
        and isinstance(d.func, ast.Name)
        and (d.func.id == "atlasvibe_node" or d.func.id == "atlasvibe"),
    )


def get_atlasvibe_decorator_param(tree: ast.Module, name: str) -> Optional[ast.keyword]: # Name implies old decorator
    decorator = get_atlasvibe_decorator(tree)

    if not decorator:
        return None
    return find(decorator.keywords, lambda k: k.arg == name)


def get_node_type(tree: ast.Module) -> Optional[str]:
    kw = get_atlasvibe_decorator_param(tree, "node_type")
    if not kw:
        return None
    if not isinstance(kw.value, ast.Constant):
        raise ValueError("Node type must be a string")
    return kw.value.value


def get_pip_dependencies(tree: ast.Module) -> Optional[list[dict[str, str]]]:
    kw = get_atlasvibe_decorator_param(tree, "deps")

    if not kw:
        return None

    if not isinstance(kw.value, ast.Dict):
        raise ValueError("Pip dependencies must be a dictionary")

    deps: list[Any] = []
    for package, ver in zip(kw.value.keys, kw.value.values):
        if not isinstance(package, ast.Constant) or not isinstance(ver, ast.Constant):
            raise ValueError("Pip dependencies must be a dictionary of strings")
        deps.append({"name": package.value, "v": ver.value})

    return deps


def has_decorator(node: ast.FunctionDef | ast.ClassDef, decorator_name: str) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == decorator_name:
            return True
        elif (
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == decorator_name
        ):
            return True

    return False


def find(collection: list[Any], predicate: Callable[[Any], bool]) -> Optional[Any]:
    return next(filter(predicate, collection), None)


# overload_param contains all the parameters in the OVERLOAD function
# default_value is the trigger value for the parameters
def extract_overload_arguments(node: ast.FunctionDef) -> Tuple:
    overload_param = [arg.arg for arg in node.args.args]
    default_value = ast.literal_eval(node.args.defaults[0])
    return overload_param[-1], default_value, overload_param[:-1]
