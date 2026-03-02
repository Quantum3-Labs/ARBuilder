/**
 * Get Orbit Context Tool (M4)
 *
 * Retrieves relevant Orbit chain documentation, code examples, and patterns
 * from the knowledge base using Vectorize + reranking.
 */

import { searchVectorize, rerankResults, type SearchResult } from "../vectorize";

export interface GetOrbitContextInput {
  query: string;
  nResults?: number;
  contentType?: "code" | "documentation" | "all";
  rerank?: boolean;
}

export interface GetOrbitContextOutput {
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
 * Enhance query with Orbit-specific keywords for better retrieval.
 */
function enhanceQuery(query: string): string {
  const qLower = query.toLowerCase();
  let enhanced = query;

  // Core Orbit SDK keywords
  if (qLower.includes("deploy") || qLower.includes("create rollup") || qLower.includes("launch")) {
    enhanced = `orbit-sdk createRollup deploy chain rollup ${enhanced}`;
  }
  if (qLower.includes("config") || qLower.includes("chain id") || qLower.includes("parameter")) {
    enhanced = `prepareChainConfig orbit chain configuration ${enhanced}`;
  }
  if (qLower.includes("token bridge") || qLower.includes("bridge") || qLower.includes("gateway")) {
    enhanced = `createTokenBridge orbit token bridge gateway ${enhanced}`;
  }
  if (qLower.includes("validator") || qLower.includes("batch poster") || qLower.includes("sequencer")) {
    enhanced = `orbit validator batch poster sequencer getValidators ${enhanced}`;
  }
  if (qLower.includes("anytrust") || qLower.includes("dac") || qLower.includes("keyset")) {
    enhanced = `anytrust DAC keyset setValidKeyset data availability ${enhanced}`;
  }
  if (qLower.includes("gas token") || qLower.includes("native token") || qLower.includes("custom gas")) {
    enhanced = `orbit custom gas token nativeToken ERC20 fee ${enhanced}`;
  }
  if (qLower.includes("node") || qLower.includes("nitro")) {
    enhanced = `prepareNodeConfig nitro node orbit ${enhanced}`;
  }
  if (qLower.includes("governance") || qLower.includes("upgrade") || qLower.includes("executor")) {
    enhanced = `UpgradeExecutor governance orbit admin ${enhanced}`;
  }

  // Default Orbit context if no specific keywords matched
  if (enhanced === query) {
    enhanced = `arbitrum orbit chain l3 orbit-sdk ${enhanced}`;
  }

  return enhanced;
}

export async function getOrbitContext(
  vectorize: VectorizeIndex,
  ai: Ai,
  input: GetOrbitContextInput
): Promise<GetOrbitContextOutput> {
  const {
    query,
    nResults = 5,
    contentType = "all",
    rerank = true,
  } = input;

  // Enhance query with Orbit-specific terms
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
