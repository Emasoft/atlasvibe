/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { Button } from "@/renderer/components/ui/button";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/renderer/providers/theme-provider";

export const DarkModeToggle = () => {
  const { theme, setTheme } = useTheme();

  const toggleTheme = () => {
    if (theme === "dark") {
      setTheme("light");
    } else {
      setTheme("dark");
    }
  };

  return (
    <Button
      size="icon"
      variant="ghost"
      onClick={toggleTheme}
      data-testid="darkmode-toggle"
    >
      {theme === "dark" ? (
        <Moon className="stroke-accent1" />
      ) : (
        <Sun className="stroke-accent1" />
      )}
    </Button>
  );
};
