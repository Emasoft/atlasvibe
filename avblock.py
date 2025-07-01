# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import os
import sys

import typer
from rich import print

from cli.cmd import add, sync
from cli.constants import BLOCKS_DOCS_FOLDER, BLOCKS_SOURCE_FOLDER, ERR_STRING
from cli.logging import err_console
from cli.state import state

app = typer.Typer()
app.command()(add.add)
app.command()(sync.sync)


@app.callback()
def main(verbose: bool = False):
    if verbose:
        print("Verbose mode is on!")
        state["verbose"] = True


if __name__ == "__main__":
    # this is to make sure we are running the cli in the right directory
    required_folders = [BLOCKS_DOCS_FOLDER, BLOCKS_SOURCE_FOLDER]
    if not all([os.path.isdir(folder) for folder in required_folders]):
        err_console.print(
            f"{ERR_STRING} avblock.py must be run at a directory where the following folders are present: {required_folders}"
        )
        sys.exit(1)

    app()
