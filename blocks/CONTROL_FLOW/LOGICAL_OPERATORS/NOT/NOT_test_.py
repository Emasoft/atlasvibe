from atlasvibe import Boolean


def test_NOT(mock_atlasvibe_decorator):
    import NOT

    x = Boolean(b=True)
    y = Boolean(b=False)

    return1 = NOT.NOT(x)
    return2 = NOT.NOT(y)

    assert return1.b is False
    assert return2.b is True
