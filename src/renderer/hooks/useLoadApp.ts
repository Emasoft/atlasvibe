/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { useAppStore } from "@/renderer/stores/app";
import { Project } from "@/renderer/types/project";

import { useShallow } from "zustand/react/shallow";
import { useLoadProject } from "@/renderer/stores/project";
import { tryParse } from "@/types/result";
import { fromPromise } from "neverthrow";
import { toast } from "sonner";
import { ZodError } from "zod";
import { fromZodError } from "zod-validation-error";
import { parseElectronError } from "@/renderer/utils/parse-error";
import {
  migrateProjectFormat,
  validateProjectReferences,
} from "@/renderer/lib/project-migration";

export const useLoadApp = () => {
  const loadProject = useLoadProject();

  const setShowWelcomeScreen = useAppStore(
    useShallow((state) => state.setShowWelcomeScreen),
  );

  const openFilePicker = async () => {
    const res = await fromPromise(
      window.api.openFilePicker(["atlasvibe", "json"]),
      (e) => parseElectronError((e as Error).message),
    );
    if (res.isErr()) {
      toast.error("Failed to open file", { description: res.error });
      return;
    }
    if (res.value === undefined) {
      return;
    }
    const { fileContent, filePath } = res.value;

    // Parse and migrate project format if needed
    let parsedData;
    try {
      parsedData = JSON.parse(fileContent);
    } catch (e) {
      toast.error("Invalid JSON", {
        description: "Failed to parse project file",
      });
      return;
    }

    const { project: migratedProject, migrated } =
      migrateProjectFormat(parsedData);

    if (migrated) {
      toast.info("Project migrated", {
        description: "Project file was updated to the latest format",
      });
    }

    // Validate and load
    const parseRes = tryParse(Project)(migratedProject);
    if (parseRes.isErr()) {
      if (parseRes.error instanceof ZodError) {
        toast.error("Project validation error", {
          description: fromZodError(parseRes.error).toString(),
        });
      } else {
        toast.error("Error parsing project", {
          description:
            (parseRes.error as Error).message || String(parseRes.error),
        });
      }
      return;
    }

    const proj = parseRes.value;

    // Validate custom block references
    const errors = validateProjectReferences(proj);
    if (errors.length > 0) {
      toast.warning("Project validation warnings", {
        description: errors.join(", "),
      });
    }

    // Load project asynchronously
    const loadRes = await loadProject(proj, filePath);
    if (loadRes.isOk()) {
      setShowWelcomeScreen(false);
    } else {
      toast.error("Error loading project", {
        description: loadRes.error.message,
      });
    }
  };

  return openFilePicker;
};
