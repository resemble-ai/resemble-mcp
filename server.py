"""
Resemble AI Documentation MCP Server

Provides intelligent access to Resemble AI documentation for AI coding assistants.
Designed for minimal tool calls - get comprehensive answers in a single request.
"""

import json
import asyncio
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
        "name": "Deepfake Detection",
        "description": "Detect AI-generated audio and watermarking",
        "pages": [
            "detect/overview",
            "detect/overview/create",
            "detect/overview/get",
            "detect/watermark/overview",
            "detect/watermark/apply",
            "detect/watermark/detect",
            "detect/identity/overview",
        ],
        "keywords": ["detect", "deepfake", "fake", "watermark", "identity", "verify", "authentic"]
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
    """Find the best matching topic for a query."""
    query_lower = query.lower()
    
    # Direct topic name match
    for topic_id, topic in TOPICS.items():
        if topic_id in query_lower or topic["name"].lower() in query_lower:
            return topic_id
    
    # Keyword match
    best_match = None
    best_score = 0
    
    for topic_id, topic in TOPICS.items():
        score = sum(1 for kw in topic["keywords"] if kw in query_lower)
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
    
    # Add API spec
    if API_SPEC_FILE.exists():
        resources.append(Resource(
            uri="resemble://docs/api-spec",
            name="API Specification",
            description="Complete Resemble AI V2 API specification",
            mimeType="text/markdown"
        ))
    
    return resources


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a documentation resource."""
    if uri.startswith("resemble://topic/"):
        topic_id = uri.replace("resemble://topic/", "")
        return get_topic_content(topic_id)
    
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
    return [
        Tool(
            name="resemble_docs_lookup",
            description="""Get comprehensive documentation about a Resemble AI topic. 
This is the PRIMARY tool - use it first for any question about Resemble AI.
Returns complete, aggregated documentation in a single call.

Available topics: voice-cloning, text-to-speech, speech-to-speech, speech-to-text, 
getting-started, voice-design, streaming, detect, agents, sdks, projects-clips, 
audio-tools, ssml

Examples:
- "voice-cloning" → Everything about cloning voices
- "text-to-speech" → TTS documentation and guides  
- "getting-started" → Auth, quickstart, basics""",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic to look up (e.g., 'voice-cloning', 'text-to-speech', 'streaming')",
                        "enum": list(TOPICS.keys())
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


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    
    if name == "resemble_docs_lookup":
        topic = arguments.get("topic", "")
        
        # Try to find topic even if not exact match
        if topic not in TOPICS:
            found_topic = find_topic(topic)
            if found_topic:
                topic = found_topic
            else:
                # Return available topics
                topics_list = "\n".join([f"- **{tid}**: {t['name']} - {t['description']}" for tid, t in TOPICS.items()])
                return [TextContent(
                    type="text",
                    text=f"Topic '{topic}' not found.\n\nAvailable topics:\n{topics_list}"
                )]
        
        content = get_topic_content(topic)
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
    
    raise ValueError(f"Unknown tool: {name}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
