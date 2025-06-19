from functools import reduce
from typing import Callable
from pkgs.atlasvibe.atlasvibe.data_container import (
    OrderedPair,
    Scalar,
    Vector,
    DCNpArrayType,
)


def get_val(
    data_container: OrderedPair | Scalar | Vector,
) -> DCNpArrayType:
    match data_container:
        case OrderedPair():
            return data_container.y
        case Scalar():
            return data_container.c
        case Vector():
            return data_container.v


def perform_arithmetic_operation(
    a: OrderedPair | Scalar | Vector,
    b: list[OrderedPair | Scalar | Vector],
    operation: Callable[[DCNpArrayType, DCNpArrayType], DCNpArrayType],
) -> OrderedPair | Scalar | Vector:
    """Perform a generic arithmetic operation on data containers.

    Parameters
    ----------
    a : OrderedPair | Scalar | Vector
        The first operand
    b : list[OrderedPair | Scalar | Vector]
        The list of additional operands
    operation : Callable
        The numpy operation to apply (e.g., np.add, np.subtract)

    Returns
    -------
    OrderedPair | Scalar | Vector
        The result in the same container type as 'a'
    """
    initial = get_val(a)
    seq = map(lambda dc: get_val(dc), b)
    y = reduce(lambda u, v: operation(u, v), seq, initial)

    match a:
        case OrderedPair():
            return OrderedPair(x=a.x, y=y)
        case Vector():
            return Vector(v=y)
        case Scalar():
            return Scalar(c=y)
