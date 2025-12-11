# Resemble AI MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

Official MCP server exposing Resemble AI documentation as resources and tools. Connect to Cursor, Claude Code, or any MCP-compatible client to enable your coding assistant to access Resemble AI docs during development.

## Overview

This is the official Resemble AI MCP server. It implements the Model Context Protocol (stdio transport) to serve documentation from `docs/pages/` as queryable resources. The server aggregates docs by topic and provides full-text search across all MDX files.

**What it provides:**
- Topic-based documentation aggregation (13 topics: voice-cloning, text-to-speech, agents, etc.)
- Full-text search across all MDX documentation pages
- OpenAPI 3.0 spec with exact request/response schemas for code generation
- Direct page and endpoint access

Once connected, your coding assistant can query Resemble AI documentation programmatically. You can vibe code complete applications—your assistant has instant access to guides, tutorials, and exact API schemas for accurate code generation.

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/resemble-ai/resemble-mcp.git
cd resemble-mcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure MCP Client

**Cursor**: Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "resemble-ai-docs": {
      "command": "/path/to/resemble-mcp/venv/bin/python",
      "args": ["/path/to/resemble-mcp/server.py"]
    }
  }
}
```

**Claude Code / Claude Desktop**: Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent location for your OS:

```json
{
  "mcpServers": {
    "resemble-ai-docs": {
      "command": "/path/to/resemble-mcp/venv/bin/python",
      "args": ["/path/to/resemble-mcp/server.py"]
    }
  }
}
```

> **Note**: Use absolute paths. Replace `/path/to/resemble-mcp` with your actual path.

### 3. Restart Client

Restart your MCP client to load the server. Tools will be available after restart.

## Available Tools

### `resemble_docs_lookup`

Returns aggregated documentation for a topic. Accepts topic ID and returns all related pages concatenated.

**Parameters:**
- `topic` (string, required): One of: `voice-cloning`, `text-to-speech`, `speech-to-speech`, `speech-to-text`, `getting-started`, `voice-design`, `streaming`, `detect`, `agents`, `sdks`, `projects-clips`, `audio-tools`, `ssml`

**Returns:** Markdown content with all pages for the topic.

### `resemble_search`

Full-text search across all documentation pages. Returns matching pages with snippets.

**Parameters:**
- `query` (string, required): Search query
- `limit` (integer, optional): Max results (default: 5)

**Returns:** List of matching pages with titles, paths, and content snippets.

### `resemble_get_page`

Retrieves a specific documentation page by path.

**Parameters:**
- `path` (string, required): Page path relative to `docs/pages/` (e.g., `getting-started/quickstart`)

**Returns:** Full page content in Markdown.

### `resemble_list_topics`

Lists all available topic IDs with descriptions.

**Returns:** Markdown list of topics.

### `resemble_api_endpoint`

Get detailed OpenAPI specification for a specific API endpoint. Returns exact request/response schemas, parameters, and types.

**Parameters:**
- `method` (string, required): HTTP method (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`)
- `path` (string, required): API endpoint path (e.g., `/synthesize`, `/voices`)

**Returns:** Endpoint specification with schemas, parameters, and response formats.

### `resemble_api_search`

Search the OpenAPI spec for endpoints matching a query.

**Parameters:**
- `query` (string, required): Search query (e.g., `voice`, `streaming`, `agent`)

**Returns:** List of matching endpoints with methods, paths, and summaries.

## Usage

Once configured, your coding assistant (Cursor, Claude Code, etc.) can call these tools directly. Example use cases:

**Building a voice cloning app:**
```json
{
  "name": "resemble_docs_lookup",
  "arguments": { "topic": "voice-cloning" }
}
```

**Searching for streaming implementation:**
```json
{
  "name": "resemble_search",
  "arguments": { "query": "websocket streaming", "limit": 5 }
}
```

**Getting exact API schema for implementation:**
```json
{
  "name": "resemble_api_endpoint",
  "arguments": { "method": "POST", "path": "/synthesize" }
}
```

**Finding all voice-related API endpoints:**
```json
{
  "name": "resemble_api_search",
  "arguments": { "query": "voice" }
}
```

Your assistant uses these tools automatically when you ask it to build features. For example, "build me a TTS streaming service" triggers `resemble_docs_lookup` for the `text-to-speech` topic, and may use `resemble_api_endpoint` to get exact request schemas for accurate implementation.

## Project Structure

```
resemble-mcp/
├── server.py               # MCP server implementation
├── docs/
│   └── pages/              # MDX documentation files
│       ├── getting-started/    # Auth, quickstart, basics
│       ├── voice-generation/   # TTS, STT, S2S
│       ├── voice-creation/     # Voice cloning, recordings
│       ├── agents/             # AI agents
│       ├── detect/             # Deepfake detection
│       └── guides/             # Step-by-step tutorials
└── openapi/
    └── openapi.yml         # OpenAPI 3.0 specification
```

## Supported MCP Clients

Works with any client implementing the [Model Context Protocol](https://modelcontextprotocol.io):
- [Cursor](https://cursor.sh/) - AI code editor
- [Claude Code](https://claude.ai/code) - Anthropic's coding agent
- [Claude Desktop](https://claude.ai/download) - Anthropic's desktop app
- Any other MCP-compatible client

## Development

The server uses stdio transport (reads from stdin, writes to stdout) as per MCP specification.

```bash
# Run server directly (for testing/debugging)
python server.py
```

**Architecture:**
- Server implementation: `server.py`
- Documentation source: `docs/pages/` (MDX files)
- API specification: `openapi/openapi.yml` (OpenAPI 3.0)
- Topic definitions: Hardcoded in `TOPICS` dict
- Search: Full-text search with scoring across docs and OpenAPI endpoints

## Troubleshooting

**Server not loading:**
- Verify absolute paths in MCP config
- Ensure virtual environment is activated
- Check `mcp` package is installed: `pip show mcp`

**Tools not appearing:**
- Restart MCP client
- Check client logs for initialization errors
- Verify server starts without errors: `python server.py`

**Search returns no results:**
- Use `resemble_docs_lookup` with topic ID for guaranteed results
- Try broader search terms
- Check topic list: `resemble_list_topics`

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Resemble AI](https://resemble.ai)
- [Resemble AI Documentation](https://docs.resemble.ai)
- [MCP Protocol](https://modelcontextprotocol.io)
