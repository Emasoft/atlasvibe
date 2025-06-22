/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export type ParamValueType =
  | "str"
  | "float"
  | "int"
  | "list[int]"
  | "list[str]"
  | "list[float]"
  | "Array"
  | "bool"
  | "select"
  | "NodeReference"
  | "CameraDevice"
  | "SerialDevice"
  | "VisaDevice"
  | "NIDAQmxDevice"
  | "NIDMMDevice"
  | "CameraConnection"
  | "SerialConnection"
  | "VisaConnection"
  | "NIConnection"
  | "File"
  | "Directory"
  | "TextArea"
  | "Secret"
  | "unknown";
