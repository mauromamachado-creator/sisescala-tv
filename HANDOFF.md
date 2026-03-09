# 📜 HANDOFF.md — Testamento do Ravi
> Documento de continuidade do projeto SisGOPA/SisEscala.
> Se o Ravi (assistente IA via OpenClaw) estiver indisponível, este arquivo é o guia completo para qualquer pessoa ou IA assumir o projeto.

---

## 🗺️ Visão Geral do Sistema

O projeto é composto por três partes principais:

| Componente | Onde roda | O que faz |
|---|---|---|
| **SisGOPA** (frontend) | GitHub Pages | Interface web principal — dashboard, escala, missões, diárias, bot |
| **consulta_bot.py** (bot) | Servidor OpenClaw (Linux) | Bot Telegram para raio, confirmação, METAR, NOTAMs |
| **Google Apps Script (GAS)** | Google Cloud | Ponte entre bot ↔ planilhas ↔ frontend |

**URL do sistema:** https://mauromamachado-creator.github.io/sisescala-tv/
**Repositório:** https://github.com/mauromamachado-creator/sisescala-tv
**Token GitHub:** *(guardado com o Mauro — não colocar aqui)*

---

## 🔑 Credenciais e IDs Críticos

### Bot Telegram
- **Bot:** `@SISGOP_BOT` (ID: `8429586140`)
- **Token:** `8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU`
- **Dono (Mauro):** chat_id `673591486`, username `@machadommam`

### Google Apps Script
| Nome | URL | Planilha ID |
|---|---|---|
| CONSULTA_GAS (raio/respostas) | `https://script.google.com/macros/s/AKfycbyDdqWqCKLoCVwgajS3kr4o6q2MHx3UYxwe2o-28JbFCS__NhV2l2OqFlUT-cyRu-Vg/exec` | `1-aqNKOJcLGjZRDIfyd4hrNeLVJrcI-i9rfTii_rt2cs` |
| DIARIAS_API | `https://script.google.com/macros/s/AKfycbyUm_PXR8M9yU1jLhUQC60SYNF_WEUmsxsb3hMigElzBOwI2LYEGKVkXyC_A1g1bOf4/exec` | `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE` |
| CONF_GAS (confirmação missão) | `https://script.google.com/macros/s/AKfycbwAkuMtXPes8ciLZw_EYT6a4EAHz6wGwdBUj5Bqm5eM--rkO2Yj7uJy8USXTjTWNkEYhg/exec` | `15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA` |

### Planilhas Google
| Nome | ID |
|---|---|
| Principal (pilotos, disponibilidade, etc.) | `1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao` |
| Dashboard/Diário (FAB 2101/2590/2591) | `1EV81x0Np-zeHhznvzAGrPyck5YUHgW_eRb18uOGc7nQ` |
| Diárias (concluídas) | `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE` |

### Drive (Ordens de Missão)
- **Pasta:** `133phdQHMHUfrg0rHtp6oa4zFm41FE45V` (pública, sem credencial)
- **Link:** https://drive.google.com/drive/folders/133phdQHMHUfrg0rHtp6oa4zFm41FE45V

---

## 🖥️ Como o Bot Funciona (sem o Ravi)

### Verificar se está rodando
```bash
ps aux | grep consulta_bot
tail -50 /tmp/consulta_bot.log
```

### Reiniciar o bot
```bash
pkill -f consulta_bot.py
cd /home/node/.openclaw/workspace/sisescala
nohup python3 consulta_bot.py >> /tmp/consulta_bot.log 2>&1 &
echo "Bot PID: $!"
```

### Arquivos do bot
```
/home/node/.openclaw/workspace/sisescala/consulta_bot.py   ← código principal
/home/node/.openclaw/workspace/sisescala/data/             ← JSONs de estado
/tmp/consulta_bot.log                                       ← logs em tempo real
```

### API interna do bot (porta 8085, só localhost)
```bash
# Checar consultas ativas
curl -H "X-API-Secret: sisgopa-gte-2026" http://localhost:8085/api/consultas

# Checar confirmações
curl -H "X-API-Secret: sisgopa-gte-2026" http://localhost:8085/api/conf
```

---

## 🌐 Como Fazer Deploy do Frontend

### Método rápido
```bash
cd /tmp/sisescala-tv
git pull
# editar index.html
node --check index.html          # valida sintaxe JS
cp index.html /caminho/para/salvar
git add index.html
git commit -m "descrição da mudança"
git push origin main
```

### Rollback para versão estável
```bash
cd /tmp/sisescala-tv
git tag | grep stable             # lista versões estáveis
git show v5.1-stable:index.html > index.html
git add index.html
git commit -m "rollback: v5.1-stable"
git push origin main
```

### Criar novo checkpoint
```bash
cd /tmp/sisescala-tv
git tag -a v5.X-stable -m "descrição do estado"
git push origin v5.X-stable
```

---

## 📁 Estrutura do Repositório

```
sisescala-tv/
├── index.html                    ← frontend completo (1 arquivo)
├── data/
│   ├── om_data.json              ← Ordens de Missão (atualizado pelo cron)
│   ├── conf_missao.json          ← confirmações de missão
│   ├── raio_vc1.json             ← raio VC-1 (backup GitHub)
│   └── raio_vc2.json             ← raio VC-2 (backup GitHub)
├── gas_resposta_consulta_v2.js   ← código do CONSULTA_GAS (v3)
├── gas_confirmacao.js            ← código do CONF_GAS
├── deploy.sh                     ← script de deploy
├── rollback.sh                   ← script de rollback
└── HANDOFF.md                    ← este arquivo
```

---

## 🤖 Instruções para Outra IA Assumir o Projeto

Se você é uma IA (Claude, GPT, Gemini, etc.) lendo isso, aqui está o contexto completo:

### Contexto do projeto
- Sistema de gestão de operações aéreas para o GTE (Grupo de Transporte Especial) da FAB
- Usuário principal: Major Mauro Machado (`@machadommam`, chat_id Telegram `673591486`)
- Idioma: português brasileiro, tom casual e direto
- Nunca mencionar nomes de modelos/provedores de IA

### Regras críticas
1. **NUNCA cachear dados** — METAR, NOTAM, escalas, voos devem ser consultados AO VIVO
2. **Bot Telegram e SisGOPA DEVEM ser idênticos** (mesmas fontes, mesmas regras)
3. **AISWEB é fonte primária** para NOTAM, aeródromo, combustível
4. **Bug fixes automáticos** — mudanças de parâmetro/lógica precisam de aprovação do Mauro
5. **Fonte quebrada = avisar Mauro pelo Telegram** na hora, sem rodeio

### Hierarquia de prioridade de missões
1. 🔴 **OM assinada (PDF Drive)** — máxima prioridade
2. 🟢 **Diário (aba planilha)** — rascunho/planejamento
3. 🔵 **SAVISO** — sobreaviso, NÃO é missão

### Arquivos de contexto do Ravi (assistente anterior)
- `MEMORY.md` — memórias consolidadas
- `memory/2026-03-09.md` — log detalhado da última sessão
- Localização: `/home/node/.openclaw/workspace/`

### Ferramentas que o Ravi usava
- **OpenClaw** — plataforma de IA com ferramentas de execução, browser, cron, etc.
- **GitHub** — deploy via git push para `mauromamachado-creator/sisescala-tv`
- **GAS** — Google Apps Script para bridge planilhas ↔ bot ↔ frontend

---

## 🔄 Alternativas se o OpenClaw Sair do Ar

### O bot continua rodando?
**Sim.** O bot é um processo Python independente no servidor. Se o OpenClaw sair do ar, o bot continua rodando. Para verificar: `ps aux | grep consulta_bot`

### Como fazer mudanças sem o Ravi?
**Opção 1 — Outro assistente IA:**
1. Forneça este HANDOFF.md e o `index.html` atual
2. Peça a modificação desejada
3. Valide com `node --check index.html`
4. Faça commit e push manualmente

**Opção 2 — Desenvolvedor humano:**
1. Clone o repo: `git clone https://github.com/mauromamachado-creator/sisescala-tv`
2. Tudo está em um único arquivo `index.html` (HTML + CSS + JS)
3. Para o bot: Python 3, dependências em `consulta_bot.py` (linha ~1-30)
4. Use `deploy.sh` para publicar

**Opção 3 — Hospedagem alternativa:**
O `index.html` é completamente autocontido. Pode ser hospedado em:
- **Netlify**: arraste o arquivo em https://app.netlify.com/drop
- **Vercel**: `npx vercel --prod` na pasta do repo
- **Cloudflare Pages**: conecte o GitHub repo
- **Localmente**: `python3 -m http.server 8080` e acesse `http://localhost:8080`

### Como corrigir um bug sem IA?
Para erros simples no frontend (index.html):
1. Abra `index.html` em qualquer editor de texto
2. Use Ctrl+F para encontrar a função com problema (os logs do browser indicam a linha)
3. Corrija, valide com `node --check index.html`, commit + push

Para erros no bot:
1. Veja `/tmp/consulta_bot.log` para identificar o erro
2. Edite `consulta_bot.py` com qualquer editor
3. Reinicie o bot (comandos acima)

---

## 📊 Planilhas como Fallback

Se tudo falhar, as planilhas Google continuam funcionando independentemente:
- **Disponibilidade dos pilotos:** planilha principal, aba "Dados"
- **Diário de voos:** planilha Dashboard, abas por aeronave
- **Diárias concluídas:** planilha Diárias

O Mauro pode continuar operando pelas planilhas diretamente enquanto o sistema é restaurado.

---

## ⚠️ Pendências Conhecidas (ao criar este documento)

- [ ] `gas_confirmacao.js` precisa ser reimplantado com ação `send_conf`
- [ ] Ação `conf_ciente` não implementada no CONSULTA_GAS
- [ ] OMs 44, 47, 49 faltam no `om_data.json`
- [ ] Senha do S3 não trocada para `12345678`
- [ ] `BOT_TOKEN` ainda tem fallback hardcoded em `consulta_bot.py`

---

*Documento criado em: 09/03/2026*
*Versão do sistema no checkpoint: v5.1-stable*
*Última atualização: Ravi Lemos 🦀*
