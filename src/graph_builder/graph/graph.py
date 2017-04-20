from typing import Dict, Set, List, Iterable, Type

import numpy as np

from graph_builder.graph.attribute import Attribute


class Node:
    attributes: Set[Type[Attribute]] = set()
    parameters: Dict[str, any]

    def __init__(self, parameters: Dict[str, any] = None):
        self.parameters = parameters if parameters is not None else {}
        self.attributes = set(self.attributes)  # copy construction

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def __str__(self):
        return self.__repr__()


class Operator(Node):
    name: str
    attributes: Set[Type[Attribute]] = []
    inputs: Dict[str, "Variable"]
    outputs: Dict[str, "Variable"]

    def __init__(self,
                 name: str,
                 parameters: Dict[str, object] = None):

        super().__init__(parameters)

        self.name = name
        self.parameters = parameters
        self.inputs = {}
        self.outputs = {}

    def get_input_name(self, var: "Variable"):
        for name, v in self.inputs.items():
            if v is not var:
                continue

            return name

        else:
            raise KeyError(f"'{name}' is not input of {self}")

    def get_output_name(self, var: "Variable"):
        for name, v in self.outputs.items():
            if v is not var:
                continue

            return name

        else:
            raise KeyError(f"'{name}' is not output of {self}")

    def append_input(self, name: str, var: "Variable"):
        self.inputs[name] = var
        var.input_to.add(self)

    def remove_input(self, var: "Variable"):
        name = self.get_input_name(var)
        self.inputs.pop(name)
        var.input_to.remove(self)

    def replace_input(self, v_old: "Variable", v_new: "Variable"):
        name = self.get_input_name(v_old)
        self.remove_input(v_old)
        self.append_input(name, v_new)

    def append_output(self, name: str, var: "Variable"):
        if var.output_from is not None:
            raise KeyError(f"{var} has been registered as f{var.output_from}'s output already.")

        self.outputs[name] = var
        var.output_from = self

    def remove_output(self, var: "Variable"):
        name = self.get_output_name(var)
        var = self.outputs.pop(name)
        var.output_from = None

    def replace_output(self, v_old: "Variable", v_new: "Variable"):
        name = self.get_output_name(v_old)
        self.remove_output(v_old)
        self.append_output(name, v_new)

    def __repr__(self):
        return f"""<{self.__class__.__name__} inputs={self.inputs}, outputs={self.outputs}>"""

    def __str__(self):
        return self.__repr__()

    def __call__(self, *args: Iterable["Variable"]) -> Iterable["Variable"]:
        raise NotImplementedError


class Variable(Node):
    """
    レイヤー間で受け渡される変数
    名前で識別される
    現在のところ、float32型(4byte/element)を想定している
    shapeはタプルで、その順序はAttribute(OrderNC etc)に依存
    """

    shape: List[int]
    input_to: Set[Operator]
    output_from: Operator = None
    axis_order: Type[Attribute]  # FIXME: Attribute -> AxisOrder

    def __init__(self, shape: List[int], axis_order: Type[Attribute]):
        from graph_builder.graph.variables import attributes as VA  # FIXME import order
        assert issubclass(axis_order, VA.AxisOrder)
        super().__init__()
        self.shape = list(shape)
        self.input_to = set()
        self.attributes.add(axis_order)
        self.axis_order = axis_order
        assert axis_order.ndim == len(self.shape)

    @property
    def name(self):
        return self.parameters["name"] if "name" in self.parameters else ""

    @name.setter
    def name(self, name: str):
        self.parameters["name"] = name

    @property
    def size(self):
        # noinspection PyTypeChecker
        return int(np.prod(self.shape))

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def shape_dict(self):
        return self.axis_order.get_shape_dict(self)

    def change_axis_order(self, axis_order: Type[Attribute]):
        from graph_builder.graph.variables import attributes as VA  # FIXME import order
        assert issubclass(axis_order, VA.AxisOrder)
        # 次元数を減らす時は、なくなる次元のサイズが1のときだけOK
        # 増える次元は、サイズ1
        current_shape_dict = self.shape_dict
        new_shape = [current_shape_dict.get(axis, 1) for axis in axis_order.axes]
        for axis, size in current_shape_dict.items():
            if axis not in axis_order.axes:
                assert size == 1
        self.axis_order = axis_order
        self.shape = new_shape

    def __repr__(self):
        order_repr = ''.join(map(lambda e: e.name, self.axis_order.axes))
        return f"<Variable shape={self.shape}, order=\"{order_repr}\">"

    def __str__(self):
        return self.__repr__()
