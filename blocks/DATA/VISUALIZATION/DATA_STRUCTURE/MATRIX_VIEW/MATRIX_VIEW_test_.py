def test_MATRIX_VIEW(mock_atlasvibe_node_decorator, mock_atlasvibe_decorator):
    """Verify MATRIX_VIEW can visualize a 3x4 matrix without errors."""
    import MATRIX_VIEW
    from blocks.DATA.GENERATION.SIMULATIONS.MATRIX.MATRIX import MATRIX

    try:
        # generate a MATRIX that has different number of rows and columns
        m1 = MATRIX(row=3, column=4)

        # run MATRIX_VIEW function
        MATRIX_VIEW.MATRIX_VIEW(default=m1)
    except Exception:
        raise AssertionError("Unable visualize the matrix")
