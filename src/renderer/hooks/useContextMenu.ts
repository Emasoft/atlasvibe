/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { useCallback, useRef, useState } from "react";

export const useContextMenu = <MI>() => {
  const [menu, setMenu] = useState<MI | null>(null);
  const flowRef = useRef<HTMLDivElement | null>(null);
  const onPaneClick = useCallback(() => setMenu(null), [setMenu]);

  return { menu, setMenu, flowRef, onPaneClick };
};
