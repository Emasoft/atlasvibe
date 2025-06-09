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
import { migrateProjectFormat, validateProjectReferences } from "@/renderer/lib/project-migration";

export const useLoadApp = () => {
  const loadProject = useLoadProject();

  const setShowWelcomeScreen = useAppStore(
    useShallow((state) => state.setShowWelcomeScreen),
  );

  const openFilePicker = async () => {
    const res = await fromPromise(window.api.openFilePicker(), (e) =>
      parseElectronError((e as Error).message),
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
      toast.error("Invalid JSON", { description: "Failed to parse project file" });
      return;
    }
    
    const { project: migratedProject, migrated } = migrateProjectFormat(parsedData);
    
    if (migrated) {
      toast.info("Project migrated", { 
        description: "Project file was updated to the latest format" 
      });
    }
    
    // Validate and load
    const loadRes = tryParse(Project)(migratedProject)
      .andThen((proj) => {
        // Validate custom block references
        const errors = validateProjectReferences(proj);
        if (errors.length > 0) {
          toast.warning("Project validation warnings", {
            description: errors.join(", ")
          });
        }
        return loadProject(proj, filePath);
      })
      .map(() => setShowWelcomeScreen(false));

    if (loadRes.isOk()) {
      return;
    }

    if (loadRes.error instanceof ZodError) {
      toast.error("Project validation error", {
        description: fromZodError(loadRes.error).toString(),
      });
    } else {
      toast.error("Error loading project", {
        description: loadRes.error.message,
      });
    }
  };

  return openFilePicker;
};
