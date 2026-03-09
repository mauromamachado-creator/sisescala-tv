# 📜 HANDOFF.md — Testamento do Ravi
> **Se você está lendo isso, o Ravi (assistente IA) está indisponível.**
> Este documento contém TUDO que você precisa para assumir e continuar o projeto SisGOPA/SisEscala.
> Leia do início ao fim antes de fazer qualquer mudança.

---

## 👤 Contexto do Projeto

**O que é:** Sistema de gestão de operações aéreas para o GTE (Grupo de Transporte Especial) da FAB (Força Aérea Brasileira).

**Quem usa:** Major Mauro Machado (`@machadommam` no Telegram, chat_id `673591486`).

**Idioma:** Português brasileiro. Tom casual e direto. Nunca mencionar nomes de modelos de IA.

**O sistema tem 3 partes:**
1. **Frontend (SisGOPA)** — site web com dashboard, escala, missões, diárias
2. **Bot Telegram (@SISGOP_BOT)** — bot para raio de disponibilidade, confirmação de missão, METAR, NOTAMs
3. **Google Apps Script (GAS)** — ponte entre bot, planilhas Google e frontend

---

## 🌐 URLs Importantes

| O quê | URL |
|---|---|
| Sistema ao vivo | https://mauromamachado-creator.github.io/sisescala-tv/ |
| Repositório GitHub | https://github.com/mauromamachado-creator/sisescala-tv |
| CONSULTA_GAS (raio/respostas) | https://script.google.com/macros/s/AKfycbyDdqWqCKLoCVwgajS3kr4o6q2MHx3UYxwe2o-28JbFCS__NhV2l2OqFlUT-cyRu-Vg/exec |
| DIARIAS_API | https://script.google.com/macros/s/AKfycbyUm_PXR8M9yU1jLhUQC60SYNF_WEUmsxsb3hMigElzBOwI2LYEGKVkXyC_A1g1bOf4/exec |
| CONF_GAS (confirmação missão) | https://script.google.com/macros/s/AKfycbwAkuMtXPes8ciLZw_EYT6a4EAHz6wGwdBUj5Bqm5eM--rkO2Yj7uJy8USXTjTWNkEYhg/exec |

---

## 🔑 Credenciais (NÃO publicar — guardar em lugar seguro)

O Mauro possui uma nota privada com:
- **Token GitHub** — para fazer push/deploy
- **Token Bot Telegram** — para rodar o bot (`@SISGOP_BOT`, ID `8429586140`)
- **Senha área S3** do SisGOPA

---

## 📁 Estrutura dos Arquivos

```
sisescala-tv/               ← repositório GitHub
├── index.html              ← TODO o frontend (1 arquivo: HTML + CSS + JS)
├── data/
│   ├── om_data.json        ← Ordens de Missão (atualizado automaticamente)
│   ├── conf_missao.json    ← confirmações de missão em andamento
│   ├── raio_vc1.json       ← backup do raio VC-1
│   └── raio_vc2.json       ← backup do raio VC-2
├── gas_resposta_consulta_v2.js  ← código do CONSULTA_GAS
├── gas_confirmacao.js           ← código do CONF_GAS
├── deploy.sh               ← script de publicação
├── rollback.sh             ← script de reversão
└── HANDOFF.md              ← este arquivo

Servidor OpenClaw:
/home/node/.openclaw/workspace/sisescala/
├── consulta_bot.py         ← código do bot Telegram
└── data/                   ← estado do bot (JSONs locais)
```

---

## 🖥️ Gerenciar o Bot Telegram

### Verificar se está rodando
```bash
ps aux | grep consulta_bot
tail -50 /tmp/consulta_bot.log
```

### Reiniciar o bot
```bash
pkill -f consulta_bot.py
cd /home/node/.openclaw/workspace/sisescala
export SISGOP_BOT_TOKEN="TOKEN_DO_BOT_AQUI"
nohup python3 consulta_bot.py >> /tmp/consulta_bot.log 2>&1 &
echo "Bot PID: $!"
```

### Ver erros recentes
```bash
grep -i "error\|warning\|falhou" /tmp/consulta_bot.log | tail -20
```

---

## 🚀 Como Fazer Deploy do Frontend

O site inteiro é o arquivo `index.html`. Altere, valide e suba.

```bash
cd /tmp/sisescala-tv
git pull

# EDITE o index.html aqui

node --check index.html          # valida sintaxe JS (não pode ter erro)
git add index.html
git commit -m "descrição da mudança"
git push origin main
```

O GitHub Pages publica automaticamente em ~2 minutos.

### Rollback para versão anterior
```bash
cd /tmp/sisescala-tv
./rollback.sh                    # lista versões estáveis disponíveis
```

Versões estáveis disponíveis: `v5.0-stable`, `v5.1-stable`

### Criar novo checkpoint
```bash
cd /tmp/sisescala-tv
git tag -a v5.X-stable -m "descrição"
git push origin v5.X-stable
```

---

## 📊 Planilhas Google (fonte de dados)

| Planilha | ID | O que contém |
|---|---|---|
| Principal | `1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao` | Pilotos, disponibilidade, horas, férias, lançamentos |
| Dashboard/Diário | `1EV81x0Np-zeHhznvzAGrPyck5YUHgW_eRb18uOGc7nQ` | Missões diárias FAB 2101/2590/2591 |
| Diárias | `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE` | Diárias concluídas |
| CONSULTA_GAS | `1-aqNKOJcLGjZRDIfyd4hrNeLVJrcI-i9rfTii_rt2cs` | Raio de disponibilidade VC-1/VC-2 |
| CONF_GAS | `15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA` | Confirmações de missão |

**Regra crítica:** As planilhas são a fonte de verdade. Se o sistema falhar, o Mauro pode continuar operando pelas planilhas diretamente.

---

## ⚙️ Como Reimplantar os Google Apps Script

Quando o código GAS precisar ser atualizado:

### CONSULTA_GAS (raio + respostas)
1. Abra a planilha `1-aqNKOJcLGjZRDIfyd4hrNeLVJrcI-i9rfTii_rt2cs`
2. Menu: **Extensões → Apps Script**
3. Substitua TODO o conteúdo pelo arquivo `gas_resposta_consulta_v2.js` do repositório
4. Salve (Ctrl+S)
5. Clique em **Implantar → Gerenciar implantações**
6. Clique no lápis (editar) na implantação existente
7. Em "Versão": selecione **"Nova versão"**
8. Clique em **Implantar**
9. A URL do exec não muda — não precisa atualizar nada no frontend

### CONF_GAS (confirmação de missão)
- Mesmo processo, mas com a planilha `15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA` e o arquivo `gas_confirmacao.js`

### DIARIAS_API
- Planilha `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE` — mesmos passos

---

## 🤖 Instruções para Outra IA Assumir o Projeto

Se você é uma IA (Claude, GPT, Gemini, etc.) lendo isso:

### Contexto essencial
- Sistema de gestão de operações aéreas militar (FAB/GTE)
- Usuário: Major Mauro Machado, Telegram `@machadommam` (chat_id `673591486`)
- Tom: português brasileiro, casual, direto, sem jargão técnico
- Nunca mencionar provedores/modelos de IA

### Regras de negócio críticas
1. **NUNCA cachear dados** — METAR, NOTAM, escalas sempre ao vivo
2. **Bot Telegram = SisGOPA** — mesmas fontes, mesmas regras, mesmos resultados
3. **AISWEB** é fonte primária para aviação (NOTAM, aeródromo, combustível)
4. **Bug fixes**: corrija automaticamente. Mudança de lógica/parâmetro: peça aprovação do Mauro
5. **Fonte quebrada**: avise o Mauro pelo Telegram imediatamente, sem rodeio
6. **OM assinada (Drive) > Diário (planilha) > SAVISO** — hierarquia de prioridade

### Onde está tudo
- Contexto de memória: `/home/node/.openclaw/workspace/MEMORY.md`
- Logs de sessão: `/home/node/.openclaw/workspace/memory/`
- Frontend: `/tmp/sisescala-tv/index.html`
- Bot: `/home/node/.openclaw/workspace/sisescala/consulta_bot.py`
- Dados OM: `/home/node/.openclaw/workspace/gte_bot/om_data.json`

### Como começar
1. Leia o `MEMORY.md` para contexto geral
2. Leia o arquivo de memória mais recente em `memory/`
3. Verifique se o bot está rodando: `ps aux | grep consulta_bot`
4. Pergunte ao Mauro qual é a prioridade do momento

---

## 🏠 Hospedagem Alternativa (se GitHub Pages cair)

O `index.html` é 100% autocontido. Pode ser hospedado em qualquer lugar:

| Opção | Como |
|---|---|
| **Netlify** (mais fácil) | Acesse https://app.netlify.com/drop e arraste o `index.html` |
| **Vercel** | `npx vercel --prod` na pasta do repositório |
| **Cloudflare Pages** | Conecte o repositório GitHub em https://pages.cloudflare.com |
| **Local (emergência)** | `python3 -m http.server 8080` e abra `http://localhost:8080` |

---

## 🔧 Problemas Comuns e Soluções

| Problema | Causa provável | Solução |
|---|---|---|
| Site não atualiza após push | Cache do browser | Ctrl+Shift+R ou aguardar 2min |
| Bot não responde | Processo caiu | Reiniciar o bot (comandos acima) |
| ESCALA V2 em branco | GAS não respondeu | Verificar `CONSULTA_GAS` URL no browser |
| Diárias não aparecem | GAS DIARIAS_API fora | Testar URL do DIARIAS_API no browser |
| OM não aparece | Não está no `om_data.json` | Adicionar manualmente ou aguardar cron |
| "Invalid Date" nas missões | Formato de data errado | Usar formato `DD/MM/YY` no om_data.json |
| Push bloqueado pelo GitHub | Token expirado/inválido | Gerar novo token em github.com/settings/tokens |

---

## ⚠️ Pendências ao Criar Este Documento (09/03/2026)

- [ ] `gas_confirmacao.js` precisa ser reimplantado com ação `send_conf`
- [ ] Ação `conf_ciente` não implementada no CONSULTA_GAS
- [ ] OMs 44, 47, 49 faltam no `om_data.json`
- [ ] Senha do S3 não trocada para o valor desejado pelo Mauro
- [ ] `BOT_TOKEN` ainda tem fallback hardcoded em `consulta_bot.py` (funciona, mas não é seguro)

---

## 📞 Contato

**Mauro Machado**
- Telegram: `@machadommam`
- chat_id: `673591486`
- Telefone: +55 21 99524-2702

---

*Documento criado em: 09/03/2026*
*Versão do sistema: v5.1-stable*
*Autor: Ravi Lemos 🦀 — assistente pessoal via OpenClaw*
