/**
 * GitHub repo scraper for Worker-native ingestion.
 *
 * Uses GitHub REST API (Trees + Contents) instead of tarball download
 * to avoid binary decompression in Workers. Zero npm dependencies.
 */

export interface GitHubFile {
  path: string;
  extension: string;
  content: string;
  size: number;
}

export interface ScrapedRepo {
  files: GitHubFile[];
  sdkVersion?: string;
  isVersionDeprecated?: boolean;
  totalFiles: number;
  fetchedFiles: number;
}

interface TreeEntry {
  path: string;
  mode: string;
  type: "blob" | "tree";
  sha: string;
  size?: number;
  url: string;
}

interface TreeResponse {
  sha: string;
  url: string;
  tree: TreeEntry[];
  truncated: boolean;
}

interface ContentsResponse {
  content?: string;
  encoding?: string;
  download_url?: string;
  size: number;
}

// File filtering configuration
const ALLOWED_EXTENSIONS = new Set([
  ".rs",
  ".toml",
  ".md",
  ".json",
  ".ts",
  ".js",
  ".sol",
  ".yaml",
  ".yml",
]);

const SKIP_DIRS = new Set([
  "node_modules",
  "target",
  ".git",
  "vendor",
  "dist",
  "build",
  "__pycache__",
  ".cargo",
  ".github",
  "third_party",
  ".next",
  "artifacts",
  "cache",
  "coverage",
  "out",
]);

const SKIP_FILES = new Set([
  "Cargo.lock",
  "package-lock.json",
  "yarn.lock",
  "pnpm-lock.yaml",
  "bun.lockb",
]);

const MAX_FILE_SIZE = 100 * 1024; // 100KB per file
const MAX_FILES = 500;
const MAX_TOTAL_SIZE = 5 * 1024 * 1024; // 5MB total content

const MINIMUM_SDK_VERSION = "0.8.0";

/**
 * Parse a GitHub URL into owner and repo.
 */
export function parseRepoUrl(url: string): { owner: string; repo: string } {
  const cleaned = url.replace(/\/$/, "").replace(/\.git$/, "");
  const match = cleaned.match(
    /github\.com\/([^/]+)\/([^/]+)/
  );
  if (!match) {
    throw new Error(`Invalid GitHub URL: ${url}`);
  }
  return { owner: match[1], repo: match[2] };
}

/**
 * List files in a GitHub repo using the Trees API.
 * Returns filtered list of blob entries matching allowed extensions.
 */
export async function listRepoFiles(
  owner: string,
  repo: string,
  token?: string
): Promise<TreeEntry[]> {
  const headers: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "User-Agent": "ArbBuilder/2.0",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/git/trees/HEAD?recursive=1`,
    { headers }
  );

  if (!response.ok) {
    throw new Error(
      `GitHub API error ${response.status}: ${await response.text()}`
    );
  }

  const data = (await response.json()) as TreeResponse;

  // Filter to relevant files
  const filtered = data.tree.filter((entry) => {
    if (entry.type !== "blob") return false;

    // Check extension
    const ext = getExtension(entry.path);
    if (!ALLOWED_EXTENSIONS.has(ext)) return false;

    // Check path segments for skip dirs
    const parts = entry.path.split("/");
    for (const part of parts.slice(0, -1)) {
      if (SKIP_DIRS.has(part)) return false;
    }

    // Check skip files
    const filename = parts[parts.length - 1];
    if (SKIP_FILES.has(filename)) return false;

    // Check size (Trees API includes size for blobs)
    if (entry.size && entry.size > MAX_FILE_SIZE) return false;

    return true;
  });

  // Prioritize: .rs and .toml first (for SDK version detection), then others
  filtered.sort((a, b) => {
    const extA = getExtension(a.path);
    const extB = getExtension(b.path);
    const priorityA = extA === ".rs" || extA === ".toml" ? 0 : 1;
    const priorityB = extB === ".rs" || extB === ".toml" ? 0 : 1;
    if (priorityA !== priorityB) return priorityA - priorityB;
    return a.path.localeCompare(b.path);
  });

  // Cap at MAX_FILES
  return filtered.slice(0, MAX_FILES);
}

/**
 * Fetch content of a single file from GitHub Contents API.
 * Returns decoded UTF-8 text content.
 */
export async function fetchFileContent(
  owner: string,
  repo: string,
  path: string,
  token?: string
): Promise<string> {
  const headers: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "User-Agent": "ArbBuilder/2.0",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}`,
    { headers }
  );

  if (!response.ok) {
    throw new Error(
      `GitHub Contents API error ${response.status} for ${path}`
    );
  }

  const data = (await response.json()) as ContentsResponse;

  // GitHub returns base64-encoded content for files under 100KB
  if (data.content && data.encoding === "base64") {
    // Remove newlines that GitHub adds to base64 content
    const cleaned = data.content.replace(/\n/g, "");
    return atob(cleaned);
  }

  // For larger files, fall back to download_url
  if (data.download_url) {
    const dlResponse = await fetch(data.download_url);
    if (!dlResponse.ok) {
      throw new Error(`Download failed for ${path}: HTTP ${dlResponse.status}`);
    }
    return await dlResponse.text();
  }

  throw new Error(`No content available for ${path}`);
}

/**
 * Scrape a GitHub repository: list files, fetch contents, detect SDK version.
 * Fetches up to maxFiles files per invocation, starting from fileOffset.
 */
export async function scrapeGithubRepo(
  url: string,
  token?: string,
  maxFiles?: number,
  fileOffset?: number
): Promise<ScrapedRepo> {
  const { owner, repo } = parseRepoUrl(url);
  const limit = maxFiles ?? 50;
  const offset = fileOffset ?? 0;

  // List all matching files
  const tree = await listRepoFiles(owner, repo, token);

  // Fetch files in order, respecting limits
  const files: GitHubFile[] = [];
  let totalSize = 0;
  let sdkVersion: string | undefined;

  const filesToFetch = tree.slice(offset, offset + limit);

  for (const entry of filesToFetch) {
    try {
      const content = await fetchFileContent(owner, repo, entry.path, token);

      if (!content.trim()) continue;

      const fileSize = new TextEncoder().encode(content).length;
      if (totalSize + fileSize > MAX_TOTAL_SIZE) break;

      const ext = getExtension(entry.path);

      files.push({
        path: entry.path,
        extension: ext,
        content,
        size: fileSize,
      });
      totalSize += fileSize;

      // Detect SDK version from Cargo.toml
      if (entry.path.endsWith("Cargo.toml") && !sdkVersion) {
        sdkVersion = extractSdkVersion(content);
      }
    } catch {
      // Skip files that fail to fetch
      continue;
    }
  }

  const isVersionDeprecated = sdkVersion
    ? compareSdkVersion(sdkVersion, MINIMUM_SDK_VERSION) < 0
    : false;

  return {
    files,
    sdkVersion,
    isVersionDeprecated,
    totalFiles: tree.length,
    fetchedFiles: files.length,
  };
}

/**
 * Extract stylus-sdk version from Cargo.toml content.
 */
export function extractSdkVersion(cargoContent: string): string | undefined {
  // Pattern 1: Simple format - stylus-sdk = "0.9.0"
  let match = cargoContent.match(/stylus-sdk\s*=\s*"([^"]+)"/);
  if (match) return match[1];

  // Pattern 2: Complex format - stylus-sdk = { version = "0.9.0", ... }
  match = cargoContent.match(
    /stylus-sdk\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"/s
  );
  if (match) return match[1];

  return undefined;
}

/**
 * Compare two semantic versions for SDK deprecation check.
 */
function compareSdkVersion(v1: string, v2: string): number {
  const parse = (v: string) => {
    const cleaned = v.replace(/^[\^~>=<]+/, "");
    return cleaned
      .split(".")
      .slice(0, 3)
      .map((x) => parseInt(x, 10) || 0);
  };

  const p1 = parse(v1);
  const p2 = parse(v2);
  while (p1.length < 3) p1.push(0);
  while (p2.length < 3) p2.push(0);

  for (let i = 0; i < 3; i++) {
    if (p1[i] < p2[i]) return -1;
    if (p1[i] > p2[i]) return 1;
  }
  return 0;
}

/**
 * Get file extension including the dot.
 */
function getExtension(path: string): string {
  const lastDot = path.lastIndexOf(".");
  if (lastDot === -1) return "";
  return path.slice(lastDot);
}
