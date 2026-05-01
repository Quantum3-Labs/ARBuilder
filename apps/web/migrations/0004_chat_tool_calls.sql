-- Add tool_calls column to usage_logs to track which MCP tools a chat turn invoked.
-- NULL for non-chat tool invocations (existing rows and direct /api/v1/tools/* calls).
-- Stored as JSON array, e.g. '["get_stylus_context","generate_stylus_code"]'.
ALTER TABLE usage_logs ADD COLUMN tool_calls TEXT;
