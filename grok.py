# server.py

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import base64
from mcp.server.fastmcp import FastMCP
from xai_sdk import Client
from xai_sdk.chat import user, system, image, file
from xai_sdk.tools import web_search as xai_web_search, x_search as xai_x_search, code_execution

XAI_API_KEY = os.getenv("XAI_API_KEY")
if not XAI_API_KEY:
    raise ValueError("環境変数 'XAI_API_KEY' が設定されていません。")

# model config
DEFAULT_CHAT_MODEL = "grok-4-1-fast-non-reasoning"
DEFAULT_SEARCH_MODEL = "grok-4-1-fast-reasoning"
DEFAULT_IMAGE_MODEL = "grok-imagine-image"
DEFAULT_VIDEO_MODEL = "grok-imagine-video"

# MCPserver init
mcp = FastMCP(name="Grok MCP Server")

xai_client = Client(api_key=XAI_API_KEY)

def encode_file_to_base64(file_path: str) -> str:
    """画像や動画ファイルをBase64文字列にエンコード"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def extract_usage(response) -> dict:
    """レスポンスからトークン使用量を抽出"""
    if not hasattr(response, 'usage') or not response.usage:
        return {}
    return {
        "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
        "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
        "reasoning_tokens": getattr(response.usage, 'reasoning_tokens', 0),
        "total_tokens": getattr(response.usage, 'total_tokens', 0),
    }

def build_params(**kwargs) -> dict:
    """Noneや空の値を除外してAPIリクエスト用の辞書を作成"""
    return {k: v for k, v in kwargs.items() if v}


@mcp.tool()
async def manage_files(
    action: str,
    file_path: Optional[str] = None,
    file_id: Optional[str] = None,
    limit: int = 100,
    max_bytes: int = 500000
):
    """
    ファイル操作
    """
    if action == "upload":
        if not file_path or not Path(file_path).exists():
            return {"error": f"File not found: {file_path}"}
        uploaded = xai_client.files.upload(file_path)
        return {"file_id": uploaded.id, "filename": uploaded.filename, "size": uploaded.size}
        
    elif action == "list":
        response = xai_client.files.list(limit=limit, order="desc", sort_by="created_at")
        return {"files": [{"file_id": f.id, "filename": f.filename, "size": f.size} for f in response.data]}
        
    elif action == "get_info":
        if not file_id: return {"error": "file_id is required"}
        f = xai_client.files.get(file_id)
        return {"file_id": f.id, "filename": f.filename, "size": f.size}
        
    elif action == "get_content":
        if not file_id: return {"error": "file_id is required"}
        content = xai_client.files.content(file_id)
        truncated = len(content) > max_bytes
        content_str = content[:max_bytes].decode("utf-8", errors="replace")
        return {"file_id": file_id, "content": content_str, "truncated": truncated}
        
    elif action == "delete":
        if not file_id: return {"error": "file_id is required"}
        res = xai_client.files.delete(file_id)
        return {"file_id": res.id, "deleted": res.deleted}
        
    return {"error": f"Unknown action: {action}"}

@mcp.tool()
async def grok_search(
    prompt: str,
    platform: str = "web",
    model: str = DEFAULT_CHAT_MODEL,
    allowed_targets: Optional[List[str]] = None,
    excluded_targets: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_inline_citations: bool = False
):
    """
    Web検索とX(Twitter)検索
    platform: "web" または "x" を指定
    allowed_targets: Webの場合はドメイン、Xの場合はハンドル名
    """
    if allowed_targets and excluded_targets:
        return {"error": "Cannot specify both allowed and excluded targets"}

    tools_list = []
    if platform == "web":
        params = build_params(allowed_domains=allowed_targets, excluded_domains=excluded_targets)
        tools_list.append(xai_web_search(**params))
    elif platform == "x":
        fd = datetime.strptime(from_date, "%d-%m-%Y") if from_date else None
        td = datetime.strptime(to_date, "%d-%m-%Y") if to_date else None
        params = build_params(allowed_x_handles=allowed_targets, excluded_x_handles=excluded_targets, from_date=fd, to_date=td)
        tools_list.append(xai_x_search(**params))
    else:
        return {"error": "platform must be 'web' or 'x'"}

    chat_params = {"model": model, "tools": tools_list}
    if include_inline_citations:
        chat_params["include"] = ["inline_citations"]

    chat = xai_client.chat.create(**chat_params)
    chat.append(user(prompt))
    response = chat.sample()

    result = {
        "content": response.content,
        "citations": list(response.citations) if response.citations else [],
        "usage": extract_usage(response)
    }

    if include_inline_citations and response.inline_citations:
        result["inline_citations"] = [
            {"id": c.id, "url": c.web_citation.url if c.HasField("web_citation") else c.x_citation.url}
            for c in response.inline_citations
        ]

    return result

@mcp.tool()
async def grok_chat(
    prompt: str,
    model: str = DEFAULT_CHAT_MODEL,
    system_prompt: Optional[str] = None,
    file_ids: Optional[List[str]] = None,
    image_paths: Optional[List[str]] = None,
    image_urls: Optional[List[str]] = None,
    response_id: Optional[str] = None,
    use_code_execution: bool = False
):
    """
    テキスト・画像・ファイルを使った汎用チャット。
    response_idを渡すと過去の会話を引き継げます。
    use_code_executionをTrueにするとコード実行が可能になります。
    """

    chat_params = {
    "model": model,
    "store_messages": bool(response_id)
    }
    if response_id:
        chat_params["previous_response_id"] = response_id
    if use_code_execution:
        chat_params["tools"] = [code_execution()]
        chat_params["include"] = ["code_execution_call_output"]

    chat = xai_client.chat.create(**chat_params)
    
    if system_prompt and not response_id:
        chat.append(system(system_prompt))

    # ユーザーからの入力を組み立てる
    content_items = []
    
    if file_ids:
        for fid in file_ids:
            content_items.append(file(fid))
            
    if image_paths:
        for path in image_paths:
            ext = Path(path).suffix.lower().replace('.', '')
            base64_img = encode_file_to_base64(path)
            content_items.append(image(image_url=f"data:image/{ext};base64,{base64_img}"))
            
    if image_urls:
        for url in image_urls:
            content_items.append(image(image_url=url))
            
    content_items.append(prompt)
    chat.append(user(*content_items))
    
    response = chat.sample()

    result = {
        "content": response.content,
        "response_id": response.id,
        "usage": extract_usage(response)
    }
    
    if use_code_execution and response.tool_outputs:
        result["code_outputs"] = [to.message.content for to in response.tool_outputs]

    return result

@mcp.tool()
async def grok_agent(
    prompt: str,
    model: str = DEFAULT_SEARCH_MODEL,
    file_ids: Optional[List[str]] = None,
    image_paths: Optional[List[str]] = None,
    image_urls: Optional[List[str]] = None,
    use_web_search: bool = False,
    use_x_search: bool = False,
    use_code_execution: bool = False,
    allowed_targets: Optional[List[str]] = None,
    excluded_targets: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    system_prompt: Optional[str] = None,
    include_inline_citations: bool = False,
    max_turns: Optional[int] = None
):
    """
    web検索・X検索・コード実行・ファイル・画像を自由に組み合わせて使える万能エージェント
    """
    if allowed_targets and excluded_targets:
        return {"error": "Cannot specify both allowed and excluded targets"}

    tools_list = []
    if use_web_search:
        params = build_params(allowed_domains=allowed_targets, excluded_domains=excluded_targets)
        tools_list.append(xai_web_search(**params))
    if use_x_search:
        fd = datetime.strptime(from_date, "%d-%m-%Y") if from_date else None
        td = datetime.strptime(to_date, "%d-%m-%Y") if to_date else None
        params = build_params(allowed_x_handles=allowed_targets, excluded_x_handles=excluded_targets, from_date=fd, to_date=td)
        tools_list.append(xai_x_search(**params))
    if use_code_execution:
        tools_list.append(code_execution())

    include_options = ["code_execution_call_output"]
    if include_inline_citations:
        include_options.append("inline_citations")

    chat_params = {"model": model, "include": include_options}
    if tools_list:
        chat_params["tools"] = tools_list
    if max_turns:
        chat_params["max_turns"] = max_turns

    chat = xai_client.chat.create(**chat_params)

    if system_prompt:
        chat.append(system(system_prompt))

    content_items = []
    if file_ids:
        for fid in file_ids:
            content_items.append(file(fid))
    if image_paths:
        for path in image_paths:
            ext = Path(path).suffix.lower().replace('.', '')
            base64_img = encode_file_to_base64(path)
            content_items.append(image(image_url=f"data:image/{ext};base64,{base64_img}"))
    if image_urls:
        for url in image_urls:
            content_items.append(image(image_url=url))
    content_items.append(prompt)
    chat.append(user(*content_items))

    response = chat.sample()

    result = {
        "content": response.content,
        "usage": extract_usage(response),
    }
    if response.citations:
        result["citations"] = list(response.citations)
    if response.tool_calls:
        result["tool_calls"] = [{"name": tc.function.name, "arguments": tc.function.arguments} for tc in response.tool_calls]
    if response.server_side_tool_usage:
        result["server_side_tool_usage"] = dict(response.server_side_tool_usage)
    if use_code_execution and response.tool_outputs:
        result["code_outputs"] = [to.message.content for to in response.tool_outputs]

    return result

@mcp.tool()
async def generate_image(
    prompt: str,
    model: str = DEFAULT_IMAGE_MODEL,
    n: int = 1,
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    aspect_ratio: Optional[str] = None
):
    """
    画像を生成します。image_pathまたはimage_urlを渡すとimg2imgになります。
    aspect_ratio例: "16:9", "1:1", "9:16"
    """
    params = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "image_format": "url"
    }

    if image_path:
        ext = Path(image_path).suffix.lower().replace('.', '')
        base64_img = encode_file_to_base64(image_path)
        params["image_url"] = f"data:image/{ext};base64,{base64_img}"
    elif image_url:
        params["image_url"] = image_url

    if aspect_ratio:
        params["aspect_ratio"] = aspect_ratio

    images = xai_client.image.sample_batch(**params)
    return {
        "urls": [img.url for img in images],
        "revised_prompts": [img.prompt for img in images]
    }

@mcp.tool()
async def generate_video(
    prompt: str,
    model: str = DEFAULT_VIDEO_MODEL,
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    video_path: Optional[str] = None,
    video_url: Optional[str] = None,
    duration: Optional[int] = None,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None
):
    """
    動画を生成します。
    image_path/image_urlを渡すと画像から動画生成（img2video）になります。
    video_path/video_urlを渡すと動画から動画生成（video2video）になります。
    """
    params = {
        "model": model,
        "prompt": prompt
    }

    if image_path:
        ext = Path(image_path).suffix.lower().replace('.', '')
        params["image_url"] = f"data:image/{ext};base64,{encode_file_to_base64(image_path)}"
    elif image_url:
        params["image_url"] = image_url

    if video_path:
        ext = Path(video_path).suffix.lower().replace('.', '')
        params["video_url"] = f"data:video/{ext};base64,{encode_file_to_base64(video_path)}"
    elif video_url:
        params["video_url"] = video_url

    if duration:
        params["duration"] = duration
    if aspect_ratio:
        params["aspect_ratio"] = aspect_ratio
    if resolution:
        params["resolution"] = resolution

    response = xai_client.video.generate(**params)
    return {
        "url": response.url,
        "duration": getattr(response, 'duration', None)
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")