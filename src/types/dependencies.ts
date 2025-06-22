/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

// Dependency management types
// These are generic types for managing Python dependencies

export type DependencyGroupInfo = {
  name: string;
  description: string;
  dependencies: PythonDependency[];
  status: "installed" | "dne";
};

export type PythonDependency = {
  name: string;
  version: string;
  description?: string;
  installed: boolean;
};
