/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    //"plugin:react/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  plugins: ["react-refresh"],
  rules: {
    "no-restricted-imports": [
      "warn",
      {
        patterns: [
          {
            group: ["../"],
            message: "Relative imports are not allowed.",
          },
        ],
      },
    ],
  },
  settings: {
    react: {
      version: "detect",
    },
  },
};
