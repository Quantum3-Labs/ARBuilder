-- Add rate_limit_tier to api_keys for tier-based daily quotas.
-- Tiers: 'free' (default), 'pro', 'unlimited'.
-- Limits live in code (apps/web/src/lib/rateLimit.ts) so they can be tuned
-- without a migration; this column only carries the tier name.
ALTER TABLE api_keys ADD COLUMN rate_limit_tier TEXT NOT NULL DEFAULT 'free';
