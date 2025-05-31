export type LspFileMetadata = {
  uri: string;
  name: string;
  language: string;
  lastModified: string;
  version: number;
  symbolIndex: string[];
  dependencies: string[];
};

export type MetadataJsonSchema = {
  projectId: string;
  files: Record<string, LspFileMetadata>;
  lspCacheVersion: string;
};

const LOCAL_STORAGE_KEY = "lspMetadataCache";

export class LspCacheService {
  private cache: MetadataJsonSchema | null = null;

  async load(): Promise<MetadataJsonSchema | null> {
    const data = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (data) {
      try {
        this.cache = JSON.parse(data);
        return this.cache;
      } catch (e) {
        console.error("Invalid LSP metadata cache:", e);
      }
    }
    return null;
  }

  async save(metadata: MetadataJsonSchema): Promise<void> {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(metadata, null, 2));
    this.cache = metadata;
  }

  getFile(uri: string): LspFileMetadata | null {
    return this.cache?.files[uri] ?? null;
  }

  updateFile(uri: string, metadata: Partial<LspFileMetadata>) {
    if (!this.cache || !this.cache.files[uri]) return;
    this.cache.files[uri] = { ...this.cache.files[uri], ...metadata };
    this.save(this.cache);
  }

  renameFile(oldUri: string, newUri: string, newName: string) {
    if (!this.cache || !this.cache.files[oldUri]) return;
    const oldMeta = this.cache.files[oldUri];
    delete this.cache.files[oldUri];
    this.cache.files[newUri] = {
      ...oldMeta,
      uri: newUri,
      name: newName,
      lastModified: new Date().toISOString(),
      version: oldMeta.version + 1,
    };
    this.save(this.cache);
  }

  deleteFile(uri: string) {
    if (!this.cache || !this.cache.files[uri]) return;
    delete this.cache.files[uri];
    this.save(this.cache);
  }
}
