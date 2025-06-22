/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export enum ItemTypes {
  TestElementRow = "TestElementRow",
}

export enum Droppable {
  TestSequenceTable = "TestSequenceTable",
}

export type TestSequenceDragResult = {
  type: ItemTypes.TestElementRow;
  rowIdx: number;
};

export type DropResult = {
  type: Droppable;
};

export type TestSequenceDropResult = DropResult & {
  type: Droppable.TestSequenceTable;
  targetIdx: number;
};
