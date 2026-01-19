import base64
import re
from typing import Optional

import markdown
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.docx_generator import html_to_docx_bytes, markdown_to_docx_bytes
from open_webui.utils.models import get_all_models

router = APIRouter()

SYSTEM_PROMPT = (
    "You are a report-writing assistant. Write a clear, structured report in Markdown. "
    "Use headings, bullet lists, and tables when helpful. Avoid code fences unless the "
    "user explicitly asks for code. Output only Markdown."
)


class DocxGenerateForm(BaseModel):
    prompt: str
    model: str
    temperature: Optional[float] = 0.4
    max_tokens: Optional[int] = None


class DocxRenderForm(BaseModel):
    content: str
    html: Optional[str] = None
    file_name: Optional[str] = None


def _extract_title(markdown_text: str) -> Optional[str]:
    for line in markdown_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _sanitize_filename(value: str) -> str:
    value = value.strip()
    if not value:
        return "report"
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    value = value.strip("._-")
    if len(value) > 80:
        value = value[:80].rstrip("._-")
    return value or "report"


def _resolve_filename(content: str, prompt: str, file_name: Optional[str]) -> str:
    if file_name:
        base = _sanitize_filename(file_name)
    else:
        base = _sanitize_filename(_extract_title(content) or prompt)
    if not base.lower().endswith(".docx"):
        base = f"{base}.docx"
    return base


def _extract_content(response) -> str:
    if not response:
        return ""
    choices = response.get("choices") if isinstance(response, dict) else None
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return (message.get("content") or "").strip()


@router.post("/docx/generate")
async def generate_docx_report(
    request: Request,
    form_data: DocxGenerateForm,
    user=Depends(get_verified_user),
):
    prompt = (form_data.prompt or "").strip()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.EMPTY_CONTENT,
        )

    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    payload = {
        "model": form_data.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }

    if form_data.temperature is not None:
        payload["temperature"] = form_data.temperature
    if form_data.max_tokens:
        payload["max_tokens"] = form_data.max_tokens

    response = await generate_chat_completion(request, payload, user)

    if isinstance(response, Response):
        detail = ""
        if getattr(response, "body", None):
            detail = response.body.decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=response.status_code,
            detail=detail or ERROR_MESSAGES.DEFAULT(),
        )

    content = _extract_content(response)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.EMPTY_CONTENT,
        )

    html = markdown.markdown(content, extensions=["tables", "fenced_code"])
    if form_data.html:
        docx_bytes = html_to_docx_bytes(form_data.html, fallback_markdown=content)
    else:
        docx_bytes = markdown_to_docx_bytes(content)
    docx_base64 = base64.b64encode(docx_bytes).decode("ascii")

    file_name = _resolve_filename(content, prompt, None)

    return {
        "content": content,
        "html": html,
        "docx": docx_base64,
        "file_name": file_name,
    }


@router.post("/docx")
async def render_docx(
    form_data: DocxRenderForm,
    user=Depends(get_verified_user),
):
    content = (form_data.content or "").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.EMPTY_CONTENT,
        )

    docx_bytes = markdown_to_docx_bytes(content)
    file_name = _resolve_filename(content, content, form_data.file_name)

    headers = {"Content-Disposition": f'attachment; filename="{file_name}"'}

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )
