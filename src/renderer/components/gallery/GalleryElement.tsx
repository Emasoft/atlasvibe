/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { useNodesInitialized, useReactFlow } from "reactflow";
import { YoutubeIcon } from "lucide-react";
import { Button } from "@/renderer/components/ui/button";
import { Avatar, AvatarImage } from "@/renderer/components/ui/avatar";
import { GalleryApp } from "@/renderer/types/gallery";
import { useEffect } from "react";
import { useLoadProject } from "@/renderer/stores/project";
import { Project } from "@/renderer/types/project";
import { tryParse } from "@/types/result";
import { toast } from "sonner";
import { ZodError } from "zod";
import { fromZodError } from "zod-validation-error";
import { loadSampleProject, getSampleProjectPath } from "@/renderer/utils/gallery-loader";

export interface AppGalleryElementProps {
  galleryApp: GalleryApp;
  setIsGalleryOpen: (isOpen: boolean) => void;
}

export const GalleryElement = ({
  galleryApp,
  setIsGalleryOpen,
}: AppGalleryElementProps) => {
  const loadProject = useLoadProject();

  const rfInstance = useReactFlow();
  const nodesInitialized = useNodesInitialized();

  const handleAppLoad = async () => {
    // Show loading toast
    const loadingToast = toast.loading(`Loading ${galleryApp.title}...`);

    try {
      // Extract project name from path (e.g., "sample_projects/loop" -> "loop")
      const projectName = galleryApp.appPath.replace("sample_projects/", "");

      // Load from the new folder-based structure
      const projectResult = await loadSampleProject(projectName);

      if (projectResult.isErr()) {
        toast.dismiss(loadingToast);
        toast.error("Failed to load sample project", {
          description: projectResult.error.message,
        });
        return;
      }

      // Load the project with its path so it knows where to find custom blocks
      const projectPath = getSampleProjectPath(galleryApp.appPath);
      const res = tryParse(Project)(projectResult.value)
        .andThen((proj) => loadProject(proj, projectPath))
        .map(() => {
          toast.dismiss(loadingToast);
          toast.success(`Loaded ${galleryApp.title}`);
          setIsGalleryOpen(false);
        });

      if (res.isErr()) {
        toast.dismiss(loadingToast);
        if (res.error instanceof ZodError) {
          toast.error("Project validation error", {
            description: fromZodError(res.error).toString(),
          });
        } else {
          toast.error("Error loading project", {
            description: res.error.message,
          });
        }
      }
    } catch (error) {
      toast.dismiss(loadingToast);
      toast.error("Unexpected error loading project", {
        description: error instanceof Error ? error.message : String(error),
      });
    }
  };

  useEffect(() => {
    // fixes the issue that app is not centered in the viewport
    if (nodesInitialized) {
      rfInstance.fitView({
        padding: 0.8,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodesInitialized]);

  return (
    <div className="m-1 min-h-40">
      <div className="flex w-full">
        <Avatar className="m-1 h-36 w-36">
          <AvatarImage className="object-contain" src={galleryApp.imagePath} />
        </Avatar>
        <div className="px-2" />

        <div className="flex grow flex-col items-start">
          <div className="text-xl font-semibold">{galleryApp.title}</div>
          <div className="text-sm font-thin">{galleryApp.description}</div>

          <div className="py-1" />

          <div>
            {galleryApp.relevantNodes.map((node) => (
              <a
                href={node.docs}
                key={node.name}
                target="_blank"
                className="mr-2 rounded-md bg-muted p-1 text-sm"
              >
                {node.name}
              </a>
            ))}
          </div>

          <div className="py-1" />

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              data-testid={galleryApp.title.toLowerCase().split(" ").join("_")}
              onClick={async () => {
                await handleAppLoad();
              }}
            >
              Load
            </Button>

            {galleryApp.youtubeLink && (
              <a href={galleryApp.youtubeLink} target="_blank">
                <Button variant="outline" size="sm" className="">
                  <YoutubeIcon />
                </Button>
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
