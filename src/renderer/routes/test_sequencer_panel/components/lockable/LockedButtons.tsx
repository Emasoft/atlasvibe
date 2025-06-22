/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { createLockedEntity } from "@/renderer/routes/test_sequencer_panel/utils/CreateLockedEntity";
import { Button } from "@/renderer/components/ui/button";

const LockableButton = createLockedEntity(Button);
export default LockableButton;
