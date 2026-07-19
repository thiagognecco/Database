"""AI service using Anthropic Claude API with improved prompts and error handling."""
import json
import re
import os
import logging
from dotenv import load_dotenv
from anthropic import Anthropic
from app.ai_cache import ai_cache, rate_limiter

load_dotenv()

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

    # Quick check for common keywords first (match whole words to avoid false positives)
    text = f"{titulo} {resumo} {url}".lower()
    import re
    for keyword, category in COMMON_CATEGORIES.items():
        # Use word boundary for short keywords to avoid matching inside other words
        pattern = r'\b' + re.escape(keyword) + r'\b' if len(keyword) <= 4 else re.escape(keyword)
        if re.search(pattern, text):
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
    prompt = f"""Analise este link e categorize-o. Responda em português do Brasil.

URL: {url}
Título: {titulo}
Resumo: {resumo}

Responda APENAS com este JSON (sem markdown, sem texto extra, em português):
{{
    "categoria": "Deve ser uma de: Tecnologia, Educação, Programação, Desenvolvimento, IA, Marketing, Negócios, Saúde, Jurídico, Finanças, Outro",
    "tema": "Tema principal em 2-3 palavras em português, sem abreviar (ex: 'Python', 'Machine Learning', 'Design de API')",
    "confiabilidade": "Alta, Média ou Baixa baseado na qualidade da URL"
}}

Dicas:
- Sites oficiais de linguagens de programação (python.org, nodejs.org, etc.) → categoria "Programação"
- Repositórios, bibliotecas e SDKs de código → categoria "Programação" ou "Desenvolvimento"
- Modelos de IA, LLMs, APIs de IA → categoria "IA"
- O tema deve ser específico e nunca abreviado. Não use "Ia" como tema.

Exemplos:
- https://github.com/openai/gpt-4 → {{"categoria": "IA", "tema": "GPT-4", "confiabilidade": "Alta"}}
- https://www.python.org → {{"categoria": "Programação", "tema": "Python", "confiabilidade": "Alta"}}
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


async def refine_metadata_pt(titulo: str, resumo: str, url: str) -> dict:
    """
    Translate and refine scraped title/summary into natural Portuguese (Brazil).
    """
    if not titulo and not resumo:
        return {"titulo": titulo, "resumo": resumo}

    wait_time = rate_limiter.wait_if_needed()
    if wait_time > 0:
        logger.warning(f"Rate limited, skipping metadata refinement")
        return {"titulo": titulo, "resumo": resumo}

    prompt = f"""Você recebeu um título e resumo extraídos de uma página web. Reescreva-os em português do Brasil de forma natural, clara e concisa.

URL: {url}
Título original: {titulo or "Não disponível"}
Resumo original: {resumo or "Não disponível"}

Responda APENAS com este JSON (sem markdown, sem texto extra):
{{
    "titulo": "Título em português (curto e claro)",
    "resumo": "Resumo de 1-2 frases em português"
}}

Se o texto original já estiver em português, apenas melhore a redação."""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        global API_CALL_COUNT
        API_CALL_COUNT += 1
        response_text = message.content[0].text.strip()
        result = _parse_json_response(response_text)

        if result and "titulo" in result and "resumo" in result:
            return {
                "titulo": result["titulo"] or titulo,
                "resumo": result["resumo"] or resumo,
            }

        return {"titulo": titulo, "resumo": resumo}

    except Exception as e:
        logger.error(f"AI metadata refinement error: {e}", exc_info=True)
        return {"titulo": titulo, "resumo": resumo}


async def extract_metadata_with_ai(url: str) -> dict:
    """
    Extract better metadata using Claude (fallback for failed web scraping).
    """
    prompt = f"""Preveja o conteúdo desta URL e sugira um título e resumo em português do Brasil.

URL: {url}

Responda APENAS com este JSON (sem markdown, sem texto extra, em português):
{{
    "titulo": "Título provável da página em português (curto, claro)",
    "resumo": "Resumo de 1-2 frases em português sobre o que este recurso contém"
}}

Foco em precisão. Exemplos:
- github.com/usuario/repo → {{"titulo": "Usuário/Repo", "resumo": "Repositório GitHub para..."}}
- medium.com/@author/artigo → {{"titulo": "Título do Artigo", "resumo": "Descrição breve baseada na estrutura da URL"}}"""

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

    prompt = f"""Gere um resumo conciso (1-2 frases) em português do Brasil descrevendo o que o usuário encontrará neste recurso.

Título: {titulo}
URL: {url}

Responda APENAS com o texto do resumo em português (sem JSON, sem markdown, sem aspas, apenas texto puro).
Mantenha claro, informativo, e preferencialmente com menos de 100 caracteres."""

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
