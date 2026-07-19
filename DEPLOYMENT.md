# 🚀 Deployment - Banco de Links

## Opção 1: Railway.app (⭐ RECOMENDADO - Mais fácil)

### Passo 1: Criar conta no Railway
1. Acesse https://railway.app
2. Clique em "Start Project"
3. Faça login com GitHub/Google

### Passo 2: Deploy
1. Clique em "New Project" → "Deploy from GitHub"
2. Conecte seu repositório GitHub com este projeto
3. Railway detectará automaticamente que é Python/FastAPI
4. Configure variáveis de ambiente:
   - `ANTHROPIC_API_KEY` = sua chave (copie de `.env`)
   - `BANCO_LINKS_PORT` = 8000

### Passo 3: Pronto! 🎉
Railway gera uma URL pública automática (ex: `https://projeto-production.up.railway.app`)

---

## Opção 2: Replit (Super fácil, sem GitHub)

### Passo 1: Criar Replit
1. Acesse https://replit.com
2. Clique em "+ Create Repl"
3. Escolha "Import from GitHub" e cole: `https://github.com/seu-usuario/links`
   - OU faça "Upload files" e envie este projeto em ZIP

### Passo 2: Configurar variáveis
1. Clique em "Secrets" (ícone de cadeado)
2. Adicione: `ANTHROPIC_API_KEY=sk-ant-...`

### Passo 3: Rodar
1. Clique em "Run" ou execute: `python -m app.main`
2. URL automática aparece em "Webview"

---

## Opção 3: Vercel + Backend separado

Para maior performance, pode separar:
- **Frontend (Vercel)**: próximo, rápido, grátis
- **Backend (Railway/Render)**: API FastAPI

Mas por enquanto, uma única app funciona bem.

---

## Checklist de Deploy

- [ ] API rodando sem erros
- [ ] Banco de dados (2105 links) carregando
- [ ] Filtros e buscas funcionando
- [ ] Domínio/URL pública gerada
- [ ] ANTHROPIC_API_KEY configurada

---

## Troubleshooting

**"Module not found"?**
- Certifique-se que `requirements.txt` está atualizado
- Railway/Replit fazem `pip install -r requirements.txt` automaticamente

**"Banco de dados não aparece"?**
- Banco é criado automaticamente em `dados/banco.db`
- Se estiver vazio, faça backup/restore do seu banco local

**Porta errada?**
- Use porta `8000` (Railway/Render padrão)
- Não use `8765` em produção

---

## Credenciais Seguras

⚠️ **NUNCA commite `.env` no GitHub!**

1. Já adicionamos `.env` ao `.gitignore`
2. Em production, configure via painel do Railway/Replit
3. Variáveis de ambiente > Secrets (não commit)

---

Pronto para ir ao vivo! 🚀
