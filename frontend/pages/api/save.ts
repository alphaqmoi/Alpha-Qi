import type { NextApiRequest, NextApiResponse } from "next";
import path from "path";
import fs from "fs/promises";

type Data = { success: boolean; message?: string };

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
    const { uri, metadata } = req.body;

    if (!uri || typeof metadata !== "object") {
      return res
        .status(400)
        .json({ success: false, message: "Invalid payload" });
    }

    const metadataDir = path.resolve(process.cwd(), "savedFiles", ".metadata");
    await fs.mkdir(metadataDir, { recursive: true });

    const baseName = path.basename(uri).replace(/\.[^/.]+$/, "");
    const metadataPath = path.join(metadataDir, `${baseName}.metadata.json`);
    await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2), "utf8");

    return res.status(200).json({ success: true });
  } catch (err) {
    console.error("Metadata save error:", err);
    return res.status(500).json({ success: false, message: "Server error" });
  }
}
