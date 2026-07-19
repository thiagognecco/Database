"""AI Chat endpoint with context from stored links."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel
import os
import anthropic

from app.database import get_db, Link

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str
    limit: int = 5

@router.post("/chat")
async def ai_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Chat with AI using link context."""

    if not request.message or len(request.message.strip()) < 2:
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    try:
        # Search for relevant links
        search_terms = request.message.lower().split()
        query = db.query(Link)

        # Build OR conditions for search
        conditions = []
        for term in search_terms:
            if len(term) > 2:
                term_pattern = f"%{term}%"
                conditions.append(
                    or_(
                        Link.titulo.ilike(term_pattern),
                        Link.resumo.ilike(term_pattern),
                        Link.categoria.ilike(term_pattern),
                        Link.tema.ilike(term_pattern),
                        Link.tags.ilike(term_pattern),
                        Link.plataforma.ilike(term_pattern),
                    )
                )

        if conditions:
            query = query.filter(or_(*conditions))

        relevant_links = query.limit(request.limit).all()

        # Prepare context for AI
        links_context = ""
        if relevant_links:
            links_context = "\n\nLinks relevantes encontrados no banco:\n"
            for link in relevant_links:
                links_context += f"\n- **{link.titulo or link.url}**\n"
                links_context += f"  Categoria: {link.categoria or 'N/A'}\n"
                if link.resumo:
                    links_context += f"  Resumo: {link.resumo[:200]}...\n"
                if link.tema:
                    links_context += f"  Tema: {link.tema}\n"
                links_context += f"  URL: {link.url}\n"
        else:
            links_context = "\n\nNenhum link específico encontrado relacionado ao assunto."

        # Create prompt for Claude
        system_prompt = """Você é um assistente especializado em gerenciamento de conhecimento e recursos educacionais.
Você tem acesso a um banco de links com artigos, tutoriais, vídeos e recursos sobre diversos temas.
Quando o usuário fizer uma pergunta, você deve:
1. Analisar a pergunta com atenção
2. Considerar os links relevantes fornecidos
3. Fornecer uma resposta útil e bem estruturada
4. Citar os links relevantes quando aplicável
5. Oferecer insights e sugestões práticas

Mantenha as respostas concisas mas completas (2-3 parágrafos)."""

        user_prompt = f"{request.message}{links_context}"

        # Call Claude API
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-opus-4-1",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        ai_response = message.content[0].text

        # Return response with links
        return {
            "response": ai_response,
            "links": [
                {
                    "id": link.id,
                    "titulo": link.titulo or link.url,
                    "categoria": link.categoria,
                    "plataforma": link.plataforma,
                    "url": link.url,
                    "resumo": link.resumo
                }
                for link in relevant_links
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na IA: {str(e)}")
