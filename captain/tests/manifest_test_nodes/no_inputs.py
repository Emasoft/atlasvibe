from atlasvibe import DataContainer, atlasvibe


@atlasvibe
def NO_INPUTS(foo: list[int], bar: str) -> DataContainer:
    return DataContainer()
