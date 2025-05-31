import type { NextApiRequest, NextApiResponse } from "next";
import path from "path";
import fs from "fs/promises";

type Data = {
  success: boolean;
  message?: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data>,
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res
      .status(405)
      .json({ success: false, message: "Method not allowed" });
  }

  try {
    const { id, name, content } = req.body;

    if (!id || !name || typeof content !== "string") {
      return res
        .status(400)
        .json({ success: false, message: "Invalid payload" });
    }

    // Sanitize filename (basic example)
    const safeName = name.replace(/[^a-zA-Z0-9.\-_]/g, "_");

    // Ensure directory exists
    const dir = path.resolve(process.cwd(), "savedFiles");
    await fs.mkdir(dir, { recursive: true });

    // Save file content
    const filePath = path.join(dir, safeName);
    await fs.writeFile(filePath, content, "utf8");

    return res
      .status(200)
      .json({ success: true, message: "File saved successfully" });
  } catch (error) {
    console.error("Save file error:", error);
    return res
      .status(500)
      .json({ success: false, message: "Internal server error" });
  }
}
