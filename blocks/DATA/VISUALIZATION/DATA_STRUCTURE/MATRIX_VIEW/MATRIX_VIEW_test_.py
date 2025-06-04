# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

def test_MATRIX_VIEW(mock_atlasvibe_node_decorator):
    import MATRIX_VIEW
    from blocks.DATA.GENERATION.SIMULATIONS.MATRIX.MATRIX import MATRIX

    try:
        # generate a MATRIX that has different number of rows and columns
        m1 = MATRIX(row=3, column=4)

        # run MATRIX_VIEW function
        MATRIX_VIEW.MATRIX_VIEW(default=m1)
    except Exception:
        raise AssertionError("Unable visualize the matrix")
