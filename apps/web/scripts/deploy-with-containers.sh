#!/bin/bash
# Deploy script that ensures container bindings are included
# This works around wrangler's OpenNext framework detection which ignores container config

set -e

# Cleanup function to restore files on exit (success or failure)
cleanup() {
  if [ -f "_package.json.bak" ]; then
    mv _package.json.bak package.json
    echo "Restored package.json"
  fi
  if [ -f "_open-next.config.ts.bak" ]; then
    mv _open-next.config.ts.bak open-next.config.ts
    echo "Restored open-next.config.ts"
  fi
}

# Register cleanup function
trap cleanup EXIT

echo "=== Building with OpenNext ==="
npx opennextjs-cloudflare build

echo ""
echo "=== Injecting ScraperContainer class ==="
node scripts/inject-container.js

echo ""
echo "=== Deploying with containers ==="
# Temporarily rename framework detection files
# This allows wrangler to use our wrangler.prod.jsonc config directly

if [ -f "open-next.config.ts" ]; then
  mv open-next.config.ts _open-next.config.ts.bak
fi

# Rename package.json to prevent framework detection
# wrangler detects "next" in dependencies
mv package.json _package.json.bak

# Create minimal package.json that doesn't trigger framework detection
cat > package.json << 'PKGEOF'
{
  "name": "arbbuilder-worker",
  "private": true,
  "type": "module"
}
PKGEOF

# Deploy with explicit config and framework detection disabled
WRANGLER_DISABLE_FRAMEWORK_DETECTION=true npx wrangler deploy -c wrangler.prod.jsonc

echo ""
echo "=== Deployment complete ==="
echo "Container binding SCRAPER_CONTAINER should now be available"
