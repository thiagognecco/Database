"""SQLAlchemy models for links database."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Config(Base):
    """Application configuration / settings."""
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    chave = Column(String(100), unique=True, nullable=False, index=True)
    valor = Column(Text, nullable=True)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Link(Base):
    """Link com metadados completos."""
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    titulo = Column(String(500), nullable=True)
    resumo = Column(Text, nullable=True)
    autor = Column(String(200), nullable=True)
    data = Column(DateTime, nullable=True)
    plataforma = Column(String(100), nullable=True, index=True)
    categoria = Column(String(100), nullable=True, index=True)
    tema = Column(String(200), nullable=True)
    confiabilidade = Column(String(50), default="Média")
    bot = Column(Boolean, default=False)
    favorito = Column(Boolean, default=False, index=True)
    tags = Column(Text, default="")  # JSON array of tags
    rating = Column(Integer, default=0)  # 0-5 stars
    lido = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_titulo_resumo", "titulo", "resumo"),
        Index("idx_categoria_plataforma", "categoria", "plataforma"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "titulo": self.titulo,
            "resumo": self.resumo,
            "autor": self.autor,
            "data": self.data.isoformat() if self.data else None,
            "plataforma": self.plataforma,
            "categoria": self.categoria,
            "tema": self.tema,
            "confiabilidade": self.confiabilidade,
            "bot": self.bot,
            "favorito": self.favorito,
            "tags": self.tags or "",
            "rating": self.rating,
            "lido": self.lido,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
