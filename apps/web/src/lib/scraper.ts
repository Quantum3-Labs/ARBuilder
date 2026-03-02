/**
 * Web documentation scraper for Worker-native ingestion.
 *
 * Uses native HTMLRewriter to strip unwanted elements, then regex-based
 * HTML-to-markdown conversion. Zero npm dependencies.
 */

export interface ScrapedDocument {
  title: string;
  content: string;
  contentHash: string;
  stylusVersion?: string;
  isVersionDeprecated?: boolean;
}

const MINIMUM_SDK_VERSION = "0.8.0";

/**
 * Scrape a documentation URL and return cleaned markdown content.
 */
export async function scrapeDocumentation(url: string): Promise<ScrapedDocument> {
  const response = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 (compatible; ArbBuilder/2.0; +https://arbuilder.app)",
    },
    redirect: "follow",
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} fetching ${url}`);
  }

  const html = await response.text();

  // Pass 1: Strip unwanted elements via HTMLRewriter
  const stripped = await stripUnwantedElements(html);

  // Extract title from original HTML
  const title = extractTitle(html);

  // Pass 2: Convert cleaned HTML to markdown via regex
  const markdown = htmlToMarkdown(stripped);

  // Clean up whitespace
  const content = markdown
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+\n/g, "\n")
    .trim();

  if (!content) {
    throw new Error(`No content extracted from ${url}`);
  }

  const contentHash = await sha256(content);
  const stylusVersion = extractStylusVersion(content);
  const isVersionDeprecated = stylusVersion
    ? compareVersions(stylusVersion, MINIMUM_SDK_VERSION) < 0
    : false;

  return { title, content, contentHash, stylusVersion, isVersionDeprecated };
}

/**
 * Strip script, style, nav, header, footer, aside, noscript elements
 * using Cloudflare's native HTMLRewriter.
 */
async function stripUnwantedElements(html: string): Promise<string> {
  const tagsToRemove = [
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "noscript",
    "svg",
    "iframe",
  ];

  let rewriter = new HTMLRewriter();
  for (const tag of tagsToRemove) {
    rewriter = rewriter.on(tag, {
      element(el) {
        el.remove();
      },
    });
  }

  const transformed = rewriter.transform(new Response(html));
  return await transformed.text();
}

/**
 * Extract <title> content from HTML.
 */
function extractTitle(html: string): string {
  const match = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (match) {
    return match[1].replace(/<[^>]+>/g, "").trim();
  }
  return "";
}

/**
 * Convert cleaned HTML to simplified markdown using regex.
 * Handles: headers, code blocks, lists, links, emphasis, paragraphs.
 */
export function htmlToMarkdown(html: string): string {
  let md = html;

  // Decode common HTML entities
  md = md.replace(/&amp;/g, "&");
  md = md.replace(/&lt;/g, "<");
  md = md.replace(/&gt;/g, ">");
  md = md.replace(/&quot;/g, '"');
  md = md.replace(/&#39;/g, "'");
  md = md.replace(/&nbsp;/g, " ");

  // Code blocks: <pre><code>...</code></pre>
  md = md.replace(
    /<pre[^>]*>\s*<code[^>]*(?:class="[^"]*language-(\w+)[^"]*"[^>]*)?>([\s\S]*?)<\/code>\s*<\/pre>/gi,
    (_, lang, code) => {
      const cleanCode = code.replace(/<[^>]+>/g, "").trim();
      return `\n\n\`\`\`${lang || ""}\n${cleanCode}\n\`\`\`\n\n`;
    }
  );

  // Standalone <pre> blocks without <code>
  md = md.replace(/<pre[^>]*>([\s\S]*?)<\/pre>/gi, (_, code) => {
    const cleanCode = code.replace(/<[^>]+>/g, "").trim();
    return `\n\n\`\`\`\n${cleanCode}\n\`\`\`\n\n`;
  });

  // Inline code: <code>...</code>
  md = md.replace(/<code[^>]*>([\s\S]*?)<\/code>/gi, (_, code) => {
    const cleanCode = code.replace(/<[^>]+>/g, "").trim();
    return `\`${cleanCode}\``;
  });

  // Headers: h1-h6
  for (let i = 1; i <= 6; i++) {
    const hashes = "#".repeat(i);
    md = md.replace(
      new RegExp(`<h${i}[^>]*>([\\s\\S]*?)<\\/h${i}>`, "gi"),
      (_, text) => `\n\n${hashes} ${text.replace(/<[^>]+>/g, "").trim()}\n\n`
    );
  }

  // Links: <a href="...">text</a>
  md = md.replace(
    /<a[^>]+href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/gi,
    (_, href, text) => {
      const cleanText = text.replace(/<[^>]+>/g, "").trim();
      if (!cleanText) return "";
      // Skip anchor-only links
      if (href.startsWith("#")) return cleanText;
      return `[${cleanText}](${href})`;
    }
  );

  // Bold: <strong>/<b>
  md = md.replace(/<(?:strong|b)[^>]*>([\s\S]*?)<\/(?:strong|b)>/gi, "**$1**");

  // Italic: <em>/<i>
  md = md.replace(/<(?:em|i)[^>]*>([\s\S]*?)<\/(?:em|i)>/gi, "*$1*");

  // Unordered lists
  md = md.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, text) => {
    return `\n- ${text.replace(/<[^>]+>/g, "").trim()}`;
  });
  md = md.replace(/<\/?[ou]l[^>]*>/gi, "\n");

  // Paragraphs and divs
  md = md.replace(/<\/p>/gi, "\n\n");
  md = md.replace(/<p[^>]*>/gi, "\n\n");
  md = md.replace(/<\/div>/gi, "\n");
  md = md.replace(/<div[^>]*>/gi, "\n");

  // Line breaks
  md = md.replace(/<br\s*\/?>/gi, "\n");

  // Horizontal rules
  md = md.replace(/<hr\s*\/?>/gi, "\n---\n");

  // Tables: basic handling - extract text
  md = md.replace(/<\/tr>/gi, "\n");
  md = md.replace(/<\/t[dh]>/gi, " | ");
  md = md.replace(/<t[dh][^>]*>/gi, "");
  md = md.replace(/<\/?(?:table|thead|tbody|tr)[^>]*>/gi, "\n");

  // Strip all remaining HTML tags
  md = md.replace(/<[^>]+>/g, "");

  // Clean up multiple blank lines
  md = md.replace(/\n{3,}/g, "\n\n");

  return md.trim();
}

/**
 * SHA-256 hash using crypto.subtle (native to Workers).
 */
export async function sha256(input: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Extract Stylus SDK version from documentation content.
 * Returns the highest detected version.
 */
export function extractStylusVersion(content: string): string | undefined {
  const patterns = [
    // Cargo.toml code blocks: stylus-sdk = "0.9.0"
    /stylus-sdk\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"/g,
    // Version mentions: stylus-sdk version 0.9.0
    /stylus-sdk\s+version\s+([0-9]+\.[0-9]+\.[0-9]+)/gi,
    // SDK v0.9.0 mentions
    /stylus[\s-]*sdk\s+v?([0-9]+\.[0-9]+\.[0-9]+)/gi,
  ];

  const found: string[] = [];
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      found.push(match[1]);
    }
  }

  if (found.length === 0) return undefined;

  // Return highest version
  found.sort((a, b) => compareVersions(b, a));
  return found[0];
}

/**
 * Compare two semantic versions.
 * Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
 */
export function compareVersions(v1: string, v2: string): number {
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
