import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { BlockManifest, BlockMetadata } from "@/renderer/types/manifest";
import { ok, Result, safeTry } from "neverthrow";
import { getManifest, getMetadata } from "@/renderer/lib/api";
import { HTTPError } from "ky";
import { ZodError } from "zod";
import { useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { useProjectStore } from "./project";

type State = {
  standardBlocksManifest: BlockManifest | undefined;
  customBlocksManifest: BlockManifest | undefined | null;
  standardBlocksMetadata: BlockMetadata | undefined;
  customBlocksMetadata: BlockMetadata | undefined | null;
  manifestChanged: boolean;
  regeneratingBlocks: Set<string>; // Track which blocks are being regenerated
};

type Actions = {
  fetchManifest: () => Promise<Result<void, HTTPError | ZodError>>;
  importCustomBlocks: (
    startup: boolean,
  ) => Promise<Result<void, HTTPError | ZodError>>;
  setManifestChanged: (val: boolean) => void;
  setBlockRegenerating: (blockPath: string, isRegenerating: boolean) => void;
  clearRegeneratingBlocks: () => void;
};

// TODO: Fix eslint-plugin-neverthrow to allow this
// so that we can use the plugin for the whole codebase
export const useManifestStore = create<State & Actions>()(
  immer((set, get) => ({
    standardBlocksManifest: undefined,
    customBlocksManifest: undefined,
    standardBlocksMetadata: undefined,
    customBlocksMetadata: undefined,
    manifestChanged: true,
    regeneratingBlocks: new Set(),

    fetchManifest: () => {
      return safeTry(async function* () {
        // Get current project path
        const projectPath = useProjectStore.getState().path;

        // Always fetch standard blocks
        const standardManifest = yield* (await getManifest(undefined, projectPath)).safeUnwrap();
        const standardMetadata = yield* (await getMetadata(undefined, false, projectPath)).safeUnwrap();

        // If we have a project path, also fetch its custom blocks
        let customManifest = null;
        let customMetadata = null;

        if (projectPath) {
          // For sample projects, the path might be relative (e.g., "sample_projects/...")
          // The backend will handle resolving the actual path
          const customBlocksPath = projectPath.startsWith('sample_projects/')
            ? projectPath
            : `${projectPath}/atlasvibe_blocks`;

          try {
            customManifest = yield* (await getManifest(customBlocksPath)).safeUnwrap();
            customMetadata = yield* (await getMetadata(customBlocksPath, false)).safeUnwrap();
          } catch (error) {
            // It's okay if there are no custom blocks in the project
            console.log("No custom blocks found for project:", projectPath);
          }
        }

        set({
          standardBlocksManifest: standardManifest,
          standardBlocksMetadata: standardMetadata,
          customBlocksManifest: customManifest,
          customBlocksMetadata: customMetadata,
        });

        return ok(undefined);
      });
    },

    importCustomBlocks: async (startup: boolean) => {
      const blocksDirPath = !startup
        ? await window.api.pickDirectory(false)
        : await window.api.getCustomBlocksDir();

      if (!blocksDirPath) {
        if (get().customBlocksManifest !== undefined) return ok(undefined);
        set({
          manifestChanged: true,
          customBlocksManifest: null,
          customBlocksMetadata: null,
        });
        return ok(undefined);
      }

      return safeTry(async function* () {
        const manifest = yield* (await getManifest(blocksDirPath)).safeUnwrap();
        const metadata = yield* (
          await getMetadata(blocksDirPath, !startup)
        ).safeUnwrap();
        set({
          manifestChanged: true,
          customBlocksManifest: manifest,
          customBlocksMetadata: metadata,
        });
        window.api.cacheCustomBlocksDir(blocksDirPath);
        return ok(undefined);
      });
    },

    setManifestChanged: (val: boolean) => {
      set({ manifestChanged: val });
    },

    setBlockRegenerating: (blockPath: string, isRegenerating: boolean) => {
      set((state) => {
        const newSet = new Set(state.regeneratingBlocks);
        if (isRegenerating) {
          newSet.add(blockPath);
        } else {
          newSet.delete(blockPath);
        }
        state.regeneratingBlocks = newSet;
      });
    },

    clearRegeneratingBlocks: () => {
      set({ regeneratingBlocks: new Set() });
    },
  })),
);

export const useManifest = () => {
  const { manifest, customManifest } = useManifestStore(
    useShallow((state) => ({
      manifest: state.standardBlocksManifest,
      customManifest: state.customBlocksManifest,
    })),
  );

  return useMemo(() => {
    if (manifest === undefined || customManifest === undefined) {
      return undefined;
    }

    return customManifest
      ? {
          ...manifest,
          children: manifest.children.concat(customManifest.children),
        }
      : manifest;
  }, [manifest, customManifest]);
};

export const useMetadata = () => {
  const { metadata, customMetadata } = useManifestStore(
    useShallow((state) => ({
      metadata: state.standardBlocksMetadata,
      customMetadata: state.customBlocksMetadata,
    })),
  );

  return useMemo(() => {
    const html = document.getElementsByTagName("html")[0];
    if (metadata === undefined || customMetadata === undefined) {
      html.removeAttribute("data-blockmetadata");
      return undefined;
    }
    html.setAttribute("data-blockmetadata", "true");

    return customMetadata
      ? {
          ...metadata,
          ...customMetadata,
        }
      : metadata;
  }, [metadata, customMetadata]);
};
