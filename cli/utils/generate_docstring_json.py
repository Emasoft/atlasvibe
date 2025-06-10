import json
import os

from rich import print

from cli.constants import BLOCKS_SOURCE_FOLDER, ERR_STRING
from captain.utils.docstring_utils import parse_python_file, extract_docstring_from_node, create_docstring_json, parse_docstring


def generate_docstring_json() -> bool:
    """
    Will return True if all the docstrings are formatted correctly
    False if there is any docstring format error

    This will also save the JSON data in the docstring key of block_data.json
    """
    error = 0
    # Walk through all the folders and files in the current directory
    for root, _, files in os.walk(BLOCKS_SOURCE_FOLDER):
        # Iterate through the files
        for file in files:
            # Check if the file is a Python file and has the same name as the folder
            if not (file.endswith(".py") and file[:-3] == os.path.basename(root)):
                continue
            # Construct the file path
            file_path = os.path.join(root, file)
            block_name = os.path.basename(root)

            # Parse the file and find the function
            func_node, docstring = parse_python_file(file_path, block_name)

            if not func_node:
                print(
                    f"{ERR_STRING} Could not find the {block_name} function in {block_name}.py! Please make sure there is a function called {block_name}."
                )
                continue

            if not docstring:
                print(f"{ERR_STRING} Docstring not found for {block_name}")
                error += 1
                continue

            # Process the docstring using docstring_parser
            parsed_docstring = parse_docstring(docstring)

            if not parsed_docstring.short_description:
                print(
                    f"{ERR_STRING} short_description not found for {block_name}"
                )
                error += 1

            if not parsed_docstring.long_description:
                # it is okay to not have a long description
                parsed_docstring.long_description = ""

            if not parsed_docstring.params:
                print(f"{ERR_STRING} 'Parameters' not found for {block_name}")
                error += 1

            if not parsed_docstring.many_returns:
                print(f"{ERR_STRING} 'Returns' not found for {block_name}")
                error += 1

            # Build the JSON data using shared utility
            docstring_json_data = create_docstring_json(parsed_docstring, include_empty_fields=False)
            # Remove the "docstring" key since we'll wrap it later
            if isinstance(docstring_json_data, dict) and "docstring" in docstring_json_data:
                docstring_json_data = docstring_json_data["docstring"]

            # Write the data to a JSON file in the same directory
            output_file_path = os.path.join(root, "block_data.json")

            if os.path.exists(output_file_path):
                with open(output_file_path, "r") as output_file:
                    existing_json_data = json.load(output_file)
            else:
                existing_json_data = {}

            existing_json_data["docstring"] = docstring_json_data

            with open(output_file_path, "w") as output_file:
                json.dump(existing_json_data, output_file, indent=2)

    if error > 0:
        print(f"Found {error} [bold red]ERRORS[/bold red] with docstring formatting!")
        return False

    return True
