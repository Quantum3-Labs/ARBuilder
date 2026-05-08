-- Per-key CORS allowlist for browser-originated requests.
-- NULL  = unrestricted (server-to-server use, default).
-- '[]'  = locked (no browser may use this key).
-- '["https://docs.example.com", ...]'  = browser may use this key only from these origins.
--
-- Server-to-server requests (no Origin header) ignore this column entirely.
ALTER TABLE api_keys ADD COLUMN allowed_origins TEXT;
