"""AI service using Anthropic Claude API with improved prompts and error handling."""
import json
import re
import os
import logging
from anthropic import Anthropic
from app.ai_cache import ai_cache, rate_limiter

client = Anthropic()
logger = logging.getLogger(__name__)

# Model configuration
MODEL = "claude-opus-4-8"  # Latest, most capable model

# Track API usage for monitoring
API_CALL_COUNT = 0
API_TOKENS_USED = 0

# Cache de categorias para evitar chamadas desnecessárias
COMMON_CATEGORIES = {
    "tecnologia": "Tecnologia",
    "educação": "Educação",
    "programação": "Programação",
    "desenvolvimento": "Desenvolvimento",
    "ia": "IA",
    "machine learning": "IA",
    "python": "Programação",
    "javascript": "Programação",
    "react": "Programação",
    "typescript": "Programação",
    "github": "Programação",
    "youtube": "Educação",
    "medium": "Educação",
}


def _parse_json_response(text: str) -> dict | None:
    """Robustly parse JSON from response, handling markdown blocks."""
    text = text.strip()

    # Remove markdown code blocks
    if text.startswith("```"):
        # Extract content between triple backticks
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    # Try to find JSON object if there's surrounding text
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}\nText: {text}")
        return None


async def categorize_link(url: str, titulo: str = "", resumo: str = "") -> dict:
    """
    Use Claude to suggest category, theme, and confidence for a link.
    Results are cached to avoid redundant API calls.

    Returns: {
        "categoria": "Tecnologia",
        "tema": "Python",
        "confiabilidade": "Alta"
    }
    """
    global API_CALL_COUNT

    # Quick check for common keywords first
    text = f"{titulo} {resumo} {url}".lower()
    for keyword, category in COMMON_CATEGORIES.items():
        if keyword in text:
            return {
                "categoria": category,
                "tema": keyword.title(),
                "confiabilidade": "Alta"
            }

    # Check cache before calling API
    cache_key = f"categorize:{url}"
    cached_result = ai_cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for {url}")
        return cached_result

    # Check rate limit
    wait_time = rate_limiter.wait_if_needed()
    if wait_time > 0:
        logger.warning(f"Rate limited, would need to wait {wait_time:.1f}s")
        # Return default instead of blocking
        return {
            "categoria": "Outro",
            "tema": "Geral",
            "confiabilidade": "Média"
        }

    # Use Claude for smart categorization with improved prompt
    prompt = f"""Analyze this link and categorize it.

URL: {url}
Title: {titulo}
Summary: {resumo}

Respond ONLY with this JSON (no markdown, no extra text):
{{
    "categoria": "Must be one of: Tecnologia, Educação, Programação, Desenvolvimento, IA, Marketing, Negócios, Saúde, Jurídico, Finanças, Outro",
    "tema": "Main topic in 2-3 words (e.g., 'Python Web Dev', 'Machine Learning', 'API Design')",
    "confiabilidade": "Alta, Média, or Baixa based on URL quality"
}}

Examples:
- https://github.com/openai/gpt-4 → {{"categoria": "IA", "tema": "GPT-4", "confiabilidade": "Alta"}}
- https://medium.com/python-tips → {{"categoria": "Programação", "tema": "Python", "confiabilidade": "Média"}}"""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        API_CALL_COUNT += 1
        response_text = message.content[0].text.strip()
        result = _parse_json_response(response_text)

        if result:
            # Cache the result
            ai_cache.set(cache_key, result)
            logger.info(f"Categorized and cached {url}")
            return result

        # Fallback if parsing failed
        logger.warning(f"Failed to categorize {url}, using defaults")
        return {
            "categoria": "Outro",
            "tema": "Geral",
            "confiabilidade": "Média"
        }

    except Exception as e:
        logger.error(f"AI categorization error: {e}", exc_info=True)
        return {
            "categoria": "Outro",
            "tema": "Geral",
            "confiabilidade": "Média"
        }


async def extract_metadata_with_ai(url: str) -> dict:
    """
    Extract better metadata using Claude (fallback for failed web scraping).
    """
    prompt = f"""Predict the content of this URL and suggest a title and summary.

URL: {url}

Respond ONLY with this JSON (no markdown, no extra text):
{{
    "titulo": "Likely accurate page title (short, clear)",
    "resumo": "1-2 sentence summary of what this resource contains"
}}

Focus on accuracy. Examples:
- github.com/user/repo → {{"titulo": "User/Repo", "resumo": "GitHub repository for..."}}
- medium.com/@author/article → {{"titulo": "Article Title", "resumo": "Brief description based on URL structure"}}"""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text.strip()
        result = _parse_json_response(response_text)

        if result and "titulo" in result and "resumo" in result:
            return result

        # Fallback
        logger.warning(f"Failed to extract metadata for {url}")
        return {
            "titulo": url.split("/")[-1] or url.split("//")[-1],
            "resumo": "Link adicionado"
        }

    except Exception as e:
        logger.error(f"AI metadata extraction error: {e}", exc_info=True)
        return {
            "titulo": url.split("/")[-1] or url.split("//")[-1],
            "resumo": "Link adicionado"
        }


async def generate_summary_with_ai(titulo: str, url: str) -> str:
    """
    Generate a better summary using Claude based on title and URL.
    Results are cached to avoid redundant API calls.
    """
    global API_CALL_COUNT

    if not titulo or not url:
        return ""

    # Check cache before calling API
    cache_key = f"summary:{url}:{titulo}"
    cached_result = ai_cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for summary of {url}")
        return cached_result.get("summary", "")

    # Check rate limit
    wait_time = rate_limiter.wait_if_needed()
    if wait_time > 0:
        logger.warning(f"Rate limited, skipping summary generation")
        return ""

    prompt = f"""Generate a concise summary (1-2 sentences) describing what the user will find at this resource.

Title: {titulo}
URL: {url}

Respond ONLY with the summary text (no JSON, no markdown, no quotes, just plain text).
Keep it clear, informative, and under 100 characters if possible."""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        API_CALL_COUNT += 1
        summary = message.content[0].text.strip()

        if summary:
            # Cache the result
            ai_cache.set(cache_key, {"summary": summary})

        return summary if summary else ""

    except Exception as e:
        logger.error(f"AI summary generation error: {e}", exc_info=True)
        return ""


def get_ai_stats() -> dict:
    """Get AI service usage statistics."""
    return {
        "api_calls": API_CALL_COUNT,
        "cache_stats": ai_cache.stats(),
        "rate_limit": rate_limiter.get_status()
    }
