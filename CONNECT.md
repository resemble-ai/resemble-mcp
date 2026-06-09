# Connect to the Resemble AI MCP server

One hosted server, every MCP client. Deepfake detection, media intelligence, audio
source tracing, and watermarking.

- **Actions endpoint (recommended):** `https://mcp.resemble.ai/mcp` (Streamable HTTP)
- **Docs endpoint:** `https://mcp.resemble.ai/sse` (SSE)
- **Auth:** your own Resemble API key as a Bearer token. Get one at
  [app.resemble.ai](https://app.resemble.ai) → Account → API. The server stores nothing —
  your key is used in-memory for the call only.

Replace `YOUR_RESEMBLE_API_KEY` below.

## Claude Code
```bash
claude mcp add --transport http resemble https://mcp.resemble.ai/mcp \
  --header "Authorization: Bearer YOUR_RESEMBLE_API_KEY"
```

## Claude Desktop  (Settings → Developer → Edit Config)
```json
{
  "mcpServers": {
    "resemble": {
      "type": "http",
      "url": "https://mcp.resemble.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_RESEMBLE_API_KEY" }
    }
  }
}
```

## Cursor  (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "resemble": {
      "url": "https://mcp.resemble.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_RESEMBLE_API_KEY" }
    }
  }
}
```

## VS Code  (`.vscode/mcp.json`)
```json
{
  "servers": {
    "resemble": {
      "type": "http",
      "url": "https://mcp.resemble.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_RESEMBLE_API_KEY" }
    }
  }
}
```

## Codex CLI  (`~/.codex/config.toml`)
```toml
[mcp_servers.resemble]
url = "https://mcp.resemble.ai/mcp"
http_headers = { "Authorization" = "Bearer YOUR_RESEMBLE_API_KEY" }
```

## Gemini CLI  (`~/.gemini/settings.json`)
```json
{
  "mcpServers": {
    "resemble": {
      "httpUrl": "https://mcp.resemble.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_RESEMBLE_API_KEY" }
    }
  }
}
```

## Windsurf  (`~/.codeium/windsurf/mcp_config.json`)
```json
{
  "mcpServers": {
    "resemble": {
      "serverUrl": "https://mcp.resemble.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_RESEMBLE_API_KEY" }
    }
  }
}
```

## OpenClaw  (`~/.openclaw/openclaw.json`)
```json
{
  "mcpServers": {
    "resemble": {
      "url": "https://mcp.resemble.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_RESEMBLE_API_KEY" }
    }
  }
}
```

## Hermes Agent  (`/opt/data/config.yaml`, under `tools`/`mcpServers`)
```yaml
mcpServers:
  resemble:
    url: https://mcp.resemble.ai/mcp
    headers:
      Authorization: Bearer YOUR_RESEMBLE_API_KEY
```

## n8n / Zapier (MCP Client node)
- Server URL: `https://mcp.resemble.ai/mcp` · Transport: HTTP Streamable
- Header: `Authorization: Bearer YOUR_RESEMBLE_API_KEY`

## Tools exposed
`detect_deepfake` · `get_detection` · `analyze_media` · `ask_about_detection` ·
`detect_watermark` · `apply_watermark` · `trace_audio_source`
