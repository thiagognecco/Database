"""AI service using Anthropic Claude API."""
import json
import os
from anthropic import Anthropic

client = Anthropic()

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
}


async def categorize_link(url: str, titulo: str = "", resumo: str = "") -> dict:
    """
    Use Claude to suggest category, theme, and confidence for a link.

    Returns: {
        "categoria": "Tecnologia",
        "tema": "Python",
        "confiabilidade": "Alta"
    }
    """

    # Quick check for common keywords
    text = f"{titulo} {resumo} {url}".lower()
    for keyword, category in COMMON_CATEGORIES.items():
        if keyword in text:
            return {
                "categoria": category,
                "tema": keyword.title(),
                "confiabilidade": "Alta"
            }

    # If no match, use Claude for smart categorization
    prompt = f"""Analyze this link and suggest category, theme, and reliability.

URL: {url}
Title: {titulo}
Summary: {resumo}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
    "categoria": "One of: Tecnologia, Educação, Programação, Desenvolvimento, IA, Marketing, Negócios, Outro",
    "tema": "Specific topic (2-3 words)",
    "confiabilidade": "Alta/Média/Baixa"
}}"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        response_text = message.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        result = json.loads(response_text)
        return result

    except Exception as e:
        import logging
        logging.warning(f"AI categorization failed: {e}, using defaults")
        return {
            "categoria": "Outro",
            "tema": "Geral",
            "confiabilidade": "Média"
        }


async def extract_metadata_with_ai(url: str) -> dict:
    """
    Extract better metadata using Claude (fallback for failed web scraping).
    """

    prompt = f"""Given this URL, predict the likely content type and suggest a title/description.

URL: {url}

Respond with JSON:
{{
    "titulo": "Likely page title",
    "resumo": "2-3 sentence summary of what this resource likely contains"
}}"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text.strip()

        # Remove markdown if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        return json.loads(response_text)

    except Exception as e:
        import logging
        logging.warning(f"AI metadata extraction failed: {e}")
        return {
            "titulo": url.split("/")[-1] or url.split("//")[-1],
            "resumo": "Link adicionado"
        }


async def generate_summary_with_ai(titulo: str, url: str) -> str:
    """
    Generate a better summary using Claude based on title and URL.
    """
    if not titulo or not url:
        return ""

    prompt = f"""Based on this title and URL, generate a concise 1-2 sentence summary that describes what the user will find.

Title: {titulo}
URL: {url}

Respond ONLY with the summary text (no JSON, no markdown, just plain text)."""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text.strip()

    except Exception as e:
        import logging
        logging.warning(f"AI summary generation failed: {e}")
        return ""
