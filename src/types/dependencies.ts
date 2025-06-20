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


