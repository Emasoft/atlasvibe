/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { z } from "zod";

export const GalleryApp = z.object({
  title: z.string(),
  description: z.string(),
  appPath: z.string(),
  imagePath: z.string(),
  youtubeLink: z.optional(z.string()),
  relevantNodes: z.array(
    z.object({
      name: z.string(),
      docs: z.string(),
    }),
  ),
  cloudDemoEnabled: z.boolean(),
});

export type GalleryApp = z.infer<typeof GalleryApp>;

export const GalleryData = z.record(z.string(), z.array(GalleryApp));

export type GalleryData = z.infer<typeof GalleryData>;
