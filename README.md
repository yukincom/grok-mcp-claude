# Grok-MCP-Claude

Grok MCP server optimized for Claude Desktop — clean, single-file implementation using xAI's Grok for real-time web/X search and image generation.

## Concept

**Claude thinks, Grok searches.**

Claude Desktop handles conversation, memory, and reasoning. Grok provides what Claude can't — real-time web search, X (Twitter) search, and image/video generation.

![sucsess](https://github.com/yukincom/grok-mcp-claude/blob/main/img-for-readme/2026-02-25%201.06.18.png)

## Features

| Tool | Description |
|---|---|
| `grok_search` | Real-time web and X (Twitter) search |
| `grok_chat` | Chat with vision, file, and code execution support |
| `grok_agent` | Multi-tool agent combining search, code execution, files, and images |
| `generate_image` | Image generation with img2img support |
| `generate_video` | Video generation with img2video and video2video support |
| `manage_files` | Upload, list, retrieve, and delete files on xAI |

## Requirements

- Python 3.10+
- [xAI API key](https://console.x.ai/)
- Claude Desktop

## Installation

```bash
git clone https://github.com/yourname/grok-mcp-claude.git
cd grok-mcp-claude
pip install -r requirements.txt
```

## Configuration

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "grok": {
      "command": "python",
      "args": ["/path/to/grok-mcp-claude/grok.py"],
      "env": {
        "XAI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Tool Reference

### `grok_search`
Real-time search via web or X (Twitter).

| Parameter | Default | Description |
|---|---|---|
| `prompt` | required | Search query |
| `platform` | `"web"` | `"web"` or `"x"` |
| `model` | `DEFAULT_SEARCH_MODEL` | Model to use |
| `allowed_targets` | `None` | Whitelist of domains (web) or handles (X) |
| `excluded_targets` | `None` | Blacklist of domains (web) or handles (X) |
| `from_date` | `None` | Start date `DD-MM-YYYY` (X only) |
| `to_date` | `None` | End date `DD-MM-YYYY` (X only) |
| `include_inline_citations` | `False` | Return inline citations |

---

### `grok_chat`
General-purpose chat with optional vision, file, and code execution.

| Parameter | Default | Description |
|---|---|---|
| `prompt` | required | User message |
| `model` | `DEFAULT_CHAT_MODEL` | Model to use |
| `system_prompt` | `None` | System prompt |
| `file_ids` | `None` | xAI file IDs to attach |
| `image_paths` | `None` | Local image paths |
| `image_urls` | `None` | Image URLs |
| `response_id` | `None` | Previous response ID for stateful chat |
| `use_code_execution` | `False` | Enable code execution |

---

### `grok_agent`
Multi-tool agent. Combine web search, X search, code execution, files, and images freely.

| Parameter | Default | Description |
|---|---|---|
| `prompt` | required | User message |
| `model` | `DEFAULT_SEARCH_MODEL` | Model to use |
| `use_web_search` | `False` | Enable web search |
| `use_x_search` | `False` | Enable X search |
| `use_code_execution` | `False` | Enable code execution |
| `allowed_targets` | `None` | Whitelist of domains or handles |
| `excluded_targets` | `None` | Blacklist of domains or handles |
| `file_ids` | `None` | xAI file IDs to attach |
| `image_paths` | `None` | Local image paths |
| `image_urls` | `None` | Image URLs |
| `system_prompt` | `None` | System prompt |
| `include_inline_citations` | `False` | Return inline citations |
| `max_turns` | `None` | Max search iterations |

---

### `generate_image`
Generate images. Pass `image_path` or `image_url` for img2img.

| Parameter | Default | Description |
|---|---|---|
| `prompt` | required | Generation prompt |
| `model` | `DEFAULT_IMAGE_MODEL` | Model to use |
| `n` | `1` | Number of images |
| `image_path` | `None` | Local image for img2img |
| `image_url` | `None` | Image URL for img2img |
| `aspect_ratio` | `None` | e.g. `"16:9"`, `"1:1"`, `"9:16"` |

---

### `generate_video`
Generate videos from text, image, or video.

| Parameter | Default | Description |
|---|---|---|
| `prompt` | required | Generation prompt |
| `model` | `DEFAULT_VIDEO_MODEL` | Model to use |
| `image_path` / `image_url` | `None` | Source image for img2video |
| `video_path` / `video_url` | `None` | Source video for video2video |
| `duration` | `None` | Duration in seconds |
| `aspect_ratio` | `None` | Aspect ratio |
| `resolution` | `None` | Resolution |

---

### `manage_files`
Manage files on xAI.

| Action | Required params | Description |
|---|---|---|
| `upload` | `file_path` | Upload a file |
| `list` | — | List uploaded files |
| `get_info` | `file_id` | Get file metadata |
| `get_content` | `file_id` | Get file content |
| `delete` | `file_id` | Delete a file |

## Models

```python
DEFAULT_CHAT_MODEL   = "grok-4-1-fast-non-reasoning"
DEFAULT_SEARCH_MODEL = "grok-4-1-fast-reasoning"
DEFAULT_IMAGE_MODEL  = "grok-imagine-image"
DEFAULT_VIDEO_MODEL  = "grok-imagine-video"
```

## License

MIT
