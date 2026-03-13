# TESTAMENTO — SisGOPA v6.0
> Documento de continuidade. Se você está lendo isso, é porque precisa dar continuidade ao sistema.
> Última atualização: 13/03/2026

---

## O que é o SisGOPA

Sistema de Gestão Operacional de Pessoal e Atividades do **GTE (Grupo de Transporte Especial)** da Força Aérea Brasileira. É uma aplicação web single-page (HTML + JS puro, sem framework) hospedada no GitHub Pages.

**Dono:** Major MACHADO (Mauro Martins Alves Machado)
**Desenvolvido por:** Ravi Lemos (assistente IA via OpenClaw)

---

## URLs e Acessos

| O quê | URL / ID |
|-------|----------|
| **Produção** | https://mauromamachado-creator.github.io/sisescala-tv/ |
| **Repositório** | https://github.com/mauromamachado-creator/sisescala-tv |
| **GitHub Token** | _(armazenado no git config local — não expor em texto)_ |
| **Git user** | `ravi@sisgopa.dev` / `Ravi Lemos` |

---

## Arquitetura

```
┌─────────────────────────────────────┐
│          index.html (~7000 linhas)  │  ← Tudo numa página só
│  HTML + CSS + JS inline             │
│  Hospedado: GitHub Pages            │
└─────────┬───────────────────────────┘
          │ fetch (CSV / JSON)
          ▼
┌─────────────────────────────────────┐
│      Google Sheets (dados)          │
│  - MP 2026 (pilotos, dados)         │
│  - Escala                           │
│  - Dashboard/Planejamento           │
│  - Diárias                          │
│  - Confirmação                      │
│  - Consulta (VC-1, VC-2)           │
│  - Presença (Registro, Usuarios,    │
│    Indisponibilidade)               │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│   Google Apps Script (backends)     │
│  - gas_diarias.js (PDF diárias)     │
│  - gas_resposta_consulta_v2.js      │
│  - gas_presenca.js (MNT)           │
└─────────────────────────────────────┘
```

---

## Planilhas Google (IDs)

| Planilha | ID | Uso |
|----------|-----|-----|
| **MP 2026** | `1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao` | Dados pessoais, pilotos, tripulantes, voos |
| **Dashboard** | `1EV81x0Np-zeHhznvzAGrPyck5YUHgW_eRb18uOGc7nQ` | Sobreaviso, diárias, missões |
| **Escala** | `1MxhMnlzZNdXUkFRs_XmBI8SI3xhL1TDLEiCZ7aJKE-g` | Escalas de voo |
| **Diárias** | `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE` | Solicitações de diárias |
| **Respostas Consulta** | `1-aqNKOJcLGjZRDIfyd4hrNeLVJrcI-i9rfTii_rt2cs` | Abas VC-1, VC-2 |
| **Confirmação** | `15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA` | Confirmação de escalas |
| **Presença** | `1E49Q1bPbhT2MlYjYXfpC5mbzuxTBAPzidY3DtZW2VAs` | Registro ponto, Usuarios, Indisponibilidade |
| **PIMO** | `1Tnw8l_YXD22WB8kvpzXl53lpq7D_BFQTBFM-GkqZ5ts` | Relatório graduados |
| **Drive OMs** | Folder `133phdQHMHUfrg0rHtp6oa4zFm41FE45V` | Ordens de Missão PDFs |

---

## Google Apps Script (GAS)

### gas_presenca.js (MNT)
- **URL da API:** `https://script.google.com/macros/s/AKfycbz4zJ1MuAy_33m-twcgsCBB9j-QGHdYTi7x99KY-DPVKvVJh3xJ4IbSpKVKa0Uzz5M2fA/exec`
- **Actions:** `register`, `login`, `clockIn`, `clockOut`, `status`, `history`, `chamada`, `gerencial`, `lancar_indisp`, `minhas_indisp`, `cancelar_indisp`
- **Planilha:** `1E49Q1bPbhT2MlYjYXfpC5mbzuxTBAPzidY3DtZW2VAs`
- **Abas:** Registro, Usuarios, Indisponibilidade
- **Senha:** SHA-256 com salt `_GTE_SALT_2026`
- **Arquivo fonte:** `gas_presenca.js` no repositório

### gas_diarias.js
- **URL:** `https://script.google.com/macros/s/AKfycbyUm_PXR8M9yU1jLhUQC60SYNF_WEUmsxsb3hMigElzBOwI2LYEGKVkXyC_A1g1bOf4/exec`
- **Actions:** `get_numero`, `salvar_numero`
- **Planilha:** `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE`

### gas_resposta_consulta_v2.js
- **ID:** `AKfycbyDdqWqCKLoCVwgajS3kr4o6q2MHx3UYxwe2o-28JbFCS__NhV2l2OqFlUT-cyRu-Vg`
- **Actions:** `get`, `update`, `archive`, `lock_vc1`, `lock_vc2`, `unlock_vc1`, `unlock_vc2`
- **Planilha:** `1-aqNKOJcLGjZRDIfyd4hrNeLVJrcI-i9rfTii_rt2cs`

---

## Telas do SisGOPA (screens)

| # | ID | Nome | Descrição |
|---|-----|------|-----------|
| 1 | screen1 | Dashboard | Visão geral, METAR, calendário |
| 2 | screen2 | TV | Modo tela cheia |
| 3 | screen3 | Busca | Busca de tripulantes |
| 4 | screen4 | Cartões | Cartões/habilitações |
| 5 | screen5 | METAR/TAF | Meteorologia |
| 6 | screen6 | Diárias | Solicitação de diárias |
| 7 | screen7 | BOT | Tela BOT |
| 8 | screen8 | Reportar | Reportar problemas |
| 14 | screen14 | S3 | Área restrita (DIÁRIO, CONSULTA, OM, ESCALA V2, CONFIRMAÇÃO, ACNT) |
| 16 | screen16 | MNT | Sistema de presença (REGISTRAR, CHAMADA, GERENCIAL) |

---

## MNT — Sistema de Presença (v6.0)

### Funcionalidades
- **REGISTRAR PRESENÇA**: login SARAM + senha → ENTRADA/SAÍDA com GPS (raio 1km)
- **CHAMADA**: pública, gráfico donut, tags de indisponibilidade
- **GERENCIAL**: restrito (MACHADO + THIAGO), horas por período, situação, exportar
- **INDISPONIBILIDADE**: cada militar lança a sua (cancelável)
- **BIOMETRIA**: WebAuthn, armazena credencial no localStorage

### Coordenadas base
- Lat/Lng: `-15.8676989, -47.9060863`
- Raio: 1km

### Tipos de indisponibilidade
Serviço, Missão de Manutenção, Férias, Dispensa Chefia, Dispensa Médica, Outros

### Acesso GERENCIAL
- SARMs autorizados (normalizados): `4004221` (MACHADO), `6085199` (THIAGO VASCONCELOS)
- Array no frontend: `GERENCIAL_ALLOWED`

### localStorage keys
- `sisgopa_bio` — credencial biométrica
- `sisgopa_presenca` — sessão ativa (sessionStorage)

---

## APIs externas

| API | Chave | URL |
|-----|-------|-----|
| **AISWEB (DECEA)** | key=`1745062840`, pass=`822f92be-1958-11f1-a4e0-0050569ac2e1` | `https://aisweb.decea.mil.br/api/` |
| **METAR** | (sem chave) | `https://aviationweather.gov/api/data/metar` |
| **REDEMET** | _aguardando chave_ | — |

---

## Bot Telegram — @SISGOP_BOT (Consulta S3)
- **Token:** `8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU`
- **Porta:** 8085
- **Secret:** `sisgopa-gte-2026`
- **Código:** `/home/node/.openclaw/workspace/sisescala/consulta_bot.py`
- **Tunnel:** Cloudflare (muda a cada reinício)

## Bot Telegram — @GTEplanejamento_BOT (Planejamento)
- **Código:** `/home/node/.openclaw/workspace/gte_bot/bot.py`
- **Fontes:** aviationweather.gov, AISWEB API, Univ. Wyoming

---

## Como deployar

### Frontend (index.html)
1. Editar `/home/node/.openclaw/workspace/sisescala/index.html`
2. Copiar para `/tmp/sisescala-tv/index.html`
3. `cd /tmp/sisescala-tv && git add -A && git commit -m "mensagem" && git push origin main`
4. GitHub Pages atualiza automaticamente em ~1min

### GAS (Apps Script)
1. Copiar conteúdo do arquivo `.js` do repo
2. Colar no Google Apps Script (substituir todo o código)
3. Salvar (Ctrl+S)
4. **Implantar → Gerenciar implantações → ✏️ → Nova versão → Implantar**
5. ⚠️ Sem "Nova versão", o código antigo continua rodando

---

## GIDs das abas (Google Sheets)
- `disp=2129805598`
- `lanc=489572946`
- `previsao=1534384160`
- `acnt=519681315`

## Constantes importantes no código
- `SHEET` — ID da MP 2026
- `PLAN_SHEET` — ID do Dashboard
- `ESCALA_SHEET` — ID da Escala
- `PIMO_SHEET_ID` — ID do PIMO
- `PRESENCA_API` — URL do GAS de presença
- `PRESENCA_BASE` — Coordenadas da base
- `PRESENCA_RAIO_KM` — Raio do geofence
- `GERENCIAL_ALLOWED` — SARMs com acesso ao gerencial
- `EXCLUIDOS` — Pilotos excluídos da disponibilidade (BEH, SOZ)

## Regras de negócio
- **BEH e SOZ** excluídos da disponibilidade
- **OMs duplicadas** → usar a mais recente
- **SARAM** aceito em qualquer formato (normalizado sem pontos/traços)
- **Horas** calculadas na saída, suporta cruzar meia-noite
- **Cada entrada/saída = nova linha** (sem sobrescrever)
- **Precisa fechar entrada aberta** antes de nova entrada
- **METAR/NOTAM** sempre consultados ao vivo (nunca cache)

## Tags Git (checkpoints)
- `v5.0-stable`, `v5.1-stable`, `v5.1-estavel-20260310`
- `v-consulta-estavel-20260310`
- `v6.0-stable` ← **atual**

---

## Grupo Telegram
- **Ordens de Missão — GTE**: chat `-1003866369114`

## Contato do dono
- **Mauro Machado** — Telegram @machadommam (ID: 673591486)
- **Telefone:** +55 21 99524-2702
- **SARAM:** 400.422-1

---

_Este documento deve ser atualizado a cada versão major._
_Criado por Ravi Lemos 🦀 — 13/03/2026_
