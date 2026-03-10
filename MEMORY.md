# MEMORY.md - Long-term Memory

## Mauro Machado
- Brasileiro, casual, direto
- Trabalha com aviação (possivelmente militar/FAB - GTE = Grupo de Transporte Especial?)
- Timezone: EST (EUA)
- Telegram: @machadommam (ID: 673591486)
- Telefone: +55 21 99524-2702
- Prefere português BR, tom descontraído
- Não gosta de jargão técnico — falar direto, sem termos como "deploy", "commit", "regex" etc.

## Regras CRÍTICAS do sistema
- **NUNCA cachear dados** — METAR, NOTAM, escalas, voos, tudo deve ser consultado AO VIVO sempre
- Bot Telegram e SisGOPA DEVEM ser idênticos (mesmas fontes, mesmos dados)
- **AISWEB é fonte primária pra TODAS as funcionalidades** dos bots (NOTAM, aeródromo, pistas, horários, combustível, etc.) — não só NOTAMs. Outras fontes são fallback.
- Correção de bugs automática; mudança de parâmetro precisa de aprovação do Mauro
- OMs duplicadas no Drive → sempre usar a mais recente

## Meu nome
- **Ravi Lemos** 🦀
- Avatar: avatars/ravi.png

## Pasta Ordens de Missão (Drive)
- Folder ID: `133phdQHMHUfrg0rHtp6oa4zFm41FE45V`
- Nome: "RAVI OM"
- Link: https://drive.google.com/drive/folders/133phdQHMHUfrg0rHtp6oa4zFm41FE45V
- Mauro coloca OMs assinadas em PDF ali

## Grupo Ordens de Missão
- Chat ID: `-1003866369114`
- Nome: "Ordens de Missão — GTE"
- Tipo: supergroup
- Uso: Mauro envia OMs assinadas (fotos/PDFs), prioridade máxima sobre todas as fontes

## Hierarquia de prioridade missões
1. 🔴 **Ordem de Missão (OM)** — documento assinado, prioridade máxima
2. 🟢 **Diário (aba)** — rascunho/planejamento
3. 🔵 **SAVISO** — sobreaviso (tripulação reserva), NÃO é missão

## SisGOPA Alertas Pop-up
- Toast notification system: `alerts.json` fetched every 10 min
- Dismiss = hidden 1h, then reappears until `expires` date
- Cron `b4f9b732`: Monitor viagens INTERNACIONAIS do PR (5×/day BRT)
- Validade: viagem = até 1d após viagem; cancelamento = 7 dias
- Alertas SÓ no pop-up do SisGOPA, NÃO no Telegram
- Dedup by `viagem-YYYYMMDD-pais` / `cancela-YYYYMMDD-pais`

## Modal OM + Missões para todos tripulantes
- Clicar "📋 OM" abre modal: tripulação + pernas + combustível (min/rec litros)
- `getOMsForCrew()` / `renderOMsNaBusca()` — mostra missões OM para qualquer tripulante na BUSCA (não só pilotos)

## Regras permanentes
- **Fonte de dados quebrada = avisar Mauro direto** — se aba renomeada, coluna movida, planilha inacessível, avisa pelo Telegram na hora, sem rodeio. Ex: "Mauro, aba Férias não encontrada na planilha. Pode ter sido renomeada."
- Bug fixes automáticos, sugestões precisam de OK
- Bot Telegram e SisGOPA BOT idênticos (bidirecional)
- Alertas só no popup do SisGOPA, não via Telegram (exceto fontes quebradas)

## Bot S3 Consulta (novo)
- @SISGOP_BOT (ID: 8429586140)
- Token: 8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU
- Função: consulta de escalação, respostas dos pilotos, recebimento de OM
- Separado do bot de planejamento

## Bot GTE Planejamento
- @GTEplanejamento_BOT — bot de planejamento de voos
- Código: workspace/gte_bot/bot.py
- Roda via python3 em background
- Todas as consultas ao vivo, sem cache
- Fontes: aviationweather.gov, Univ. Wyoming, AISWEB scraping, CELOG
- Aguardando chaves API: AISWEB + REDEMET (DECEA)

## Diárias — Persistência via Google Sheets
- Planilha: "SisGOPA - Diárias" (ID: `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE`)
- Apps Script Web App: `https://script.google.com/macros/s/AKfycbyUm_PXR8M9yU1jLhUQC60SYNF_WEUmsxsb3hMigElzBOwI2LYEGKVkXyC_A1g1bOf4/exec`
- GET retorna JSON das diárias concluídas; POST com `{action:'concluir',om_id:'...'}` ou `{action:'desfazer',om_id:'...'}`
- Substituiu localStorage como fonte de verdade — todos os usuários veem o mesmo status
- localStorage mantido como cache rápido local

## Arredondamento tempo de voo
- Mudou de ceil (múltiplo de 5 superior) para round (múltiplo de 5 mais próximo)
- Aplicado em: bot.py (`round_nearest_5`) e index.html (`roundNearest5`)

## SisGOPA — Decisões Recentes
- **BEH e SOZ excluídos** — não fazem mais parte do GTE; lista `EXCLUIDOS` em `getPilotStatus`
- **Afastamento auto-calculado** — `calcAfastamentos()` usa `flights[]` (dias desde último voo); substituiu `fetchPauDeSebo()`
- **TV alertas**: mostra DESADAPTADO/INDISPONÍVEL/FÉRIAS, ordenado por prioridade, sem limite
- **TV total horas**: "Total de Horas Voadas — 2026" com animação glow
- **KPI filter**: usa `getPilotStatus(p,td).status!=='FORA'` em vez de `p.grupo!=='OUT'`
- **Versão atual**: v4.3, último commit `7f7e0ad`

## SisEscala Roadmap
- **Fase 1 (atual):** Dashboard TV lendo Google Sheets (read-only) — CSV export, auto-refresh 5min
- **Fase 2 (futuro):** SisEscala vira sistema principal com banco de dados próprio; inserção de dados direto no sistema; planilha deixa de ser fonte; backend necessário (API + DB)
- Mauro quer que a arquitetura já esteja preparada pra receber essa evolução
- Planilha "Dashboard" separada: `1EV81x0Np-zeHhznvzAGrPyck5YUHgW_eRb18uOGc7nQ` (sobreaviso, diárias, missões diárias FAB 2101/2590)
- URL live: https://mauromamachado-creator.github.io/sisescala-tv/

## Regra: Bot Telegram ↔ SisGOPA sincronizados
- Toda alteração no bot (bot.py) DEVE ser replicada na tela BOT do SisGOPA (index.html)
- São a mesma coisa — mesmas lógicas, mesmas regras, mesmos resultados, mesmos manuais (ANAC/FAA/ICAO)
- Qualquer alteração num DEVE refletir no outro — bidirecional
- Funções espelhadas: METAR, TAF, NOTAMs, Aeródromo, Tempo de Voo, Combustível, SkyVector, Planejar Voo, Msg Padrão, Código ICAO

## Plano Diretor (Livro Branco) — 07/03/2026
- Arquivo: `sisescala/ROADMAP.md`
- Fases: Visualização (v4.x ✅) → Alertas Proativos (v5) → Escrita/Interação (v6) → Integração Bot↔SisGOPA (v7) → Automação Inteligente (v8) → PWA/App (v9)
- Próxima fase: Alertas proativos Telegram (cartões, desadaptação, relatório diário)
- Princípio: planilhas como fonte de verdade, mobile first, sem servidor próprio por enquanto
