# 📜 HANDOFF.md — Testamento do Ravi 🦀
> **Se você está lendo isso, o Ravi está indisponível.**
> Este documento foi escrito para que QUALQUER PESSOA — mesmo sem conhecimento de programação — consiga entender o projeto, manter o sistema no ar, corrigir problemas e continuar o desenvolvimento.

---

## 🧭 PARTE 1 — ENTENDENDO O SISTEMA (leia primeiro)

### O que é o SisGOPA?
É um sistema web de gestão de operações aéreas feito especificamente para o **GTE (Grupo de Transporte Especial) da FAB**. Permite ver:
- Disponibilidade dos pilotos (VC-1 e VC-2)
- Missões de hoje e dos próximos dias
- Ordens de Missão (OMs) com tripulação, pernas de voo e combustível
- Diárias a serem pagas
- Escala de consulta de disponibilidade
- Confirmação de missão por Telegram

**Quem usa:** Major Mauro Machado (`@machadommam` no Telegram)

---

### De onde vêm os dados?

```
PLANILHAS GOOGLE → SISTEMA WEB (SisGOPA) → CELULAR DO MAURO (Telegram)
```

| Fonte | O que fornece |
|---|---|
| Planilha principal Google | Nomes dos pilotos, horas voadas, disponibilidade, férias |
| Planilha Dashboard | Missões diárias das aeronaves FAB 2101, 2590, 2591 |
| Planilha Diárias | Registro de diárias concluídas |
| Google Drive (pasta RAVI OM) | PDFs das Ordens de Missão assinadas |
| Bot @SISGOP_BOT | Raio de disponibilidade enviado pelo Mauro via PDF |

---

### As 3 peças do sistema

**Peça 1 — O site (SisGOPA)**
- Endereço principal: https://mauromamachado-creator.github.io/sisescala-tv/
- Endereço espelho: https://sisgopa.netlify.app/ (backup — atualiza junto com o GitHub)
- É um único arquivo chamado `index.html` hospedado gratuitamente no GitHub
- Lê os dados das planilhas Google e mostra na tela
- Não precisa de servidor — funciona como qualquer site normal

**Peça 2 — O bot (@SISGOP_BOT)**
- É um programa Python rodando num servidor da OpenClaw (empresa que hospeda o Ravi)
- Recebe PDFs do Mauro pelo Telegram, processa e atualiza os dados
- Pode enviar mensagens automáticas para os oficiais
- Fica rodando 24h por dia em background

**Peça 3 — Google Apps Script (GAS)**
- São pequenos programas rodando dentro do Google
- Fazem a ponte: bot → planilha, planilha → site
- Ficam em 3 planilhas Google diferentes (ver credenciais abaixo)

---

## 🔑 PARTE 2 — CREDENCIAIS E ACESSOS

> ⚠️ **IMPORTANTE:** O Mauro guarda essas informações em local seguro (não estão aqui por segurança).
> Se você precisar delas, peça diretamente ao Mauro Machado.

### O que o Mauro tem guardado:
1. **Token do GitHub** — senha para publicar novas versões do site
2. **Token do Bot Telegram** — senha para o bot funcionar (começa com `8429586140:...`)
3. **Senha da área S3** do SisGOPA

### IDs públicos (não são senhas, podem ficar aqui):

**Bot Telegram:**
- Nome: `@SISGOP_BOT`
- ID numérico: `8429586140`
- Dono (Mauro): chat_id `673591486`, username `@machadommam`

**Planilhas Google:**
| Planilha | ID (para abrir: docs.google.com/spreadsheets/d/ID) |
|---|---|
| Principal (pilotos/horas/férias) | `1gwkeV2iA_JPTZ3rp0wf1PvXUI0TiOzNg3Xd4DhWwpao` |
| Dashboard/Missões diárias | `1EV81x0Np-zeHhznvzAGrPyck5YUHgW_eRb18uOGc7nQ` |
| Diárias | `1klPOFZED_3Geoqkz9sgMXm3EsF7KzlZIqsz2TgkLZSE` |
| Raio/Respostas (CONSULTA) | `1-aqNKOJcLGjZRDIfyd4hrNeLVJrcI-i9rfTii_rt2cs` |
| Confirmação de Missão | `15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA` |

**Pasta Drive (Ordens de Missão):**
- Link: https://drive.google.com/drive/folders/133phdQHMHUfrg0rHtp6oa4zFm41FE45V
- É pública — qualquer pessoa com o link acessa

**Repositório GitHub:**
- Link: https://github.com/mauromamachado-creator/sisescala-tv
- Conta GitHub: `mauromamachado-creator`

**URLs dos Apps Script (GAS):**
- CONSULTA (raio + respostas): `https://script.google.com/macros/s/AKfycbyDdqWqCKLoCVwgajS3kr4o6q2MHx3UYxwe2o-28JbFCS__NhV2l2OqFlUT-cyRu-Vg/exec`
- DIÁRIAS: `https://script.google.com/macros/s/AKfycbyUm_PXR8M9yU1jLhUQC60SYNF_WEUmsxsb3hMigElzBOwI2LYEGKVkXyC_A1g1bOf4/exec`
- CONFIRMAÇÃO: `https://script.google.com/macros/s/AKfycbwAkuMtXPes8ciLZw_EYT6a4EAHz6wGwdBUj5Bqm5eM--rkO2Yj7uJy8USXTjTWNkEYhg/exec`

---

## 🆘 PARTE 3 — O QUE FAZER SE O RAVI SUMIR

### Cenário 1: OpenClaw saiu do ar temporariamente
**O site continua funcionando** — o SisGOPA não depende do Ravi para exibir dados.
**O bot continua funcionando** — é um processo independente no servidor.
Aguarde o retorno da OpenClaw. Se demorar mais de 24h, veja o Cenário 2.

---

### Cenário 2: Preciso de outro assistente IA para continuar

Qualquer IA moderna (Claude em claude.ai, ChatGPT em chatgpt.com, Gemini em gemini.google.com) consegue assumir o projeto. Siga estes passos:

**Passo 1:** Abra o site da IA que preferir e inicie uma conversa nova.

**Passo 2:** Envie esta mensagem exata:

> "Você vai assumir um projeto de um assistente anterior chamado Ravi. Vou te passar o documento de continuidade completo do projeto. Leia tudo com atenção e depois me confirme que entendeu antes de fazer qualquer coisa."

**Passo 3:** Cole o conteúdo deste arquivo HANDOFF.md inteiro na conversa.

**Passo 4:** Envie também o arquivo `MEMORY.md` do repositório (link: https://raw.githubusercontent.com/mauromamachado-creator/sisescala-tv/main/HANDOFF.md)

**Passo 5:** Descreva o problema ou tarefa que precisa resolver.

**Regras que a nova IA precisa seguir (lembre de mencionar):**
- Falar em português brasileiro, tom casual e direto
- Nunca mencionar nomes de modelos de IA
- Bug fixes pode fazer sozinha; mudança de regra de negócio precisa de aprovação
- Se uma fonte de dados quebrar, avisar o Mauro pelo Telegram imediatamente

---

### Cenário 3: Preciso de um desenvolvedor humano

Encaminhe este documento completo para o desenvolvedor. O projeto é tecnicamente simples:
- O site inteiro é **um único arquivo HTML** (sem frameworks complicados)
- O bot é **Python puro** com a biblioteca `python-telegram-bot`
- Os dados vêm de **planilhas Google** (sem banco de dados próprio)
- A hospedagem é **gratuita** via GitHub Pages

Um desenvolvedor júnior/pleno consegue assumir em menos de 1 dia de leitura.

---

### Cenário 4: Emergência — o site quebrou e preciso de algo no ar agora

O `index.html` funciona em qualquer lugar. Opções em ordem de facilidade:

**Opção A — Netlify (5 minutos, grátis):**
1. Baixe o arquivo `index.html` do GitHub: https://github.com/mauromamachado-creator/sisescala-tv/blob/main/index.html → clique em "Raw" → Ctrl+S para salvar
2. Acesse https://app.netlify.com/drop
3. Arraste o arquivo `index.html` para a área indicada
4. O site fica no ar na hora com uma URL nova

**Opção B — Vercel (5 minutos, grátis):**
1. Acesse https://vercel.com
2. Conecte com a conta GitHub `mauromamachado-creator`
3. Importe o repositório `sisescala-tv`
4. Clique em Deploy

**Opção C — Localmente no computador:**
1. Baixe o `index.html`
2. Abra um terminal e rode: `python3 -m http.server 8080`
3. Abra no browser: `http://localhost:8080`
4. Funciona offline (sem dados ao vivo, mas a estrutura fica visível)

---

## 🔄 PARTE 4 — MANUTENÇÃO BÁSICA

### Como publicar uma mudança no site

**Sem linha de comando** (mais fácil):
1. Acesse https://github.com/mauromamachado-creator/sisescala-tv
2. Clique no arquivo `index.html`
3. Clique no lápis (✏️ Edit)
4. Faça a mudança
5. Clique em "Commit changes"
6. Aguarde ~2 minutos — o site atualiza sozinho

**Com linha de comando** (mais rápido):
```bash
cd /tmp/sisescala-tv
git pull
# edite o index.html
git add index.html
git commit -m "descrição da mudança"
git push origin main
```

---

### Como voltar para uma versão anterior (rollback)

O sistema tem versões salvas ("checkpoints") no GitHub. Se algo quebrar:

```bash
cd /tmp/sisescala-tv
./rollback.sh
```

Versões estáveis disponíveis:
- `v5.0-stable` — estado de 09/03/2026 antes da remoção da ESCALA legacy
- `v5.1-stable` — estado de 09/03/2026 com ESCALA V2 funcionando ✅

---

### Como reiniciar o bot

Se o bot parar de responder:

```bash
# Verificar se está rodando
ps aux | grep consulta_bot

# Reiniciar
pkill -f consulta_bot.py
cd /home/node/.openclaw/workspace/sisescala
export SISGOP_BOT_TOKEN="TOKEN_DO_BOT_AQUI"
nohup python3 consulta_bot.py >> /tmp/consulta_bot.log 2>&1 &

# Ver logs
tail -f /tmp/consulta_bot.log
```

---

### Como atualizar o Google Apps Script (GAS)

Quando precisar atualizar o código dos GAS (após mudanças no repositório):

1. Abra a planilha correspondente (ver tabela de IDs acima)
2. Menu: **Extensões → Apps Script**
3. Selecione todo o código existente (Ctrl+A) e delete
4. Cole o conteúdo do arquivo `.js` correspondente do repositório
5. Salve (Ctrl+S)
6. Menu: **Implantar → Gerenciar implantações**
7. Clique no ícone de lápis (editar)
8. Em "Versão": selecione **"Nova versão"**
9. Clique em **Implantar**

| Arquivo no repositório | Planilha que deve receber |
|---|---|
| `gas_resposta_consulta_v2.js` | `1-aqNKOJcLGjZRDIfyd4hrNeLVJrcI-i9rfTii_rt2cs` |
| `gas_confirmacao.js` | `15MyzYrdwfkX2jChz-aokq2g1mMfThayBsDMx3tGlvxA` |

---

## 📂 PARTE 5 — ONDE ESTÁ CADA COISA

### No servidor OpenClaw
```
/home/node/.openclaw/workspace/
├── MEMORY.md                          ← memória do Ravi (contexto geral)
├── memory/2026-03-09.md               ← log detalhado da última sessão
├── sisescala/
│   ├── consulta_bot.py                ← código do bot Telegram
│   └── data/                          ← estado interno do bot
└── gte_bot/
    └── om_data.json                   ← Ordens de Missão cadastradas
```

### No GitHub (repositório)
```
sisescala-tv/
├── index.html                         ← TODO o frontend
├── data/om_data.json                  ← OMs (sincronizado com servidor)
├── data/conf_missao.json              ← confirmações em andamento
├── data/raio_vc1.json                 ← backup raio VC-1
├── data/raio_vc2.json                 ← backup raio VC-2
├── gas_resposta_consulta_v2.js        ← código GAS consulta
├── gas_confirmacao.js                 ← código GAS confirmação
├── deploy.sh                          ← script de publicação
├── rollback.sh                        ← script de reversão
└── HANDOFF.md                         ← este arquivo
```

---

## 🐛 PARTE 6 — PROBLEMAS COMUNS E SOLUÇÕES

| Sintoma | Causa mais provável | O que fazer |
|---|---|---|
| Site não atualiza | Cache do browser | Ctrl+Shift+R (força recarregar) |
| Site fora do ar | GitHub Pages com problema | Hospedar no Netlify (ver Cenário 4) |
| Bot não responde | Processo caiu | Reiniciar o bot (ver Parte 4) |
| ESCALA V2 em branco | GAS não respondeu | Aguardar 1 min e atualizar (↻ botão) |
| Diárias não aparecem | GAS DIÁRIAS fora | Testar: abrir URL do DIÁRIAS_API no browser |
| OM não aparece nas missões | Não está no om_data.json | Pedir a uma IA para adicionar |
| "Invalid Date" nas missões | Formato de data errado no JSON | Formato correto: `DD/MM/YY` (ex: `11/03/26`) |
| Push bloqueado no GitHub | Token expirado | Gerar novo token em github.com/settings/tokens |
| Bot parou após atualização | Erro de sintaxe no código | Ver logs: `tail -50 /tmp/consulta_bot.log` |

---

## ✅ PARTE 7 — STATUS DO SISTEMA EM 09/03/2026

### O que está funcionando bem ✅
- Dashboard principal (tripulantes, missões, METAR, alertas)
- Disponibilidade dos pilotos por VC
- Horas de voo e ranking
- Férias e alertas de tripulantes
- Calendário de missões
- Cartões individuais
- BOT interface (consulta METAR, TAF, NOTAM, aeródromo, etc.)
- Diárias (listagem, PDF, concluir, reabrir)
- Busca de tripulantes
- TV mode
- ESCALA V2 (raio + respostas por VC)
- Backups automáticos semanais (toda segunda, 10h Brasília)
- HANDOFF.md publicado

### Pendências conhecidas ⚠️
- [ ] `gas_confirmacao.js` precisa ser reimplantado pelo Mauro (ação `send_conf` ainda não ativa)
- [ ] Ação `conf_ciente` não implementada no CONSULTA_GAS
- [ ] OMs 44, 47, 49 faltam no `om_data.json` (precisam dos PDFs)
- [ ] Senha do S3 não trocada para o valor desejado
- [ ] Token do bot ainda tem fallback hardcoded no código (funciona, não é urgente)

---

## 📞 PARTE 8 — CONTATOS

**Mauro Machado** (dono do projeto)
- Telegram: `@machadommam`
- chat_id Telegram: `673591486`
- Telefone: +55 21 99524-2702

**Ravi Lemos 🦀** (assistente IA anterior)
- Plataforma: OpenClaw (https://openclaw.ai)
- Conta vinculada ao Mauro

---

*Documento criado em: 09/03/2026*
*Versão do sistema: v5.1-stable*
*Escrito por: Ravi Lemos 🦀*
*"Espero que nunca precisem ler isso até o fim."*
