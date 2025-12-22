/**
 * Get Stylus Context Tool
 *
 * Retrieves relevant documentation, code examples, and patterns
 * from the Stylus knowledge base using Vectorize + reranking.
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

  // Search Vectorize for relevant documents
  const searchResults = await searchVectorize(
    vectorize,
    ai,
    query,
    rerank ? nResults * 2 : nResults // Get more if reranking
  );

  // Filter by content type if specified
  let filteredResults: SearchResult[];
  if (contentType !== "all") {
    filteredResults = searchResults.filter(
      (r) => r.contentType === contentType
    );
    // Fall back to all results if filter returns too few
    if (filteredResults.length < 3) {
      filteredResults = searchResults;
    }
  } else {
    filteredResults = searchResults;
  }

  // Rerank if enabled
  let finalResults: SearchResult[];
  if (rerank && filteredResults.length > 0) {
    finalResults = await rerankResults(ai, query, filteredResults, nResults);
  } else {
    finalResults = filteredResults.slice(0, nResults);
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
