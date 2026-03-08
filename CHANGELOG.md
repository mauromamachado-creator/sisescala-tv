# CHANGELOG — SisGOPA

## v4.7 — 07/03/2026
### Novidades
- **Telefone e e-mail na BUSCA**: dados de contato clicáveis (liga/envia email direto)
- **DIÁRIAS filtro por missão**: só gera solicitação para missões PR, Reserva PR ou ESCAV
- **Cache de status**: `getPilotStatus()` com cache 30s — carregamento mais rápido
- **Cloudflare Worker METAR**: slot preparado como 1º proxy no fallback chain (deploy manual pendente)
- **Cartões vencidos = indisponível**: confirmado funcionando — Insp. Saúde, CVI/RVSM e CRM vencidos tornam tripulante indisponível

## v4.6 — 07/03/2026
### Novidades
- **Alertas Pop-up**: notificações automáticas de viagens internacionais do PR (confirmadas e canceladas), com validade configurável
- **Modal detalhe OM**: clicar em "📋 OM" mostra tripulação completa + combustível + pernas de voo
- **Missões para todos**: mecânicos, comissários, op.comms e médicos veem suas próximas missões na BUSCA (via dados das OMs)
- **Novidades no rodapé**: link com changelog e dicas de uso
- **Safari/Chrome mobile**: barra de endereço minimiza ao rolar (scroll nativo)
- **Links clicáveis com underline**: padrão visual para indicar interatividade
- **"Previsão Missões Int."**: título renomeado no dashboard

### Correções
- Scroll infinito no mobile corrigido (telas inativas com display:none)
- Footer visível no Android (100dvh)
- Pop-up centralizado na tela

## v4.5 — 07/03/2026
### Novidades
- **Tela BOT** (screen 11): METAR, TAF, NOTAMs, combustível, planejamento de voo, Código ICAO e mais
- **Tela REPORTAR** (screen 12): envio de bugs/sugestões direto do sistema
- **Animação loading**: avião SVG azul com rastro pontilhado
- **Decodificar METAR/TAF**: tradução completa em português
- **Status monitor**: 15 fontes rastreadas individualmente com painel clicável
- **BOT Combustível**: double check CELOG site + planilha
- **BOT Código ICAO**: 5259 aeroportos mundiais + fallback API

## v4.4 — 07/03/2026
### Novidades
- **Cartões mobile**: layout em cards (grid 2 colunas) em vez de tabela
- **Filtros na tela Cartões**: por status (regulares/atenção/vencidos) e por função (Pilotos/Mecânicos/etc)
- **Cruzamento cartões × disponibilidade**: cartão vencido (Insp Saúde, CVI/RVSM, CRM) = INDISPONÍVEL
- **Múltiplos motivos**: getPilotStatus reporta todos os motivos (ex: "INDISPONÍVEL (CVI, INSP SAÚDE)")
- **Alertas Dashboard**: inclui demais tripulantes (comissários, mecânicos) com cartões vencidos
- **CVI/RVSM exclusivo para pilotos**: comissários/mecânicos não são avaliados nesse cartão
- **Horas voadas**: pau de sebo como fonte primária, lançamentos como fallback
- **EXT no ranking**: pilotos externos com horas aparecem no ranking (sem %, só horas)
- **Busca expandida**: encontra mecânicos, comissários, op.comms, médicos (via aba cartões)
- **Trigrama duplicado**: DAN/CIR/ALX diferenciados por nome e aeronave — férias, cartões e status nunca se misturam
- **Hamburger menu mobile**: nav escondida, ☰ MENU toggle, grid 2 colunas

### Correções (Auditoria)
- Timeout 15s em todos os fetches (AbortController) — evita travamento
- Fallback cartões: alerta "DADOS INCOMPLETOS" quando aba cartões falha
- calcAfastamentos: regex word-boundary evita match parcial de trigrama
- setInterval com referências globais (cleanup ready)
- Calendário mobile: fonte menor, scroll touch
- Ranking: bar-hours largura fixa no mobile (alinhamento)

## v4.3 — 07/03/2026
- calcAfastamentos auto-calculado (substituiu pau de sebo como fonte de afastamento)
- BEH/SOZ excluídos (EXCLUIDOS array)
- TV Alertas: DESADAPTADO + DESADAPTADO PR + INDISPONÍVEL + FÉRIAS ordenados por prioridade
- TV: "Total de Horas Voadas 2026" com glow animado
- TV METAR: fonte menor para caber 4 localidades
- KPI renomeado: "MISSÕES CUMPRIDAS"
- Missões de hoje: fix duplicação (comparação noon-to-noon)
- CARTÕES: nova tela (screen 10) com validade de todos os tripulantes
- BUSCA: integração cartões no card de busca

## v4.2 — 06/03/2026
- OMs integradas: Google Drive → om_data.json → SisGOPA
- Hierarquia missões: OM > confirmaData > Diário
- Badge 📋 OM nos próximos dias
- EXT handling correto
- Desadaptado PR como alerta (20-34 dias)

## v4.1 — 06/03/2026
- TV modo BI (header/nav/footer ocultos)
- Fullscreen button
- SAVISO como sobreaviso
- ESCALA com senha SHA-256
- METAR 3 proxies com fallback
- METAR SPECI support

## v4.0 — 06/03/2026
- SisGOPA (renomeado de SisGOP)
- Multi-METAR (SBBR, SBCF, SBRJ, SBSP)
- TV screen com grid 3×3
- Auto-update mechanism
- Logo transparente
- PWA manifest
