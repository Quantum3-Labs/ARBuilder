/**
 * Get Stylus Context Tool
 *
 * Retrieves relevant documentation, code examples, and patterns
 * from the Stylus knowledge base using Vectorize + reranking.
 * Uses metadata filtering for efficient content type queries.
 *
 * Supports version-aware search:
 * - Boosts results matching target SDK version (1.2x)
 * - Penalizes deprecated version results (0.8x)
 */

import { searchVectorize, rerankResults, type SearchResult } from "../vectorize";
import { compareVersions } from "../stylusVersions";

// Version boost/penalty multipliers
const VERSION_MATCH_BOOST = 1.2;
const DEPRECATED_PENALTY = 0.8;

export interface GetStylusContextInput {
  query: string;
  nResults?: number;
  contentType?: "code" | "documentation" | "all";
  rerank?: boolean;
  /** Target stylus-sdk version for boosting matching results. */
  targetVersion?: string;
}

export interface GetStylusContextOutput {
  contexts: Array<{
    content: string;
    source: string;
    contentType: string;
    relevanceScore: number;
    /** Stylus SDK version of this content (if known). */
    stylusVersion?: string;
  }>;
  totalResults: number;
  query: string;
}

/**
 * Apply version-aware scoring adjustments.
 * Boosts matching versions, penalizes deprecated versions.
 */
function applyVersionScoring(
  results: SearchResult[],
  targetVersion?: string
): SearchResult[] {
  if (!targetVersion) {
    return results;
  }

  return results.map((result) => {
    let adjustedScore = result.score;

    if (result.stylusVersion) {
      // Extract major.minor for comparison
      const targetMajorMinor = targetVersion.split(".").slice(0, 2).join(".");
      const resultMajorMinor = result.stylusVersion.split(".").slice(0, 2).join(".");

      // Boost matching versions
      if (targetMajorMinor === resultMajorMinor) {
        adjustedScore *= VERSION_MATCH_BOOST;
      } else if (compareVersions(result.stylusVersion, targetVersion) > 0) {
        // Slightly boost newer versions (they may have forward-compatible patterns)
        adjustedScore *= 1.05;
      }
    }

    // Penalize deprecated versions
    if (result.isVersionDeprecated) {
      adjustedScore *= DEPRECATED_PENALTY;
    }

    return { ...result, score: adjustedScore };
  });
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
    targetVersion,
  } = input;

  // Search Vectorize with metadata filtering (more efficient than post-filtering)
  // Get more results if reranking or version-boosting to have better candidates
  const fetchMultiplier = rerank || targetVersion ? 2 : 1;
  const searchResults = await searchVectorize(vectorize, ai, query, {
    topK: nResults * fetchMultiplier,
    contentType,
  });

  // Apply version-aware scoring adjustments
  const scoredResults = applyVersionScoring(searchResults, targetVersion);

  // Rerank if enabled
  let finalResults: SearchResult[];
  if (rerank && scoredResults.length > 0) {
    finalResults = await rerankResults(ai, query, scoredResults, nResults);
  } else {
    // Sort by adjusted score and take top N
    finalResults = scoredResults
      .sort((a, b) => b.score - a.score)
      .slice(0, nResults);
  }

  return {
    contexts: finalResults.map((r) => ({
      content: r.content,
      source: r.source,
      contentType: r.contentType,
      relevanceScore: r.score,
      stylusVersion: r.stylusVersion,
    })),
    totalResults: finalResults.length,
    query,
  };
}
