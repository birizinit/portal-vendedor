# Portal de Inteligência de Carteira · Lar Plásticos

Portal para o vendedor (e admin/coordenação) entender **100% do que acontece na carteira**:
prioriza quem precisa de atenção agora, calcula recência/frequência reais a partir do
histórico de pedidos do Ploomes, e mostra alertas proativos (reativação, cotação parada,
inativos). v1 é **read-only** no Ploomes.

## Arquitetura

```
Ploomes (CRM/Sankhya) --sync background--> Espelho local (SQLite) --> API (FastAPI) --> Front (React)
                                                  |
                                  Inteligência (score, alertas) roda sobre o espelho
```

- **backend/** — FastAPI + SQLAlchemy. Cliente Ploomes (rate-limit 120/min), sync da
  carteira, motor de score/alertas, auth (vendedor/admin).
- **frontend/** — React + Vite + TypeScript + Tailwind. Login + Cockpit ("Hoje").

## Como rodar (Windows)

Atalho: dê duplo clique em **`Iniciar Portal.bat`** (sobe backend + frontend e abre o navegador).

Manual:
```powershell
# backend
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
# frontend (outro terminal)
cd frontend
npm run dev
```
Acesse **http://localhost:5173**.

## Login inicial

- Admin: definido no `backend/.env` (`PORTAL_ADMIN_EMAIL` / `PORTAL_ADMIN_PASSWORD`).
  Padrão atual: `gabriel.hernandes@larplasticos.com.br` / `admin` — **troque em produção**.
- Admin escolhe o vendedor no topo e clica **↻ Sincronizar** para puxar a carteira.

## Status (fases)

- [x] Fase 1 — Fundação (Ploomes, espelho, sync, inteligência)
- [x] Fase 2 — Cockpit + Alertas (auth + UI)
- [x] Fase 3 — Carteira 360 + Ficha do cliente (insights, mensagens prontas, histórico)
- [x] Fase 4 — Inativos & Reativação (régua de risco, potencial de recuperação)
- [x] Fase 5 — Oportunidades / Cross-sell por ramo (campeões por ramo + sugestões)
- [x] Fase 6 — Admin (visão do todo, dinheiro na mesa, ranking de carteiras)

**v1 (read-only) completa.** Próximo marco sugerido: v2 com escrita no Ploomes
(lançar cotações/pedidos com preview/confirmação).

## Deploy (GitHub + Railway)

O projeto é empacotado para rodar **num serviço só**: o `Dockerfile` builda o
front (React/Vite) e o FastAPI serve a API **e** o front buildado.

### 1. GitHub
```bash
git remote add origin https://github.com/birizinit/portal-vendedor.git
git push -u origin main
```

### 2. Railway
1. **New Project → Deploy from GitHub repo** → escolha `portal-vendedor`.
   O Railway detecta o `Dockerfile` e o `railway.json` (healthcheck em `/api/health`).
2. Em **Variables**, configure (com base no `backend/.env.example`):
   - `PLOOMES_API_KEY` — sua chave do Ploomes
   - `SECRET_KEY` — chave aleatória longa
   - `PORTAL_ADMIN_EMAIL` / `PORTAL_ADMIN_PASSWORD` — **senha forte**
3. **Persistência do banco** (recomendado): adicione um **Volume** montado em
   `/app/backend/data` (mantém a carteira sincronizada e as contas entre deploys),
   ou aponte `DATABASE_URL` para um **Postgres** do Railway.
4. Deploy. A URL pública serve o portal inteiro (front + API).

> Tooltips: passe o mouse sobre qualquer número (KPIs, score, frequência,
> dinheiro na mesa…) para ver **como ele é calculado** — ver `frontend/src/lib/explain.ts`.

## Notas de segurança

- A chave do Ploomes no `.env` é temporária (revogar e usar chave própria).
- `.env` e o banco (`data/`) estão no `.gitignore`.
- `npm config set strict-ssl false` foi necessário pela inspeção de SSL da rede corporativa.
