/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { Textarea } from "@/renderer/components/ui/textarea";
import { useEffect, useRef } from "react";

type Props = {
  onValueChange: (val: string) => void;
  value: string;
};

export const AutosizingTextarea = ({ onValueChange, value }: Props) => {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  const adjustHeight = () => {
    if (!ref.current) {
      return;
    }
    ref.current.style.height = "0px";
    ref.current.style.height = ref.current.scrollHeight + 10 + "px";
  };

  useEffect(() => {
    adjustHeight();
  }, [value]);

  const handleChange = (e) => {
    onValueChange(e.target.value);
  };

  return (
    <Textarea
      ref={ref}
      value={value}
      onChange={handleChange}
      className="max-h-96 resize-none"
    ></Textarea>
  );
};
