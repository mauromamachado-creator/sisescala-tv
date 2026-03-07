# CHANGELOG — SisGOPA

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
