"""Metadata extraction from URLs."""
from fastapi import APIRouter, HTTPException
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time
import asyncio
from datetime import datetime, timedelta

from app.schemas import URLExtract
from app.ai_service import refine_metadata_pt

router = APIRouter(prefix="/api/metadata", tags=["metadata"])

# Rate limiting: 1 request per second
_request_times = []
_rate_limit_lock = asyncio.Lock()

async def _check_rate_limit():
    """Enforce 1 request per second limit."""
    global _request_times
    async with _rate_limit_lock:
        now = time.time()
        _request_times = [t for t in _request_times if now - t < 1.0]

        if len(_request_times) >= 1:
            sleep_time = 1.0 - (now - _request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        _request_times.append(time.time())


async def extract_metadata(url: str) -> dict:
    """
    Extract title and description from URL using og tags, meta tags, or fallback to title/description.
    Returns dict with titulo, resumo, or empty strings if extraction fails/blocked.
    """
    try:
        # Enforce rate limiting (1 request per second)
        await _check_rate_limit()

        # Validate URL
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                url = "https://" + url
        except:
            pass

        # Fetch page with timeout (max 10 seconds)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )

        if response.status_code not in [200, 204]:
            # Site blocked or error
            return {"titulo": None, "resumo": None}

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title
        titulo = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            titulo = og_title.get("content")
        else:
            title_tag = soup.find("title")
            if title_tag:
                titulo = title_tag.string

        # Extract description
        resumo = None
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            resumo = og_desc.get("content")
        else:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                resumo = meta_desc.get("content")

        # Trim and clean
        if titulo:
            titulo = titulo.strip()[:500]
        if resumo:
            resumo = resumo.strip()[:1000]

        return {"titulo": titulo, "resumo": resumo}

    except httpx.TimeoutException:
        # Timeout — site is slow or blocking
        return {"titulo": None, "resumo": None}

    except httpx.HTTPError:
        # Network error or blocked
        return {"titulo": None, "resumo": None}

    except Exception:
        # Any other error
        return {"titulo": None, "resumo": None}


@router.post("/extract")
async def extract_from_url(request: URLExtract):
    """Extract metadata from a URL."""
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL não pode estar vazia")

    metadata = await extract_metadata(url)

    # Refine scraped metadata into natural Portuguese
    if metadata.get("titulo") or metadata.get("resumo"):
        refined = await refine_metadata_pt(
            metadata.get("titulo") or "",
            metadata.get("resumo") or "",
            url
        )
        metadata["titulo"] = refined.get("titulo") or metadata.get("titulo")
        metadata["resumo"] = refined.get("resumo") or metadata.get("resumo")

    return {
        "url": url,
        **metadata,
    }
