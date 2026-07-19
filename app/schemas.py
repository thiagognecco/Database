"""Pydantic schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel


class LinkCreate(BaseModel):
    """Schema for creating a new link."""
    url: str
    titulo: Optional[str] = None
    resumo: Optional[str] = None
    autor: Optional[str] = None
    data: Optional[str] = None
    plataforma: Optional[str] = None
    categoria: Optional[str] = None
    tema: Optional[str] = None
    confiabilidade: str = "Média"
    bot: bool = False
    tags: Optional[str] = ""  # JSON array
    rating: int = 0
    lido: bool = False


class LinkUpdate(BaseModel):
    """Schema for updating a link."""
    titulo: Optional[str] = None
    resumo: Optional[str] = None
    autor: Optional[str] = None
    data: Optional[str] = None
    plataforma: Optional[str] = None
    categoria: Optional[str] = None
    tema: Optional[str] = None
    confiabilidade: Optional[str] = None
    tags: Optional[str] = None  # JSON array
    rating: Optional[int] = None
    lido: Optional[bool] = None


class URLExtract(BaseModel):
    """Schema for URL metadata extraction."""
    url: str
