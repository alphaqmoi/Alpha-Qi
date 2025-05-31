// pages/api/renameFile.ts
import { NextApiRequest, NextApiResponse } from "next";
import fs from "fs/promises";
import path from "path";
import simpleGit from "simple-git";

const git = simpleGit();

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== "POST") return res.status(405).end();

  const { oldUri, newUri } = req.body;
  const root = path.resolve(process.cwd(), "savedFiles");

  const oldPath = path.join(root, path.basename(oldUri));
  const newPath = path.join(root, path.basename(newUri));

  try {
    await fs.rename(oldPath, newPath);
    await git.mv(oldPath, newPath);
    await git.commit(
      `Renamed file: ${path.basename(oldUri)} → ${path.basename(newUri)}`,
    );
    return res.status(200).json({ success: true });
  } catch (err) {
    console.error("Rename error:", err);
    return res.status(500).json({ success: false, message: err.message });
  }
}
