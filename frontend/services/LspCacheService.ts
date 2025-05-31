import fs from "fs/promises";
import path from "path";

const METADATA_DIR = path.resolve(process.cwd(), "savedFiles", ".metadata");

export class LspCacheService {
  static async getMetadata(uri: string): Promise<any | null> {
    try {
      const baseName = path.basename(uri).replace(/\.[^/.]+$/, "");
      const filePath = path.join(METADATA_DIR, `${baseName}.metadata.json`);
      const raw = await fs.readFile(filePath, "utf8");
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  static async saveMetadata(uri: string, metadata: any): Promise<void> {
    try {
      await fs.mkdir(METADATA_DIR, { recursive: true });
      const baseName = path.basename(uri).replace(/\.[^/.]+$/, "");
      const filePath = path.join(METADATA_DIR, `${baseName}.metadata.json`);
      await fs.writeFile(filePath, JSON.stringify(metadata, null, 2), "utf8");
    } catch (err) {
      console.error("Error saving metadata:", err);
      throw err;
    }
  }
}
