import type { NextApiRequest, NextApiResponse } from "next";
import { execFileSync } from "child_process";
import prettier from "prettier";

type Data = {
  formatted?: string;
  error?: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data>,
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { fileId, content } = req.body;
  if (typeof content !== "string") {
    return res.status(400).json({ error: "Invalid content" });
  }

  try {
    if (fileId.endsWith(".js") || fileId.endsWith(".ts")) {
      // Format with Prettier
      const formatted = prettier.format(content, { parser: "typescript" });
      return res.status(200).json({ formatted });
    } else if (fileId.endsWith(".py")) {
      // Format with Black via child process
      // We echo content to Black via stdin and read stdout result

      const result = execFileSync("black", ["-"], {
        input: content,
        encoding: "utf-8",
      });

      return res.status(200).json({ formatted: result });
    } else {
      return res
        .status(400)
        .json({ error: "Unsupported file type for formatting" });
    }
  } catch (error: any) {
    console.error("Format error:", error);
    return res
      .status(500)
      .json({ error: error.message || "Formatting failed" });
  }
}
