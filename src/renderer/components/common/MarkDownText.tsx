/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import clsx from "clsx";
import ReactMarkdown from "react-markdown";

type MarkDownTextProps = {
  text: string;
  isThumbnail?: boolean;
  containerClassName?: string;
  markDownclassName?: string;
};
const MarkDown = ({
  text,
  isThumbnail,
  containerClassName,
  markDownclassName,
}: MarkDownTextProps) => {
  console.log(text);
  return (
    <div
      className={clsx(
        "prose max-w-full p-6 dark:prose-invert",
        {
          "h-full overflow-hidden prose-headings:mb-0 prose-headings:mt-2 prose-p:mb-1 prose-p:mt-1 prose-p:first:mt-0 prose-ul:m-0 prose-li:m-0":
            isThumbnail,
        },
        containerClassName,
      )}
    >
      <ReactMarkdown skipHtml className={markDownclassName}>
        {text}
      </ReactMarkdown>
    </div>
  );
};

export default MarkDown;
