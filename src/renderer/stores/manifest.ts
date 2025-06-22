/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

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

        // Fetch manifest with project path to include project blocks
        // The backend will handle both standard blocks and project blocks in one call
        const manifest = yield* (await getManifest(undefined, projectPath)).safeUnwrap();
        const metadata = yield* (await getMetadata(undefined, false, projectPath)).safeUnwrap();

        set({
          standardBlocksManifest: manifest,
          standardBlocksMetadata: metadata,
          // Clear custom blocks - they're now included in the main manifest
          customBlocksManifest: null,
          customBlocksMetadata: null,
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
