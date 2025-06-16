import numpy as np
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import OrderedPair, Scalar, Vector
from typing import Literal
from blocks.MATH.ARITHMETIC.utils.arithmetic_utils import get_val, perform_arithmetic_operation

@atlasvibe
def LOG(
    a: OrderedPair | Scalar | Vector,
    b: list[OrderedPair | Scalar | Vector],
    log_base: Literal["input", "e", "10", "2"] = "e",
) -> OrderedPair | Scalar | Vector:
    """Find the logarithm of input a with base b.

    Calculated element-wise for a Vector or OrderedPair input.

    Use log_base "input" to use the bottom input as the base.

    Parameters
    ----------
    a : OrderedPair|Scalar|Vector
        The input a use to compute the log of a.
    b : OrderedPair|Scalar|Vector
        The input b use to compute the log with base b.
    log_base : "input", "e", "10", "2"
        The base to use for the logarithm, by default "e".

    Returns
    -------
    OrderedPair|Scalar|Vector
        OrderedPair if a is an OrderedPair.
        x: the x-axis of input a.
        y: the result of the logarithm.

        Scalar if a is a Scalar.
        c: the result of the logarithm.

        Vector if a is a Vector.
        v: the result of the logarithm.
    """
    
    # For standard log bases, just compute log of input a
    if log_base != "input":
        value = get_val(a)
        match log_base:
            case "e":
                y = np.log(value)
            case "10":
                y = np.log10(value)
            case "2":
                y = np.log2(value)
        
        match a:
            case OrderedPair():
                return OrderedPair(x=a.x, y=y)
            case Vector():
                return Vector(v=y)
            case Scalar():
                return Scalar(c=y)
    else:
        # For input base, use the change of base formula: log_b(a) = log(a) / log(b)
        return perform_arithmetic_operation(a, b, lambda u, v: np.log(u) / np.log(v))
