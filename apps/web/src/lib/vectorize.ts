/**
 * Vectorize client utilities for RAG operations.
 *
 * Uses Cloudflare Vectorize with BGE-M3 embeddings (1024 dimensions).
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

/**
 * Search for similar documents in Vectorize.
 */
export async function searchVectorize(
  vectorize: VectorizeIndex,
  ai: Ai,
  query: string,
  topK: number = 10
): Promise<SearchResult[]> {
  // Generate embedding for the query using Workers AI
  const embedding = await generateEmbedding(ai, query);

  // Search Vectorize
  const results = await vectorize.query(embedding, {
    topK,
    returnMetadata: "all",
  });

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
 * Generate embeddings using Workers AI BGE-M3 model.
 */
export async function generateEmbedding(
  ai: Ai,
  text: string
): Promise<number[]> {
  const response = await ai.run("@cf/baai/bge-base-en-v1.5", {
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
  const response = await ai.run("@cf/baai/bge-base-en-v1.5", {
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
