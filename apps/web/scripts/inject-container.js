/**
 * Post-build script to inject ScraperContainer class into the generated worker.
 *
 * This is needed because OpenNext generates its own worker.js, and we need to
 * add our Cloudflare Container class to it for Durable Objects support.
 */

const fs = require('fs');
const path = require('path');

const workerPath = path.join(__dirname, '../.open-next/worker.js');

// Read the generated worker
let workerCode = fs.readFileSync(workerPath, 'utf-8');

// Check if already injected
if (workerCode.includes('ScraperContainer')) {
  console.log('ScraperContainer already injected, skipping...');
  process.exit(0);
}

// Container class to inject - external module resolved by wrangler
const containerCode = `
// ===== Injected ScraperContainer for Cloudflare Containers =====
//@ts-expect-error: Will be resolved by wrangler
import { Container } from "@cloudflare/containers";

/**
 * ScraperContainer - Durable Object-backed container for Python scraper.
 * Runs the Python Flask server that handles source re-ingestion.
 */
export class ScraperContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "5m";
}
// ===== End ScraperContainer injection =====

`;

// Inject at the beginning of the file, after any initial comments
const injectionPoint = workerCode.indexOf('import');
if (injectionPoint === -1) {
  // No imports found, inject at the beginning
  workerCode = containerCode + workerCode;
} else {
  // Inject before the first import
  workerCode = workerCode.slice(0, injectionPoint) + containerCode + workerCode.slice(injectionPoint);
}

// Write back
fs.writeFileSync(workerPath, workerCode);

console.log('✅ ScraperContainer injected into worker.js');
