/**
 * Get Bridging Context Tool (M2)
 *
 * Retrieves relevant documentation, code examples, and patterns
 * from the Arbitrum SDK knowledge base using Vectorize + reranking.
 */

import { searchVectorize, rerankResults, type SearchResult } from "../vectorize";

export interface GetBridgingContextInput {
  query: string;
  nResults?: number;
  contentType?: "code" | "documentation" | "all";
  rerank?: boolean;
}

export interface GetBridgingContextOutput {
  contexts: Array<{
    content: string;
    source: string;
    contentType: string;
    relevanceScore: number;
  }>;
  totalResults: number;
  query: string;
}

/**
 * Enhance query with bridging-specific keywords for better retrieval.
 */
function enhanceQuery(query: string): string {
  const qLower = query.toLowerCase();
  let enhanced = query;

  // Add SDK-specific keywords based on query content
  if (qLower.includes("bridge") || qLower.includes("deposit") || qLower.includes("withdraw")) {
    enhanced = `arbitrum sdk bridger ${enhanced}`;
  }
  if (qLower.includes("message") || qLower.includes("l1") || qLower.includes("l2")) {
    enhanced = `cross-chain messaging retryable ${enhanced}`;
  }
  if (qLower.includes("token") || qLower.includes("erc20")) {
    enhanced = `erc20 token bridger gateway ${enhanced}`;
  }
  if (qLower.includes("l3") || qLower.includes("orbit")) {
    enhanced = `orbit l3 chain bridger ${enhanced}`;
  }

  return enhanced;
}

export async function getBridgingContext(
  vectorize: VectorizeIndex,
  ai: Ai,
  input: GetBridgingContextInput
): Promise<GetBridgingContextOutput> {
  const {
    query,
    nResults = 5,
    contentType = "all",
    rerank = true,
  } = input;

  // Enhance query with bridging-specific terms
  const enhancedQuery = enhanceQuery(query);

  // Search Vectorize - get more results if reranking
  const searchResults = await searchVectorize(vectorize, ai, enhancedQuery, {
    topK: rerank ? nResults * 3 : nResults,
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
    query: enhancedQuery,
  };
}
