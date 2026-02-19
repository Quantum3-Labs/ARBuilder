/**
 * Chunking engine for Worker-native ingestion.
 *
 * TypeScript port of src/preprocessing/chunker.py.
 * Uses character-based token estimation (~4 chars/token) to avoid tiktoken.
 */

import type { GitHubFile } from "./github";
import { sha256 } from "./scraper";

export interface ProcessedChunk {
  id: string;
  content: string;
  chunk_index: number;
  source: string;
  url: string;
  title: string;
  category: string;
}

interface ChunkMetadata {
  url: string;
  title: string;
  category: string;
  source: "documentation" | "github";
}

// Language-specific split patterns (same as Python CodeChunker)
const CODE_SPLIT_PATTERNS: Record<string, RegExp[]> = {
  ".rs": [
    /(?=^(?:pub\s+)?fn\s+\w+)/m,
    /(?=^(?:pub\s+)?struct\s+\w+)/m,
    /(?=^(?:pub\s+)?enum\s+\w+)/m,
    /(?=^(?:pub\s+)?impl\s+)/m,
    /(?=^(?:pub\s+)?trait\s+\w+)/m,
    /(?=^(?:pub\s+)?mod\s+\w+)/m,
  ],
  ".ts": [
    /(?=^(?:export\s+)?(?:async\s+)?function\s+\w+)/m,
    /(?=^(?:export\s+)?class\s+\w+)/m,
    /(?=^(?:export\s+)?interface\s+\w+)/m,
    /(?=^(?:export\s+)?type\s+\w+)/m,
  ],
  ".js": [
    /(?=^(?:export\s+)?(?:async\s+)?function\s+\w+)/m,
    /(?=^(?:export\s+)?class\s+\w+)/m,
  ],
  ".sol": [
    /(?=^contract\s+\w+)/m,
    /(?=^\s*function\s+\w+)/m,
  ],
};

/**
 * Estimate token count using character approximation.
 * ~4 chars per token for English technical text, within ~10% accuracy.
 */
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

/**
 * Generate a deterministic chunk ID matching the Python pattern.
 * chunk_{sha256(url + content[:500])[:12]}
 */
export async function generateChunkId(
  url: string,
  content: string
): Promise<string> {
  const hashInput = url + content.slice(0, 500);
  const hash = await sha256(hashInput);
  return `chunk_${hash.slice(0, 12)}`;
}

/**
 * Chunk a documentation page into ProcessedChunks.
 * Port of Python DocumentChunker: split by headers -> paragraphs -> sentences.
 */
export async function chunkDocument(
  content: string,
  metadata: ChunkMetadata,
  maxTokens = 512,
  overlapTokens = 50
): Promise<ProcessedChunk[]> {
  if (!content.trim()) return [];

  // Split by markdown headers
  const sections = splitByHeaders(content);

  // Accumulate sections into chunks
  const rawChunks: string[] = [];
  let currentChunk = "";
  let currentTokens = 0;

  for (const section of sections) {
    const sectionTokens = estimateTokens(section);

    if (currentTokens + sectionTokens <= maxTokens) {
      currentChunk += section + "\n\n";
      currentTokens += sectionTokens;
    } else {
      if (currentChunk.trim()) {
        rawChunks.push(currentChunk.trim());
      }

      if (sectionTokens > maxTokens) {
        // Split large section by paragraphs
        const subChunks = splitLargeSection(section, maxTokens);
        rawChunks.push(...subChunks);
        currentChunk = "";
        currentTokens = 0;
      } else {
        currentChunk = section + "\n\n";
        currentTokens = sectionTokens;
      }
    }
  }

  if (currentChunk.trim()) {
    rawChunks.push(currentChunk.trim());
  }

  // Apply overlap
  const overlapped = applyOverlap(rawChunks, overlapTokens);

  // Create ProcessedChunk objects with IDs
  const chunks: ProcessedChunk[] = [];
  for (let i = 0; i < overlapped.length; i++) {
    const id = await generateChunkId(metadata.url, overlapped[i]);
    chunks.push({
      id,
      content: overlapped[i],
      chunk_index: i,
      source: metadata.source,
      url: metadata.url,
      title: metadata.title,
      category: metadata.category,
    });
  }

  return chunks;
}

/**
 * Chunk code files into ProcessedChunks.
 * Port of Python CodeChunker: split by language patterns -> line-based fallback.
 */
export async function chunkCode(
  files: GitHubFile[],
  metadata: Omit<ChunkMetadata, "title">,
  maxTokens = 1024,
  overlapLines = 5
): Promise<ProcessedChunk[]> {
  const chunks: ProcessedChunk[] = [];
  const repoName = metadata.url.replace(/\/$/, "").split("/").pop() || "";

  for (const file of files) {
    if (!file.content.trim()) continue;

    let rawChunks: string[];

    if (file.extension === ".md") {
      // Markdown files use document chunking logic
      const sections = splitByHeaders(file.content);
      rawChunks = accumulateSections(sections, 512);
      rawChunks = applyOverlap(rawChunks, 50);
    } else {
      // Code files use semantic splitting
      rawChunks = semanticSplitCode(file.content, file.extension);

      // If semantic split produced a single oversized chunk, fall back to lines
      if (rawChunks.length === 1 && estimateTokens(rawChunks[0]) > maxTokens) {
        rawChunks = lineSplit(file.content, maxTokens);
      }

      // Further split any oversized chunks
      const finalChunks: string[] = [];
      for (const chunk of rawChunks) {
        if (estimateTokens(chunk) > maxTokens) {
          finalChunks.push(...lineSplit(chunk, maxTokens));
        } else {
          finalChunks.push(chunk);
        }
      }
      rawChunks = finalChunks;

      // Apply line overlap
      rawChunks = applyLineOverlap(rawChunks, overlapLines);
    }

    // Create ProcessedChunk objects
    const title = `${repoName}/${file.path}`;
    for (let i = 0; i < rawChunks.length; i++) {
      const hashUrl = `${metadata.url}/${file.path}`;
      const id = await generateChunkId(hashUrl, rawChunks[i]);
      chunks.push({
        id,
        content: rawChunks[i],
        chunk_index: i,
        source: metadata.source,
        url: metadata.url,
        title,
        category: metadata.category,
      });
    }
  }

  return chunks;
}

// --- Internal helpers ---

function splitByHeaders(text: string): string[] {
  const sections = text.split(/(?=^#{1,6}\s)/m);
  return sections.map((s) => s.trim()).filter((s) => s.length > 0);
}

function splitLargeSection(section: string, maxTokens: number): string[] {
  const paragraphs = section.split("\n\n");
  const chunks: string[] = [];
  let currentChunk = "";
  let currentTokens = 0;

  for (const para of paragraphs) {
    const paraTokens = estimateTokens(para);

    if (currentTokens + paraTokens <= maxTokens) {
      currentChunk += para + "\n\n";
      currentTokens += paraTokens;
    } else {
      if (currentChunk.trim()) {
        chunks.push(currentChunk.trim());
      }

      if (paraTokens > maxTokens) {
        // Split by sentences
        chunks.push(...splitBySentences(para, maxTokens));
        currentChunk = "";
        currentTokens = 0;
      } else {
        currentChunk = para + "\n\n";
        currentTokens = paraTokens;
      }
    }
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}

function splitBySentences(text: string, maxTokens: number): string[] {
  const sentences = text.split(/(?<=[.!?])\s+/);
  const chunks: string[] = [];
  let currentChunk = "";
  let currentTokens = 0;

  for (const sentence of sentences) {
    const sentenceTokens = estimateTokens(sentence);

    if (currentTokens + sentenceTokens <= maxTokens) {
      currentChunk += sentence + " ";
      currentTokens += sentenceTokens;
    } else {
      if (currentChunk.trim()) {
        chunks.push(currentChunk.trim());
      }
      currentChunk = sentence + " ";
      currentTokens = sentenceTokens;
    }
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}

function accumulateSections(
  sections: string[],
  maxTokens: number
): string[] {
  const chunks: string[] = [];
  let currentChunk = "";
  let currentTokens = 0;

  for (const section of sections) {
    const sectionTokens = estimateTokens(section);
    if (currentTokens + sectionTokens <= maxTokens) {
      currentChunk += section + "\n\n";
      currentTokens += sectionTokens;
    } else {
      if (currentChunk.trim()) {
        chunks.push(currentChunk.trim());
      }
      if (sectionTokens > maxTokens) {
        chunks.push(...splitLargeSection(section, maxTokens));
        currentChunk = "";
        currentTokens = 0;
      } else {
        currentChunk = section + "\n\n";
        currentTokens = sectionTokens;
      }
    }
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}

function applyOverlap(chunks: string[], overlapTokens: number): string[] {
  if (chunks.length <= 1 || overlapTokens === 0) return chunks;

  const result = [chunks[0]];

  for (let i = 1; i < chunks.length; i++) {
    const prevChunk = chunks[i - 1];
    // Approximate overlap in characters
    const overlapChars = overlapTokens * 4;
    const overlapText = prevChunk.slice(-overlapChars);

    result.push(`...${overlapText}\n\n${chunks[i]}`);
  }

  return result;
}

function semanticSplitCode(code: string, extension: string): string[] {
  const patterns = CODE_SPLIT_PATTERNS[extension];
  if (!patterns || patterns.length === 0) return [code];

  // Combine patterns into a single regex
  const combined = new RegExp(
    patterns.map((p) => p.source).join("|"),
    "m"
  );

  const sections = code.split(combined);
  return sections.map((s) => s.trim()).filter((s) => s.length > 0);
}

function lineSplit(code: string, maxTokens: number): string[] {
  const lines = code.split("\n");
  const chunks: string[] = [];
  let currentLines: string[] = [];
  let currentTokens = 0;

  for (const line of lines) {
    const lineTokens = estimateTokens(line);

    if (currentTokens + lineTokens <= maxTokens) {
      currentLines.push(line);
      currentTokens += lineTokens;
    } else {
      if (currentLines.length > 0) {
        chunks.push(currentLines.join("\n"));
      }
      currentLines = [line];
      currentTokens = lineTokens;
    }
  }

  if (currentLines.length > 0) {
    chunks.push(currentLines.join("\n"));
  }

  return chunks;
}

function applyLineOverlap(chunks: string[], overlapLines: number): string[] {
  if (chunks.length <= 1 || overlapLines === 0) return chunks;

  const result = [chunks[0]];

  for (let i = 1; i < chunks.length; i++) {
    const prevLines = chunks[i - 1].split("\n");
    const overlap = prevLines.slice(-overlapLines);
    const overlapText = overlap.join("\n");

    result.push(`// ... continued from above\n${overlapText}\n${chunks[i]}`);
  }

  return result;
}
