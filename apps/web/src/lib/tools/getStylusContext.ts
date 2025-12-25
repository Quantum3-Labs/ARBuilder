/**
 * Get Stylus Context Tool
 *
 * Retrieves relevant documentation, code examples, and patterns
 * from the Stylus knowledge base using Vectorize + reranking.
 * Uses metadata filtering for efficient content type queries.
 */

import { searchVectorize, rerankResults, type SearchResult } from "../vectorize";

export interface GetStylusContextInput {
  query: string;
  nResults?: number;
  contentType?: "code" | "documentation" | "all";
  rerank?: boolean;
}

export interface GetStylusContextOutput {
  contexts: Array<{
    content: string;
    source: string;
    contentType: string;
    relevanceScore: number;
  }>;
  totalResults: number;
  query: string;
}

export async function getStylusContext(
  vectorize: VectorizeIndex,
  ai: Ai,
  input: GetStylusContextInput
): Promise<GetStylusContextOutput> {
  const {
    query,
    nResults = 5,
    contentType = "all",
    rerank = true,
  } = input;

  // Search Vectorize with metadata filtering (more efficient than post-filtering)
  // Get more results if reranking to have better candidates
  const searchResults = await searchVectorize(vectorize, ai, query, {
    topK: rerank ? nResults * 2 : nResults,
    contentType,
  });

  // Rerank if enabled
  let finalResults: SearchResult[];
  if (rerank && searchResults.length > 0) {
    finalResults = await rerankResults(ai, query, searchResults, nResults);
  } else {
    finalResults = searchResults.slice(0, nResults);
  }

  return {
    contexts: finalResults.map((r) => ({
      content: r.content,
      source: r.source,
      contentType: r.contentType,
      relevanceScore: r.score,
    })),
    totalResults: finalResults.length,
    query,
  };
}
