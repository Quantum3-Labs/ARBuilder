/**
 * Vectorize client utilities for RAG operations.
 *
 * Uses Cloudflare Vectorize with BGE-Large embeddings (1024 dimensions).
 * Supports metadata filtering for efficient content type queries.
 */

export interface SearchResult {
  id: string;
  content: string;
  source: string;
  contentType: string;
  score: number;
}

export interface VectorizeMetadata {
  content: string;
  source: string;
  content_type: string;
  chunk_index?: number;
}

export interface SearchOptions {
  topK?: number;
  contentType?: "code" | "documentation" | "all";
}

/**
 * Search for similar documents in Vectorize.
 * Supports metadata filtering by source field for efficient queries.
 *
 * Source mapping:
 * - "documentation" → official docs (source: "documentation")
 * - "code" → github repos (source: "github")
 */
export async function searchVectorize(
  vectorize: VectorizeIndex,
  ai: Ai,
  query: string,
  options: SearchOptions = {}
): Promise<SearchResult[]> {
  const { topK = 10, contentType = "all" } = options;

  // Generate embedding for the query using Workers AI
  const embedding = await generateEmbedding(ai, query);

  // Build query options with optional metadata filter
  const queryOptions: VectorizeQueryOptions = {
    topK,
    returnMetadata: "all",
  };

  // Add metadata filter if content type is specified
  // Maps contentType to source field values in the data
  // Requires metadata index on source field
  if (contentType === "documentation") {
    queryOptions.filter = { source: "documentation" };
  } else if (contentType === "code") {
    queryOptions.filter = { source: "github" };
  }

  // Search Vectorize
  const results = await vectorize.query(embedding, queryOptions);

  // Map results to our format
  return results.matches.map((match) => {
    const metadata = match.metadata as Record<string, VectorizeVectorMetadata> | undefined;
    return {
      id: match.id,
      content: String(metadata?.content ?? ""),
      source: String(metadata?.source ?? "unknown"),
      contentType: String(metadata?.content_type ?? "documentation"),
      score: match.score,
    };
  });
}

/**
 * Generate embeddings using Workers AI BGE-M3 model (1024 dimensions).
 * BGE-M3 supports multi-lingual text and longer context.
 */
export async function generateEmbedding(
  ai: Ai,
  text: string
): Promise<number[]> {
  const response = await ai.run("@cf/baai/bge-m3", {
    text: [text],
  });

  // Handle different response formats
  if ("data" in response && Array.isArray(response.data)) {
    return response.data[0];
  }
  // Return the embedding array directly if available
  return [];
}

/**
 * Generate embeddings for multiple texts (batch).
 */
export async function generateEmbeddings(
  ai: Ai,
  texts: string[]
): Promise<number[][]> {
  const response = await ai.run("@cf/baai/bge-m3", {
    text: texts,
  });

  if ("data" in response && Array.isArray(response.data)) {
    return response.data;
  }
  return [];
}

/**
 * Rerank results using Workers AI BGE Reranker.
 */
export async function rerankResults(
  ai: Ai,
  query: string,
  results: SearchResult[],
  topK: number = 5
): Promise<SearchResult[]> {
  if (results.length === 0) return [];

  // Use BGE reranker to score query-document pairs
  const response = await ai.run("@cf/baai/bge-reranker-base", {
    query,
    contexts: results.map((r) => ({ text: r.content })),
    top_k: topK,
  });

  // Map back the scores to results
  const reranked: SearchResult[] = [];
  if (response.response) {
    for (const item of response.response) {
      if (item.id !== undefined && item.score !== undefined) {
        const result = results[item.id];
        if (result) {
          reranked.push({ ...result, score: item.score });
        }
      }
    }
  }

  return reranked;
}

/**
 * Insert vectors into Vectorize.
 */
export async function insertVectors(
  vectorize: VectorizeIndex,
  vectors: Array<{
    id: string;
    values: number[];
    metadata: Record<string, VectorizeVectorMetadata>;
  }>
): Promise<void> {
  await vectorize.upsert(vectors);
}
