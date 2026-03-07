# SisGOPA — Plano Diretor (Livro Branco)

**Versão:** 1.0 — 07/03/2026
**Autor:** Major Machado + Ravi 🦀

---

## Visão

Transformar o SisGOPA de painel de visualização em **ferramenta operacional completa** do GTE — onde o operador não só consulta, mas **decide, registra e automatiza**.

---

## Fase Atual: VISUALIZAÇÃO ✅ (v4.x)

O que já funciona:
- Dashboard com KPIs em tempo real
- Disponibilidade de pilotos (cruzamento automático: cartões + afastamento + férias + CVI)
- Ranking de horas voadas (pau de sebo + lançamentos)
- Cartões de validade (todos os tripulantes)
- Calendário, busca, checklist diário
- Escala e missões confirmadas (SAVISO)
- TV/BI para tela do esquadrão
- OMs processadas do Google Drive
- METAR multi-localidade
- Mobile responsivo + hamburger menu
- Alertas: desadaptado, indisponível, cartões vencidos (pilotos + demais tripulantes)

---

## Fase 1: ALERTAS PROATIVOS (v5.0)

**Objetivo:** O sistema avisa antes de acontecer.

- [ ] Alerta Telegram: cartão vencendo em 30/15/7 dias
- [ ] Alerta Telegram: piloto vai desadaptar em X dias se não voar
- [ ] Relatório diário automático (07h BRT): disponíveis, missões, pendências
- [ ] Checklist: alerta se não completou até o horário limite
- [ ] Previsão de indisponibilidade: "em 15 dias, N pilotos desadaptam"

**Esforço:** 1-2 semanas
**Impacto:** Alto — ninguém precisa lembrar de checar, o sistema avisa

---

## Fase 2: ESCRITA E INTERAÇÃO (v6.0)

**Objetivo:** Parar de só ler. Registrar e decidir direto no SisGOPA.

- [ ] Checklist interativo: marcar tarefas direto no sistema (escrita no Sheets)
- [ ] Confirmar/alterar escala via SisGOPA
- [ ] Registrar observações por tripulante
- [ ] Editar férias e status
- [ ] Autenticação por usuário (quem pode ver vs quem pode editar)

**Esforço:** 3-4 semanas (requer Google Sheets API com OAuth)
**Impacto:** Muito alto — vira ferramenta de trabalho, não só painel

---

## Fase 3: INTEGRAÇÃO BOT ↔ SisGOPA (v7.0)

**Objetivo:** Bot de planejamento como motor, SisGOPA como interface visual.

- [ ] Formulário "Planejar Missão" no SisGOPA (substitui `/planejar` do Telegram)
- [ ] METAR/TAF consultado direto na interface (sem comando)
- [ ] Consulta de combustível (CELOG) visual
- [ ] Chat embutido para comandos avançados
- [ ] Resultado do planejamento renderizado no SisGOPA
- [ ] NOTAMs na interface

**Esforço:** 1-2 meses
**Impacto:** Unifica tudo num lugar só

---

## Fase 4: AUTOMAÇÃO INTELIGENTE (v8.0)

**Objetivo:** O sistema sugere e otimiza.

- [ ] Sugestão automática de escala (baseada em horas + disponibilidade + desadaptação)
- [ ] Simulador: "se escalar fulano, quanto falta pra meta?"
- [ ] Gerador automático de OM (template preenchido)
- [ ] Otimização de distribuição de horas (equalizar ranking)
- [ ] Detecção de conflitos (mesmo piloto em 2 missões)

**Esforço:** 2-3 meses
**Impacto:** Game changer — decisão assistida por dados

---

## Fase 5: APP NATIVO / PWA (v9.0)

**Objetivo:** Experiência de app no celular.

- [ ] Service Worker para funcionar offline
- [ ] Push notifications nativas
- [ ] Instalável na home do celular
- [ ] Possível publicação na Play Store (via TWA/Capacitor)

**Esforço:** 1-2 semanas (PWA) / 1 mês (app store)
**Impacto:** Médio — melhora experiência, mas já funciona no browser

---

## Princípios

1. **Não quebrar o que funciona** — cada fase é incremental
2. **Planilhas continuam como fonte de verdade** — até migrar para banco próprio
3. **Mobile first** — tudo deve funcionar no celular
4. **Sem servidor próprio por enquanto** — GitHub Pages + Google Sheets + Telegram
5. **Automatizar o que é esquecido** — alertas > dashboards bonitos
6. **O operador decide, o sistema sugere** — nunca escalar automaticamente sem aprovação

---

## Métricas de Sucesso

- Fase 1: Redução de incidentes por cartão vencido / piloto desadaptado não detectado
- Fase 2: Operadores usando SisGOPA como ferramenta principal (não a planilha)
- Fase 3: Bot Telegram se torna secundário (SisGOPA é a interface principal)
- Fase 4: Tempo de montagem de escala reduzido em 50%+

---

---

## Cronograma de Lançamentos

| Versão | Fase | Previsão | Escopo Principal |
|--------|------|----------|------------------|
| v4.4 | Visualização | ✅ 07/03/2026 | Cartões, filtros, auditoria, EXT, busca expandida |
| v5.0 | Alertas Proativos | 21/03/2026 | Alertas Telegram (cartões, desadaptação, relatório diário) |
| v5.1 | Alertas Proativos | 04/04/2026 | Previsão de indisponibilidade, alerta checklist |
| v6.0 | Escrita | 02/05/2026 | Checklist interativo, edição de status/férias |
| v7.0 | Bot Integrado | 06/06/2026 | Planejamento via SisGOPA, formulários visuais |
| v8.0 | Automação | 08/08/2026 | Sugestão de escala, gerador de OM, simulador |
| v9.0 | App | 10/10/2026 | PWA completo, push notifications |

*Datas são estimativas. Cada versão major requer validação do Major Machado antes do deploy.*

---

_Este documento é vivo. Atualizar conforme as prioridades mudam._
