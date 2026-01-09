/**
 * Stylus SDK Version Manager
 *
 * Single source of truth for Stylus SDK version configuration.
 * Both Python and TypeScript read from the same shared/stylus-versions.json.
 *
 * For Cloudflare Workers, the config is bundled at build time.
 */

// Import JSON directly (bundled at build time by Next.js/bundler)
import versionsConfig from "../../../../shared/stylus-versions.json";

// Type definitions
export interface VersionPatterns {
  attributes: string[];
  imports: string[];
  storage_macro: string;
  error_handling: string;
  cfg_attr: string;
  sender: string;
}

export interface VersionInfo {
  status: "main" | "supported" | "minimum" | "deprecated";
  alloy_primitives: string;
  alloy_sol_types: string;
  breaking_changes: string[];
  released: string;
}

export interface StylusVersionsConfig {
  main_version: string;
  minimum_version: string;
  deprecated_below: string;
  versions: Record<string, VersionInfo>;
  version_patterns: Record<string, VersionPatterns>;
  deprecation_warnings: {
    below_minimum: string;
    deprecated_attribute: string;
  };
}

// Type assertion for imported JSON
const config = versionsConfig as StylusVersionsConfig;

/**
 * Get the main (default) supported SDK version.
 */
export function getMainVersion(): string {
  return config.main_version;
}

/**
 * Get the minimum supported SDK version.
 */
export function getMinimumVersion(): string {
  return config.minimum_version;
}

/**
 * Check if a version is at or above minimum.
 */
export function isVersionSupported(version: string): boolean {
  return compareVersions(version, config.minimum_version) >= 0;
}

/**
 * Check if a version is below minimum (deprecated).
 */
export function isVersionDeprecated(version: string): boolean {
  return compareVersions(version, config.deprecated_below) < 0;
}

/**
 * Get code patterns for a specific SDK version.
 */
export function getVersionPatterns(version: string): VersionPatterns {
  const majorMinor = version.split(".").slice(0, 2).join(".");
  const patterns = config.version_patterns[majorMinor];

  if (patterns) {
    return patterns;
  }

  // Default to main version's patterns
  const mainMajorMinor = config.main_version.split(".").slice(0, 2).join(".");
  return config.version_patterns[mainMajorMinor] || config.version_patterns["0.9"];
}

/**
 * Get compatible alloy-primitives version for SDK version.
 */
export function getAlloyPrimitivesVersion(sdkVersion: string): string {
  const versionInfo = config.versions[sdkVersion];

  if (versionInfo) {
    return versionInfo.alloy_primitives;
  }

  // Default to main version's alloy-primitives
  return config.versions[config.main_version].alloy_primitives;
}

/**
 * Get compatible alloy-sol-types version for SDK version.
 */
export function getAlloySolTypesVersion(sdkVersion: string): string {
  const versionInfo = config.versions[sdkVersion];

  if (versionInfo) {
    return versionInfo.alloy_sol_types;
  }

  // Default to main version's alloy-sol-types
  return config.versions[config.main_version].alloy_sol_types;
}

/**
 * Compare two semantic versions.
 * @returns -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
 */
export function compareVersions(v1: string, v2: string): number {
  const parse = (v: string): number[] => {
    const cleaned = v.replace(/^[\^~>=<]+/, "");
    return cleaned.split(".").map((x) => parseInt(x, 10) || 0);
  };

  const p1 = parse(v1);
  const p2 = parse(v2);

  // Pad with zeros
  while (p1.length < 3) p1.push(0);
  while (p2.length < 3) p2.push(0);

  for (let i = 0; i < 3; i++) {
    if (p1[i] < p2[i]) return -1;
    if (p1[i] > p2[i]) return 1;
  }

  return 0;
}

/**
 * Detect stylus-sdk version from Cargo.toml content.
 *
 * Supports multiple formats:
 * - Simple: stylus-sdk = "0.9.0"
 * - Complex: stylus-sdk = { version = "0.9.0", features = [...] }
 */
export function detectVersionFromCargoToml(cargoContent: string): string | null {
  if (!cargoContent) return null;

  // Pattern 1: Simple format - stylus-sdk = "0.9.0"
  const simpleMatch = cargoContent.match(/stylus-sdk\s*=\s*"([^"]+)"/);
  if (simpleMatch) return simpleMatch[1];

  // Pattern 2: Complex format - stylus-sdk = { version = "0.9.0", ... }
  const complexMatch = cargoContent.match(
    /stylus-sdk\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"/s
  );
  if (complexMatch) return complexMatch[1];

  return null;
}

/**
 * Get deprecation warning message for a version.
 */
export function getDeprecationWarning(version: string): string | null {
  if (!isVersionDeprecated(version)) {
    return null;
  }

  const template = config.deprecation_warnings.below_minimum;
  return template
    .replace("{version}", version)
    .replace("{minimum}", config.minimum_version);
}

/**
 * Get version info for a specific version.
 */
export function getVersionInfo(version: string): VersionInfo | null {
  return config.versions[version] || null;
}

/**
 * Get list of all known SDK versions, sorted newest first.
 */
export function listSupportedVersions(): string[] {
  return Object.keys(config.versions).sort((a, b) => compareVersions(b, a));
}

/**
 * Get the full config object (for advanced use cases).
 */
export function getConfig(): StylusVersionsConfig {
  return config;
}

// Re-export config for direct access if needed
export { config as stylusVersionsConfig };
