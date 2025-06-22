# Third-Party Licenses

This file contains the licenses and acknowledgments for third-party software used in AtlasVibe.

## AtlasVibe is a Fork of Flojoy Studio

AtlasVibe is based on Flojoy Studio, originally developed by the Flojoy team and released under the MIT License.

- Original Project: https://github.com/flojoy-ai/studio
- License: MIT License
- Copyright (c) 2023-2024 Flojoy

## Primary Dependencies

### Python Dependencies

#### MIT License

The following dependencies are licensed under the MIT License:

- **FastAPI** - https://github.com/tiangolo/fastapi
- **Pydantic** - https://github.com/pydantic/pydantic
- **Plotly** - https://github.com/plotly/plotly.py
- **uvicorn** - https://github.com/encode/uvicorn
- **python-dotenv** - https://github.com/theskumar/python-dotenv
- **requests** - https://github.com/psf/requests
- **pytest** - https://github.com/pytest-dev/pytest
- **black** - https://github.com/psf/black
- **ruff** - https://github.com/astral-sh/ruff

#### Apache License 2.0

The following dependencies are licensed under the Apache License 2.0:

- **Prefect** - https://github.com/PrefectHQ/prefect
- **Transformers** - https://github.com/huggingface/transformers
- **griffe** - https://github.com/mkdocstrings/griffe

#### BSD 3-Clause License

The following dependencies are licensed under the BSD 3-Clause License:

- **NumPy** - https://github.com/numpy/numpy
- **Pandas** - https://github.com/pandas-dev/pandas
- **scikit-image** - https://github.com/scikit-image/scikit-image
- **scipy** - https://github.com/scipy/scipy

#### Other Licenses

- **PyYAML** - MIT License - https://github.com/yaml/pyyaml
- **Pillow** - PIL Software License - https://github.com/python-pillow/Pillow
- **psutil** - BSD 3-Clause License - https://github.com/giampaolo/psutil

### JavaScript/Node Dependencies

#### MIT License

The following dependencies are licensed under the MIT License:

- **React** - https://github.com/facebook/react
- **Electron** - https://github.com/electron/electron
- **ReactFlow** - https://github.com/wbkd/react-flow
- **Plotly.js** - https://github.com/plotly/plotly.js
- **CodeMirror** - https://github.com/codemirror/codemirror5
- **Radix UI** - https://github.com/radix-ui/primitives
- **Tailwind CSS** - https://github.com/tailwindlabs/tailwindcss
- **Zustand** - https://github.com/pmndrs/zustand
- **React Hook Form** - https://github.com/react-hook-form/react-hook-form
- **Zod** - https://github.com/colinhacks/zod
- **Vite** - https://github.com/vitejs/vite
- **TypeScript** - https://github.com/microsoft/TypeScript
- **ESLint** - https://github.com/eslint/eslint
- **Prettier** - https://github.com/prettier/prettier

#### Apache License 2.0

- **TypeScript** (also listed above, dual licensed) - https://github.com/microsoft/TypeScript

## License Compatibility

All dependencies listed above are compatible with the MIT License used by AtlasVibe. The project complies with all license requirements:

1. **MIT Licensed Dependencies**: No additional requirements beyond including the copyright notice.
2. **Apache 2.0 Licensed Dependencies**: Compatible with MIT. Patent grants from Apache 2.0 provide additional protection.
3. **BSD 3-Clause Licensed Dependencies**: Compatible with MIT. Copyright notices are preserved.

## AI Model Licenses

When using AI models through the Transformers library, please note that individual models may have their own licenses separate from the library license. Users must verify and comply with the specific license of each model they use.

## Full License Texts

For the complete text of each license, please refer to:

- MIT License: https://opensource.org/licenses/MIT
- Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
- BSD 3-Clause License: https://opensource.org/licenses/BSD-3-Clause

## Updates

This file was last updated on: 2025-01-22

To update this file, run:

```bash
# Python dependencies
uv pip list --format json > python-deps.json

# JavaScript dependencies
pnpm list --json > js-deps.json
```

Then verify the licenses of any new dependencies.
