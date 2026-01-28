"""
Resemble AI Documentation MCP Server

Provides intelligent access to Resemble AI documentation for AI coding assistants.
Designed for minimal tool calls - get comprehensive answers in a single request.

Supports two transport modes:
- stdio: For local MCP clients (default)
- sse: For remote HTTP access (Lovable, Replit, etc.)

Usage:
    python server.py          # stdio mode (default)
    python server.py --sse    # SSE mode on PORT (default 8000)
"""

import os
import sys
import json
import asyncio
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# Initialize the MCP server
app = Server("resemble-ai-docs")

# Paths
BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
PAGES_DIR = DOCS_DIR / "pages"
API_SPEC_FILE = DOCS_DIR / "api_spec.md"
OPENAPI_FILE = BASE_DIR / "openapi" / "openapi.yml"

# Cache for OpenAPI spec
_openapi_cache: Optional[Dict[str, Any]] = None


def load_openapi_spec() -> Optional[Dict[str, Any]]:
    """Load and cache the OpenAPI specification."""
    global _openapi_cache
    if _openapi_cache is not None:
        return _openapi_cache
    
    if not OPENAPI_FILE.exists():
        return None
    
    try:
        content = OPENAPI_FILE.read_text(encoding='utf-8')
        _openapi_cache = yaml.safe_load(content)
        return _openapi_cache
    except Exception:
        return None


def get_openapi_endpoint(method: str, path: str) -> Optional[str]:
    """Get OpenAPI specification for a specific endpoint."""
    spec = load_openapi_spec()
    if not spec or "paths" not in spec:
        return None
    
    # Normalize path (handle both /path and path formats)
    if not path.startswith("/"):
        path = "/" + path
    
    # Try exact match first
    path_data = spec["paths"].get(path)
    
    # Try partial match if exact fails
    if not path_data:
        for spec_path in spec["paths"]:
            if path in spec_path or spec_path.endswith(path):
                path_data = spec["paths"][spec_path]
                path = spec_path
                break
    
    if not path_data:
        return None
    
    method_lower = method.lower()
    if method_lower not in path_data:
        # Return all methods if specific method not found
        return format_endpoint_spec(path, path_data)
    
    return format_endpoint_spec(path, {method_lower: path_data[method_lower]})


def format_endpoint_spec(path: str, methods: Dict) -> str:
    """Format endpoint specification as readable markdown."""
    spec = load_openapi_spec()
    output = [f"# API Endpoint: {path}\n"]
    
    for method, data in methods.items():
        output.append(f"## {method.upper()}")
        output.append(f"**Summary**: {data.get('summary', 'N/A')}")
        output.append(f"**Description**: {data.get('description', 'N/A')}")
        
        if data.get('tags'):
            output.append(f"**Tags**: {', '.join(data['tags'])}")
        
        # Parameters
        if data.get('parameters'):
            output.append("\n### Parameters")
            for param in data['parameters']:
                required = " (required)" if param.get('required') else ""
                schema = param.get('schema', {})
                param_type = schema.get('type', 'any')
                output.append(f"- `{param['name']}`{required}: {param_type} - {param.get('description', 'N/A')}")
        
        # Request body
        if data.get('requestBody'):
            output.append("\n### Request Body")
            content = data['requestBody'].get('content', {})
            for content_type, schema_data in content.items():
                output.append(f"**Content-Type**: {content_type}")
                if 'schema' in schema_data:
                    output.append("```json")
                    output.append(json.dumps(resolve_schema(schema_data['schema'], spec), indent=2))
                    output.append("```")
        
        # Responses
        if data.get('responses'):
            output.append("\n### Responses")
            for status, response in data['responses'].items():
                output.append(f"\n**{status}**: {response.get('description', 'N/A')}")
                if 'content' in response:
                    for content_type, schema_data in response['content'].items():
                        if 'schema' in schema_data:
                            output.append("```json")
                            output.append(json.dumps(resolve_schema(schema_data['schema'], spec), indent=2))
                            output.append("```")
        
        output.append("")
    
    return "\n".join(output)


def resolve_schema(schema: Dict, spec: Dict, depth: int = 0) -> Dict:
    """Resolve $ref references in schema (with depth limit to prevent infinite recursion)."""
    if depth > 5:
        return {"type": "object", "description": "..."}
    
    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')
        resolved = spec
        for part in ref_path[1:]:  # Skip the '#'
            resolved = resolved.get(part, {})
        return resolve_schema(resolved, spec, depth + 1)
    
    if schema.get('type') == 'object' and 'properties' in schema:
        result = {"type": "object", "properties": {}}
        for prop, prop_schema in schema['properties'].items():
            result["properties"][prop] = resolve_schema(prop_schema, spec, depth + 1)
        return result
    
    if schema.get('type') == 'array' and 'items' in schema:
        return {"type": "array", "items": resolve_schema(schema['items'], spec, depth + 1)}
    
    # Return simplified schema
    simple = {}
    for key in ['type', 'format', 'enum', 'example', 'description', 'default']:
        if key in schema:
            simple[key] = schema[key]
    return simple if simple else schema


def search_openapi_endpoints(query: str) -> List[Dict[str, Any]]:
    """Search OpenAPI spec for endpoints matching query."""
    spec = load_openapi_spec()
    if not spec or "paths" not in spec:
        return []
    
    results = []
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    for path, methods in spec["paths"].items():
        for method, data in methods.items():
            if method.startswith('x-'):  # Skip extensions
                continue
            
            # Score based on matches
            score = 0
            text_to_search = f"{path} {data.get('summary', '')} {data.get('description', '')} {' '.join(data.get('tags', []))}".lower()
            
            if query_lower in text_to_search:
                score += 10
            
            for word in query_words:
                if len(word) > 2 and word in text_to_search:
                    score += 2
            
            if score > 0:
                results.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": data.get('summary', ''),
                    "tags": data.get('tags', []),
                    "score": score
                })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]

# =============================================================================
# TOPIC DEFINITIONS - Maps user questions to relevant documentation
# =============================================================================

TOPICS = {
    "voice-cloning": {
        "name": "Voice Cloning",
        "description": "How to clone voices using Resemble AI",
        "pages": [
            "voice-creation/voices/clone-overview",
            "voice-creation/voices/overview",
            "voice-creation/voices/create",
            "voice-creation/voices/build",
            "voice-creation/recordings/overview",
            "voice-creation/recordings/create",
            "guides/custom-voice-recordings/getting-started",
            "guides/custom-voice-dataset/getting-started",
        ],
        "keywords": ["clone", "cloning", "voice clone", "custom voice", "train", "training", "rapid", "professional", "dataset", "recordings"]
    },
    "text-to-speech": {
        "name": "Text-to-Speech (TTS)",
        "description": "Generate speech from text",
        "pages": [
            "voice-generation/text-to-speech/overview",
            "voice-generation/text-to-speech/synchronous",
            "voice-generation/text-to-speech/streaming-http",
            "voice-generation/text-to-speech/streaming-websocket",
            "guides/creating-clips/getting-started",
            "getting-started/ssml",
        ],
        "keywords": ["tts", "text to speech", "text-to-speech", "generate speech", "synthesize", "synthesis", "clip", "audio generation"]
    },
    "speech-to-speech": {
        "name": "Speech-to-Speech",
        "description": "Convert speech in one voice to another voice",
        "pages": [
            "voice-generation/speech-to-speech",
        ],
        "keywords": ["speech to speech", "s2s", "voice conversion", "convert voice"]
    },
    "speech-to-text": {
        "name": "Speech-to-Text (STT)",
        "description": "Transcribe audio to text",
        "pages": [
            "voice-generation/speech-to-text/overview",
            "voice-generation/speech-to-text/create",
            "voice-generation/speech-to-text/get",
            "voice-generation/speech-to-text/list",
            "voice-generation/speech-to-text/intelligence",
        ],
        "keywords": ["stt", "speech to text", "transcribe", "transcription", "transcript"]
    },
    "getting-started": {
        "name": "Getting Started",
        "description": "Quick start, authentication, and basics",
        "pages": [
            "getting-started/quickstart",
            "getting-started/authentication",
            "getting-started/rate-limits",
            "getting-started/errors",
            "getting-started/model-versions",
        ],
        "keywords": ["start", "begin", "setup", "auth", "authentication", "api key", "quickstart", "rate limit", "error"]
    },
    "voice-design": {
        "name": "Voice Design",
        "description": "Create voices from text descriptions (no audio needed)",
        "pages": [
            "voice-creation/voice-design/design-overview",
            "voice-creation/voice-design/generate",
            "voice-creation/voice-design/create-from-candidate",
            "guides/voice-design/getting-started",
            "guides/voice-design/how-to-create",
            "guides/voice-design/how-to-prompt",
        ],
        "keywords": ["voice design", "design voice", "generate voice", "create voice", "voice from description", "candidate"]
    },
    "streaming": {
        "name": "Streaming Audio",
        "description": "Real-time audio streaming via HTTP or WebSocket",
        "pages": [
            "voice-generation/text-to-speech/streaming-http",
            "voice-generation/text-to-speech/streaming-websocket",
            "guides/creating-clips/websocket-streaming",
            "guides/creating-clips/websocket-streaming/getting-started",
            "guides/creating-clips/websocket-streaming/receiving-audio",
            "guides/creating-clips/websocket-streaming/error-handling",
        ],
        "keywords": ["stream", "streaming", "websocket", "real-time", "realtime", "low latency"]
    },
    "detect": {
        "name": "Deepfake Detection & Watermarking",
        "description": "Detect AI-generated audio, apply/detect watermarks, and verify identity",
        "pages": [
            "detect/overview",
            "detect/overview/create",
            "detect/overview/get",
            "detect/watermark/overview",
            "detect/watermark/apply",
            "detect/watermark/detect",
            "detect/identity/overview",
        ],
        "keywords": ["detect", "deepfake", "fake", "watermark", "watermarking", "audio watermark", 
                     "identity", "verify", "authentic", "synthetic", "ai detection", "apply watermark",
                     "detect watermark"]
    },
    "agents": {
        "name": "AI Agents",
        "description": "Build conversational AI agents",
        "pages": [
            "agents/overview",
            "agents/create",
            "agents/dispatch",
            "agents/capabilities",
            "agents/tools/overview",
            "agents/knowledge-base/overview",
            "agents/webhooks/overview",
            "agents/phone-numbers/overview",
        ],
        "keywords": ["agent", "agents", "conversational", "phone", "call", "webhook", "knowledge base", "tool"]
    },
    "sdks": {
        "name": "SDKs & Libraries",
        "description": "Python and Node.js SDK documentation",
        "pages": [
            "libraries/index",
            "libraries/python",
            "libraries/node",
        ],
        "keywords": ["sdk", "library", "python", "node", "nodejs", "npm", "pip", "install"]
    },
    "projects-clips": {
        "name": "Projects & Clips",
        "description": "Manage projects and audio clips",
        "pages": [
            "platform-management/projects/overview",
            "platform-management/projects/create",
            "platform-management/projects/list",
            "platform-management/clips/overview",
            "platform-management/clips/list",
            "platform-management/clips/get",
        ],
        "keywords": ["project", "clip", "manage", "organize", "list"]
    },
    "audio-tools": {
        "name": "Audio Tools",
        "description": "Audio enhancement and editing",
        "pages": [
            "audio-tools/audio-enhancement/overview",
            "audio-tools/audio-enhancement/create",
            "audio-tools/audio-edit/overview",
            "audio-tools/audio-edit/create",
        ],
        "keywords": ["enhance", "enhancement", "edit", "audio edit", "improve", "clean"]
    },
    "ssml": {
        "name": "SSML Reference",
        "description": "Speech Synthesis Markup Language for fine control",
        "pages": [
            "getting-started/ssml",
        ],
        "keywords": ["ssml", "markup", "prosody", "emphasis", "break", "pause", "phoneme"]
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def read_mdx_file(file_path: Path) -> Dict[str, Any]:
    """Read and parse an MDX file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        frontmatter = {}
        body = content
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
                body = parts[2].strip()
        
        return {
            "title": frontmatter.get("title", file_path.stem),
            "slug": frontmatter.get("slug", ""),
            "content": body,
            "path": str(file_path.relative_to(PAGES_DIR)).replace('.mdx', '').replace('\\', '/')
        }
    except Exception as e:
        return {"error": str(e), "path": str(file_path)}


def get_page_content(path: str) -> Optional[str]:
    """Get content of a documentation page by path."""
    if path == "api-spec":
        if API_SPEC_FILE.exists():
            return API_SPEC_FILE.read_text(encoding='utf-8')
        return None
    
    file_path = PAGES_DIR / f"{path}.mdx"
    if file_path.exists():
        doc = read_mdx_file(file_path)
        return doc.get("content")
    return None


def find_topic(query: str) -> Optional[str]:
    """Find the best matching topic for a query using flexible matching."""
    query_lower = query.lower().strip()
    
    # 1. Exact topic ID match
    if query_lower in TOPICS:
        return query_lower
    
    # 2. Direct topic name match
    for topic_id, topic in TOPICS.items():
        if topic_id in query_lower or topic["name"].lower() in query_lower:
            return topic_id
    
    # 3. Keyword match (bidirectional - query in keyword OR keyword in query)
    best_match = None
    best_score = 0
    
    for topic_id, topic in TOPICS.items():
        score = 0
        for kw in topic["keywords"]:
            # Check both directions for flexible matching
            if kw in query_lower:
                score += 3  # Keyword found in query (strong match)
            elif query_lower in kw:
                score += 2  # Query is part of keyword (partial match)
            # Also check word overlap for multi-word queries
            query_words = set(query_lower.split())
            kw_words = set(kw.split())
            overlap = query_words & kw_words
            if overlap:
                score += len(overlap)
        
        if score > best_score:
            best_score = score
            best_match = topic_id
    
    return best_match if best_score > 0 else None


def search_all_docs(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search through all documentation."""
    results = []
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    for mdx_file in PAGES_DIR.rglob("*.mdx"):
        try:
            doc = read_mdx_file(mdx_file)
            content_lower = doc.get("content", "").lower()
            title_lower = doc.get("title", "").lower()
            
            # Score based on matches
            score = 0
            if query_lower in title_lower:
                score += 10
            if query_lower in content_lower:
                score += 5
            
            # Word-by-word matching
            for word in query_words:
                if len(word) > 2:
                    if word in title_lower:
                        score += 3
                    if word in content_lower:
                        score += 1
            
            if score > 0:
                # Extract snippet
                content = doc.get("content", "")
                idx = content_lower.find(query_lower)
                if idx == -1:
                    for word in query_words:
                        idx = content_lower.find(word)
                        if idx != -1:
                            break
                
                snippet = ""
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(content), idx + 150)
                    snippet = content[start:end].strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(content):
                        snippet = snippet + "..."
                
                results.append({
                    "title": doc.get("title"),
                    "path": doc.get("path"),
                    "snippet": snippet,
                    "score": score
                })
        except Exception:
            continue
    
    # Sort by score and limit
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def get_topic_content(topic_id: str) -> str:
    """Get comprehensive content for a topic."""
    if topic_id not in TOPICS:
        return f"Topic '{topic_id}' not found. Available topics: {', '.join(TOPICS.keys())}"
    
    topic = TOPICS[topic_id]
    sections = []
    sections.append(f"# {topic['name']}\n\n{topic['description']}\n")
    
    for page_path in topic["pages"]:
        content = get_page_content(page_path)
        if content:
            sections.append(f"\n---\n\n## {page_path}\n\n{content}")
    
    return "\n".join(sections)


# =============================================================================
# MCP RESOURCES
# =============================================================================

@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available documentation resources."""
    resources = []
    
    # Add topics as primary resources
    for topic_id, topic in TOPICS.items():
        resources.append(Resource(
            uri=f"resemble://topic/{topic_id}",
            name=topic["name"],
            description=topic["description"],
            mimeType="text/markdown"
        ))
    
    # Add API spec (markdown)
    if API_SPEC_FILE.exists():
        resources.append(Resource(
            uri="resemble://docs/api-spec",
            name="API Specification (Markdown)",
            description="Complete Resemble AI V2 API specification in Markdown",
            mimeType="text/markdown"
        ))
    
    # Add OpenAPI spec
    if OPENAPI_FILE.exists():
        resources.append(Resource(
            uri="resemble://openapi/spec",
            name="OpenAPI Specification",
            description="Full OpenAPI 3.0 spec with all endpoints, schemas, and parameters",
            mimeType="application/x-yaml"
        ))
    
    return resources


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a documentation resource."""
    if uri.startswith("resemble://topic/"):
        topic_id = uri.replace("resemble://topic/", "")
        return get_topic_content(topic_id)
    
    if uri == "resemble://openapi/spec":
        if OPENAPI_FILE.exists():
            return OPENAPI_FILE.read_text(encoding='utf-8')
        raise ValueError("OpenAPI spec not found")
    
    if uri.startswith("resemble://docs/"):
        path = uri.replace("resemble://docs/", "")
        content = get_page_content(path)
        if content:
            return content
        raise ValueError(f"Page not found: {path}")
    
    raise ValueError(f"Invalid URI: {uri}")


# =============================================================================
# MCP TOOLS - Designed for minimal calls
# =============================================================================

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    tools = [
        Tool(
            name="resemble_docs_lookup",
            description="""Get comprehensive documentation about a Resemble AI topic. 
This is the PRIMARY tool - use it first for any question about Resemble AI.
Returns complete, aggregated documentation in a single call.

Supports flexible matching - use topic IDs, names, or keywords:

Topics (use these IDs or related keywords):
- voice-cloning: clone, custom voice, train, recordings, dataset
- text-to-speech: tts, synthesize, generate speech, audio generation
- speech-to-speech: s2s, voice conversion
- speech-to-text: stt, transcribe, transcription
- getting-started: auth, api key, quickstart, rate limit
- voice-design: design voice, generate voice, candidate
- streaming: websocket, real-time, low latency
- detect: deepfake, watermark, identity, verify, authentic
- agents: conversational, phone, call, webhook, knowledge base
- sdks: python, node, npm, pip, library
- projects-clips: project, clip, manage
- audio-tools: enhance, edit, improve audio
- ssml: markup, prosody, emphasis, phoneme

Examples:
- "voice-cloning" → Everything about cloning voices
- "watermark" → Watermarking docs (matched via 'detect' topic)
- "tts" → Text-to-speech documentation
- "transcribe" → Speech-to-text documentation""",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic ID, name, or keyword (e.g., 'voice-cloning', 'watermark', 'tts', 'transcribe')"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="resemble_search",
            description="""Search across all Resemble AI documentation.
Use this when you need to find specific information not covered by topic lookup,
or when exploring what documentation exists.

Returns matching pages with snippets.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'webhook callback', 'rate limits', 'emotion parameter')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="resemble_get_page",
            description="""Get the full content of a specific documentation page.
Use this when you know the exact page path from a previous search.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Page path (e.g., 'getting-started/quickstart', 'voice-creation/voices/create')"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="resemble_list_topics",
            description="""List all available documentation topics with descriptions.
Use this to discover what topics are available.""",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]
    
    # Add OpenAPI tools if spec exists
    if OPENAPI_FILE.exists():
        tools.extend([
            Tool(
                name="resemble_api_endpoint",
                description="""Get detailed OpenAPI specification for a specific API endpoint.
Returns request/response schemas, parameters, and examples.
Use this when you need exact API details for implementation.

Examples:
- method: "POST", path: "/synthesize" → TTS synthesis endpoint
- method: "GET", path: "/voices" → List voices endpoint
- method: "POST", path: "/speech-to-text" → Transcription endpoint""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, PATCH, DELETE)",
                            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/synthesize', '/voices', '/projects')"
                        }
                    },
                    "required": ["method", "path"]
                }
            ),
            Tool(
                name="resemble_api_search",
                description="""Search the OpenAPI specification for endpoints matching a query.
Use this to find which API endpoints are available for a feature.

Examples:
- "voice" → All voice-related endpoints
- "streaming" → Streaming endpoints
- "agent" → Agent-related endpoints""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for API endpoints"
                        }
                    },
                    "required": ["query"]
                }
            ),
        ])
    
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    
    if name == "resemble_docs_lookup":
        topic = arguments.get("topic", "").strip()
        original_query = topic
        
        # Try to find topic using flexible matching
        if topic not in TOPICS:
            found_topic = find_topic(topic)
            if found_topic:
                topic = found_topic
            else:
                # Return available topics with keywords for discoverability
                topics_list = "\n".join([
                    f"- **{tid}**: {t['name']}\n  Keywords: {', '.join(t['keywords'][:5])}" 
                    for tid, t in TOPICS.items()
                ])
                return [TextContent(
                    type="text",
                    text=f"No topic found matching '{original_query}'.\n\n"
                         f"**Tip**: Try using one of these topic IDs or related keywords:\n\n{topics_list}\n\n"
                         f"You can also use `resemble_search` to search across all documentation."
                )]
        
        # Include matched topic info if it was fuzzy matched
        content = get_topic_content(topic)
        if original_query.lower() != topic:
            content = f"*Matched '{original_query}' → topic '{topic}'*\n\n" + content
        
        return [TextContent(type="text", text=content)]
    
    elif name == "resemble_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        results = search_all_docs(query, limit)
        
        if not results:
            # Try to suggest a topic
            suggested_topic = find_topic(query)
            if suggested_topic:
                return [TextContent(
                    type="text",
                    text=f"No exact matches found. Try using `resemble_docs_lookup` with topic: '{suggested_topic}'"
                )]
            return [TextContent(type="text", text="No results found.")]
        
        output = f"Found {len(results)} results:\n\n"
        for r in results:
            output += f"### {r['title']}\n"
            output += f"**Path**: `{r['path']}`\n"
            if r.get('snippet'):
                output += f">{r['snippet']}\n"
            output += "\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "resemble_get_page":
        path = arguments.get("path", "")
        content = get_page_content(path)
        
        if content:
            return [TextContent(type="text", text=content)]
        return [TextContent(type="text", text=f"Page not found: {path}")]
    
    elif name == "resemble_list_topics":
        output = "# Available Documentation Topics\n\n"
        for topic_id, topic in TOPICS.items():
            output += f"## {topic['name']}\n"
            output += f"**ID**: `{topic_id}`\n"
            output += f"{topic['description']}\n"
            output += f"**Keywords**: {', '.join(topic['keywords'][:5])}...\n\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "resemble_api_endpoint":
        method = arguments.get("method", "GET")
        path = arguments.get("path", "")
        
        result = get_openapi_endpoint(method, path)
        if result:
            return [TextContent(type="text", text=result)]
        return [TextContent(type="text", text=f"Endpoint not found: {method} {path}. Use `resemble_api_search` to find available endpoints.")]
    
    elif name == "resemble_api_search":
        query = arguments.get("query", "")
        results = search_openapi_endpoints(query)
        
        if not results:
            return [TextContent(type="text", text=f"No API endpoints found matching '{query}'.")]
        
        output = f"# API Endpoints matching '{query}'\n\n"
        for r in results:
            tags = f" [{', '.join(r['tags'])}]" if r['tags'] else ""
            output += f"- **{r['method']}** `{r['path']}`{tags}\n"
            if r['summary']:
                output += f"  {r['summary']}\n"
        
        output += "\n*Use `resemble_api_endpoint` with method and path to get full details.*"
        return [TextContent(type="text", text=output)]
    
    raise ValueError(f"Unknown tool: {name}")


# =============================================================================
# MAIN
# =============================================================================

async def run_stdio():
    """Run the MCP server in stdio mode."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def run_sse():
    """Run the MCP server in SSE mode for remote access."""
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse, Response
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from mcp.server.sse import SseServerTransport
    import uvicorn

    # Create SSE transport
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        """Handle SSE connection."""
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options()
            )
        return Response()

    async def health(request):
        """Health check endpoint for Render/deployment platforms."""
        return JSONResponse({"status": "healthy", "server": "resemble-ai-docs"})

    # Create Starlette app with CORS middleware
    starlette_app = Starlette(
        debug=False,
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/sse", handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["Mcp-Session-Id"],
            )
        ],
    )

    # Get port from environment (Render sets this)
    port = int(os.environ.get("PORT", 8000))

    print(f"Starting Resemble AI Docs MCP Server (SSE mode)")
    print(f"Health check: http://0.0.0.0:{port}/health")
    print(f"SSE endpoint: http://0.0.0.0:{port}/sse")
    print(f"Messages endpoint: http://0.0.0.0:{port}/messages/")

    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    if "--sse" in sys.argv or os.environ.get("MCP_TRANSPORT") == "sse":
        run_sse()
    else:
        asyncio.run(run_stdio())
