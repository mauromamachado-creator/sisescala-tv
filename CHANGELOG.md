# SisGOPA — Changelog

## v4.2 — 06/03/2026
### Novidades
- 🏆 **TV: Top Horas GTE** — ranking unificado (VC-1 + VC-2 juntos), top 8 pilotos por horas voadas
- 📊 **TV: Progresso Horas do Ano** — barras VC-1, VC-2 e Total GTE com marcador da meta anual
- 🖼️ **Logo transparente** — sem bordas brancas, integrada ao tema dark
- 📏 **Logo mobile ajustável** — 40px no celular, 56px no desktop
- 📱 **Ícone PWA** — pode adicionar à tela inicial do iPhone/Android como app
- 🌐 **Favicon** personalizado com logo SisGOPA

### Correções
- Marcador "meta de voo hoje" mais visível (branco, glow, maior)

## v4.1 — 06/03/2026
### Novidades
- 🚦 **Status 3 cores**: verde (tudo OK), amarelo (falha parcial), vermelho (erro crítico)
- 💬 **Tooltip no status dot**: passe o mouse/toque pra ver detalhes
- 📝 **Renomeação**: SisGOP → **SisGOPA**

### Correções
- Formato de data: "sexta-feira, 6 de março de 2026 — HH:MM:SS"
- METAR observação UTC não quebra mais linha no desktop (flex layout)

## v4.0 — 06/03/2026
### Novidades
- 🔄 **Auto-update**: código atualiza automaticamente a cada 5 minutos (sem precisar limpar cache)
- 🔗 **Link curto**: https://is.gd/sisgop
- 🖼️ **Logo personalizada** no header (substituiu SVG genérico)
- 🌙 **Badge PERN** com visual diferenciado (pernoite) + tipo de missão quando disponível
- 📊 **DIÁRIO na TV**: pisca vermelho após deadline, verde fixo quando 100%
- 🎨 **Cor progressiva do DIÁRIO**: baseada no horário vs percentual (meta 17h seg-qui, 12h sex)
- 📅 **Formato de data**: "sexta-feira, 6 de março de 2026 — HH:MM:SS"
- 📱 **Status de conexão no mobile**: dot verde/vermelho + horário de atualização
- 🏖️ **Férias na Busca**: só mostra férias atuais ou futuras (passadas desconsideradas)

### Correções
- 🐛 Fix: férias não apareciam no calendário (`startDate/end` → `inicio/fim`)
- 🐛 Fix: `medals is not defined` no dashboard (trocado por 1º, 2º, 3º)
- 🐛 Fix: METAR CORS — removido acesso direto ao aviationweather.gov (só proxy)
- ✏️ Gramática: Missões, Férias, Próximas, Últimos, conexão (acentos corrigidos)
- ✏️ TBD → A DEFINIR
- 🧹 Código morto removido: `const medals`, `GIDS.ferias`

### Alertas TV
- Agora mostra apenas **indisponíveis** e **férias** (removidos alertas externos)

### Estética
- Badge tipo missão alinhado (desktop + mobile)
- METAR: layout flex (observação UTC não quebra mais linha no desktop)

---

## v3.0 — 05/03/2026
### Novidades
- 📺 **Tela TV** (screen9) com grid 3×3: KPIs, missões, top pilotos, METAR multi, alertas, próximos dias
- 🔍 **Multi-METAR**: SBBR, SBCF, SBRJ, SBSP em uma única requisição
- 🔒 **ESCALA** com proteção por senha
- ✅ **SAVISO**: missões confirmadas com prioridade sobre planejamento
- 📊 **Esforço aéreo**: progresso com alertas 50%/70% (ofício GABAER)
- 🏆 **Rankings**: posições numeradas com cores (verde top 3, amarelo meio, vermelho último)
- 🔎 **Busca**: pesquisa por piloto com horas, férias, missões
- 📅 **Calendário**: visualização mensal de missões

### Correções
- Fix: férias fetch por nome (`fetchCSVByName`)
- Fix: search input focus
- Fix: SAVISO column mapping
- Pilotos `grupo==='OUT'` excluídos dos KPIs

---

## v2.0 — 04/03/2026
### Novidades
- Renomeação: SisEscala → SisOPR → **SisGOP**
- 📋 **Tela DIÁRIO** com checklist de planejamento
- 🛩️ **Disponibilidade** e **Horas de Voo** com dados ao vivo do Google Sheets
- 📊 **ACNT/ALTR**: alertas e acidentes
- 🌤️ **METAR decoder** com traduções em português
- 📱 Layout responsivo mobile (iPhone 375×812)

---

## v1.0 — 03/03/2026
### Lançamento inicial
- Dashboard básico com KPIs
- Leitura de dados do Google Sheets
- Tela de disponibilidade de tripulantes
- Horas de voo por aeronave
- Layout dark mode para TV (1280×720)
