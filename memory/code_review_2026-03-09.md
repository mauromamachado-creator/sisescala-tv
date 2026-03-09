# Code Review — SisGOPA / consulta_bot.py + index.html (JS)
**Data:** 2026-03-09  
**Revisor:** Ravi (subagent)  
**Arquivos analisados:**
- `/home/node/.openclaw/workspace/sisescala/consulta_bot.py`
- `/home/node/.openclaw/workspace/sisescala/index.html` (apenas o JavaScript)

---

## 1. BUGS CONFIRMADOS OU POTENCIAIS

### consulta_bot.py

#### BUG-1: `action == "allyes"` atribui prioridade 1 para todas as missões (L652–656)
```python
for m in missions:
    recipient["responses"][m] = 1  # TODAS ficam com prioridade 1
```
O sistema de prioridade do resto do código usa valores sequenciais (1, 2, 3...) para indicar ordem de preferência. O botão "FULL DISP" define todas as missões como prioridade 1, colapsando a distinção. Se o tripulante depois usar `toggle` para ajustar, a reordenação parte de uma base inválida (todos em empate). **Comportamento ambíguo para o escalante.**

#### BUG-2: `check_deadlines` recebe `app` como parâmetro mas nunca o usa (L1059)
```python
async def check_deadlines(app):
```
O parâmetro `app` é inútil — a função nunca o referencia. Pior: ao ser criada com `asyncio.create_task(check_deadlines(app))` (L1109), a task é iniciada passando `app` como coroutine, e o objeto `app` do Telegram ainda não está inicializado nesse ponto (a inicialização acontece na linha seguinte). Apesar de não causar crash imediato (a função não usa `app`), a ordem lógica está errada e pode causar problemas se a função for alterada para usar `app` no futuro.

#### BUG-3: `raio_vc` callback não remove arquivo PDF temporário em caso de erro (L476–508)
Em `raio_handler` (o handler direto), o `pdf_path.unlink(missing_ok=True)` está no final do `try`. Já no callback `raio_vc`, após extrair texto com pypdf, o unlink é feito antes do parsing (`pdf_path.unlink(missing_ok=True)` na L487), mas se ocorrer exceção antes disso, o arquivo temporário fica no disco. Inconsistência de cleanup.

#### BUG-4: `_sync_response_to_sheet` faz commit antes de pull/rebase (L142–159)
```python
subprocess.run(["git", "commit", "-m", ...])       # commit local
subprocess.run(["git", "pull", "--rebase", ...])   # pull depois
subprocess.run(["git", "push", ...])               # push
```
A ordem correta seria: `pull --rebase` → `commit` → `push`. Com a ordem atual, se houver alteração remota entre o commit local e o pull, o rebase pode falhar ou criar conflito de histórico. Em ambiente de uso contínuo com múltiplos tripulantes respondendo simultaneamente, isso pode resultar em perda de sincronização silenciosa.

#### BUG-5: Auto-adicionar recipient sem nenhum controle de autorização (L601–610)
```python
# Auto-adicionar tripulante como recipient
recipient = {
    "chat_id": user_id,
    "name": ...,
    ...
}
consulta["recipients"].append(recipient)
```
Qualquer pessoa que tenha acesso à mensagem do bot (encaminhamento, grupo, etc.) e clique no botão de callback se torna automaticamente um recipient com direito de voto. Não há verificação se o `user_id` está na lista de destinatários originais da consulta.

#### BUG-6 (index.html): `renderScreenSearch` — `const inp` declarada duas vezes no mesmo escopo funcional (L2050–2052)
```javascript
container.innerHTML = html;
const _inp = document.getElementById('searchInput'); // L2050
...
const inp = document.getElementById('searchInput'); // L2052
```
Ambas fazem a mesma coisa. Além de código redundante, `_inp` e `inp` são duas declarações separadas para o mesmo elemento. Em retornos antecipados (L1909 e L1933), usa-se `inp` e `_inp` respectivamente mas ao final do fluxo principal ambas existem no mesmo escopo. Não é um `SyntaxError` porque os nomes são diferentes, mas é lógica duplicada desnecessária e confusa.

#### BUG-7 (index.html): `parseACNT` — `lastDataRowIdx` definida mas nunca lida (L1636, L1643)
```javascript
let lastDataRowIdx = -1;
...
if(name.includes('%') || status.includes('%')){ lastDataRowIdx = r; continue; }
```
`lastDataRowIdx` é atribuída dentro do loop mas nunca é utilizada fora dele. A intenção parece ser identificar a linha de percentagem para leitura posterior, mas o código ao final do bloco usa `rows[rows.length-1]` diretamente, ignorando `lastDataRowIdx`. Variável orphan.

#### BUG-8 (index.html): Ano hardcoded "2026" no painel TV (aprox. L2340)
```javascript
html += `<div ...>Total de Horas Voadas - 2026</div>`;
```
Imediatamente acima existe `const currentYear = td.getFullYear()`, mas o texto do painel TV usa o literal `"2026"` em vez de `currentYear`. O painel ficará desatualizado em 2027.

---

## 2. CÓDIGO SOLTO / SEM USO / ORPHAN

### consulta_bot.py

#### ORPHAN-1: `GAS_URL` definida mas nunca usada (L57)
```python
GAS_URL = "https://script.google.com/macros/s/AKfycbz..."
```
Definida no início do arquivo, nunca referenciada em nenhuma função. Código morto.

#### ORPHAN-2: `motivo` em `_sync_response_to_sheet` nunca utilizado (L124)
```python
async def _sync_response_to_sheet(vc_key: str, name: str, responses: dict, motivo: str = ""):
```
O parâmetro `motivo` é aceito (e passado em algumas chamadas: `motivo="arquivado"`), mas o corpo da função nunca o referencia. Parâmetro inútil.

#### ORPHAN-3: `action == "reset"` sem botão correspondente no teclado (L663–665)
```python
elif action == "reset":
    recipient["responses"] = {}
```
O código trata o callback `reset`, e a mensagem para o usuário menciona "🔄 LIMPAR = recomeçar", mas `_build_keyboard` (L262–294) não cria nenhum botão com `callback_data` contendo `"reset"`. A ação é inalcançável pelo usuário.

#### ORPHAN-4: `parse_consulta_message` retorna campos nunca consumidos
Os campos `"tipo"` e `"observacoes"` do retorno de `parse_consulta_message` são calculados e retornados, mas em `api_post_consulta → create`, apenas `"missoes"` do resultado parsed é acessado. Os outros campos são armazenados no JSON mas nunca lidos pela lógica do bot.

#### ORPHAN-5: `_raio_pending` sem expiração/limpeza (L56)
```python
_raio_pending: dict = {}  # {"u{user_id}": file_id}
```
Entradas são adicionadas quando um PDF é recebido sem caption e removidas apenas quando o callback `raio_vc` é chamado com `pop`. Se o usuário nunca clicar nos botões VC-1/VC-2, a entrada fica para sempre em memória. Em uso prolongado, leak de memória lento.

### index.html (JS)

#### ORPHAN-6: `started` em `parseChecklist` definida mas nunca alterada (L1705)
```javascript
let started = false;
// never set to true inside parseChecklist
```
Em outra função de parsing (parseFérias), `started` é usado corretamente com a lógica de header. Em `parseChecklist`, a variável existe mas nunca muda de valor — o loop usa `if(r<3)continue` diretamente, tornando `started` inútil.

---

## 3. QUEBRA DE PADRÃO / INCONSISTÊNCIAS DE NOMENCLATURA E ESTILO

### consulta_bot.py

#### ESTILO-1: Código duplicado integralmente — lógica de parsing de PDF do raio (L357–404 vs L471–510)
O bloco de extração de texto do PDF e parsing de pilotos (`POSTOS`, regex, loop de linhas) existe quase idêntico em dois lugares: dentro de `raio_handler` e dentro do bloco `if action == "raio_vc":` do `callback_handler`. Violação grave do princípio DRY. Qualquer correção no parser precisa ser feita nos dois lugares.

#### ESTILO-2: `import subprocess` duplicado (L16 e dentro de funções)
`subprocess` é importado no topo do arquivo (L16), mas é reimportado localmente dentro de `_backup_consulta_arquivada`, `_sync_response_to_sheet`, e no bloco `raio_vc` (`import subprocess as _sp`). Desnecessário e inconsistente.

#### ESTILO-3: `import pypdf` feito dentro de funções em vez de no topo
`pypdf` é importado como `import pypdf as _pypdf` dentro do `try` de `raio_handler` e como `import pypdf as _pypdf2` dentro do callback. Deveria ser importado no topo do arquivo como todos os outros módulos.

#### ESTILO-4: `vc_key_found = _resolved_vc` (L594) — alias desnecessário
Duas variáveis para o mesmo valor: `_resolved_vc` e `vc_key_found`. Ambas são usadas em partes diferentes do mesmo bloco, sem razão para terem nomes diferentes.

#### ESTILO-5: `int(chat_id)` vs `int(chat_id) if str(chat_id).isdigit() else chat_id` — validação inconsistente
Em `api_post_consulta → create`, o envio bem-sucedido usa `int(chat_id)` sem guard, mas o fallback em caso de erro usa a versão com verificação. Se `chat_id` vier como string não-numérica do frontend, a linha de sucesso levantaria `ValueError`.

#### ESTILO-6: `update_saviso` e `update_escalados` são idênticas (L917–940)
Dois endpoints com nomes diferentes que executam exatamente o mesmo código: `m["escalados"] = escalados`. Deveriam ser unificados.

### index.html (JS)

#### ESTILO-7: Código JavaScript extremamente comprimido (minificado manual)
Grande parte do JS está escrita em linhas longuíssimas com múltiplas declarações separadas por `;` na mesma linha, sem indentação consistente. Mistura de estilo minificado com trechos mais legíveis. Dificulta manutenção e revisão.

#### ESTILO-8: `calYear`/`calMonth` como globais via IIFE (aprox. L1760)
```javascript
let calYear, calMonth;
(function(){ const t = nowBRT(); calYear = t.getFullYear(); calMonth = t.getMonth(); })();
```
Padrão diferente de como outras variáveis globais são declaradas no restante do código.

---

## 4. PROBLEMAS DE SEGURANÇA

### consulta_bot.py

#### SEC-1: `BOT_TOKEN` hardcoded no código-fonte (L48)
```python
BOT_TOKEN = "8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU"
```
**CRÍTICO.** O token do bot Telegram está exposto diretamente no código. Qualquer pessoa com acesso ao repositório pode assumir controle do bot, enviar mensagens em nome dele, ou revogar o token. Deve ser carregado via variável de ambiente (`os.environ["BOT_TOKEN"]`) ou arquivo de configuração fora do repositório.

#### SEC-2: API HTTP local sem autenticação (L779–786)
```python
app.router.add_post("/api/consulta", api_post_consulta)
```
A API aceita POST de qualquer origem sem nenhum token, chave de API ou verificação de origem. Qualquer processo no mesmo host pode criar consultas, arquivar resultados, ou disparar mensagens Telegram para tripulantes. O middleware CORS com `*` amplifica o problema ao permitir requisições de qualquer site.

#### SEC-3: `GAS_URL` exposta no código-fonte (L57)
URL de Google Apps Script exposta, embora aparentemente não seja mais usada. Caso seja reativada sem controle de segurança, qualquer requisição para o endpoint pode ser manipulada.

#### SEC-4: Busca parcial de nome para envio de confirmação (L992–998)
```python
for key, cid in recipients_map.items():
    if nome_upper in key or key in nome_upper:
        chat_id = cid
        break
```
Lógica de fallback por substring pode causar envio de confirmação de missão para a pessoa errada, se houver nomes parcialmente similares (ex: "SILVA" encontra "SILVA PEREIRA" e "SILVA SANTOS" — pega o primeiro). Risco operacional relevante em contexto militar.

### index.html (JS)

#### SEC-5: XSS via interpolação direta de dados externos (múltiplos locais)
Em vários pontos do JavaScript, dados vindos de planilhas Google Sheets (via CSV/JSON) são inseridos diretamente em HTML via template literals sem sanitização:
- `onclick="showOMDetail('${om.om}')"` — em `renderOMsNaBusca`
- `title="${ev.text}"` — em `renderScreenCalendar`
- `${data.consulta.replace(/</g,'&lt;')}` — sanitização parcial (só `<`, não sanitiza `>`, `'`, `"`, `&`)

Se um dado malicioso for inserido na planilha de origem, pode executar código arbitrário no navegador dos usuários.

#### SEC-6: `renderScreenSearch` escapa apenas aspas duplas no valor do input
```javascript
value="${(query||'').replace(/"/g,'&quot;')}"
```
Apenas `"` é escapado. Caracteres como `<`, `>`, `'` não são tratados.

---

## 5. LÓGICA SUSPEITA OU FRÁGIL

### consulta_bot.py

#### FRAGIL-1: Detecção de "nova consulta" por `message_id` é frágil (L555–574)
A lógica compara o `message_id` atual com o armazenado para detectar se uma consulta nova foi enviada. Se o bot reiniciar, o `stored_msg_id` é perdido (não é persistido no JSON inicialmente — só é salvo após o primeiro callback). Entre reinicializações, o primeiro callback sempre parecerá ser de uma mensagem nova, resetando respostas já existentes.

**Nota:** O `message_id` SÓ é salvo ao `_save_data` no bloco `elif current_msg_id and not stored_msg_id:` — mas antes disso, o check `if current_msg_id and stored_msg_id and current_msg_id != stored_msg_id:` já avalia e pode resetar, mesmo com `stored_msg_id = None` (pois `None and ...` é falso). A lógica é correta nesse ponto específico, mas depende de condições de timing durante reinício.

#### FRAGIL-2: `check_deadlines` não notifica usuários ao encerrar prazo (L1059–1079)
Quando o prazo expira, a consulta é silenciosamente marcada como `locked`. Os tripulantes que ainda não responderam não recebem nenhuma notificação. Eles simplesmente verão a mensagem de "consulta encerrada" na próxima vez que clicarem.

#### FRAGIL-3: `_raio_pending` usa `f"u{user_id}"` como chave para cache de VC
Se dois escalantes autorizados enviarem PDF simultaneamente sem caption, as entradas no dict não colidirão (user_id diferente), mas a arquitetura não é thread-safe em caso de uso assíncrono simultâneo do mesmo `user_id`. Improvável em produção dado que `ESCALANTES_AUTORIZADOS` tem apenas um membro, mas frágil por design.

### index.html (JS)

#### FRAGIL-4: `parseACNT` assume `rows[rows.length-1]` como linha de percentagem (L1651–1658)
```javascript
const lastRow = rows[rows.length - 1] || [];
```
Sempre usa a última linha da planilha inteira para extrair percentagens, independente do layout. Se a planilha tiver linhas em branco ao final, dados de rodapé, ou novas missões adicionadas, os percentuais serão lidos da linha errada.

#### FRAGIL-5: Loop de datas com mutação de objeto Date (em `renderScreenCalendar`)
```javascript
for(let d = new Date(sd); d <= ed; d.setDate(d.getDate() + 1))
```
`d.setDate()` muta o objeto `d` em vez de criar um novo. Em torno de mudanças de horário de verão (DST), isso pode produzir datas puladas ou duplicadas, pois `setDate` não garante comportamento consistente com fusos horários.

#### FRAGIL-6: `getOMsForCrew` — match parcial de nome com mínimo de 3 caracteres
```javascript
if(nomeUp.includes(tNome) && tNome.length >= 3) return true;
```
Nomes curtos (3 caracteres) como "ANA" podem produzir falsos positivos em buscas mais amplas.

#### FRAGIL-7: `feriasData` em `renderScreenSearch` — comparação direta `f.fim < td`
Em `renderScreenSearch`, a filtragem de férias usa `f.fim < td` onde `td` é um objeto `Date` e `f.fim` parece ser também um `Date` (vindo de `parseDateBR`). A comparação funciona se ambos forem objetos Date, mas é dependente do tipo — se em alguma refatoração `f.fim` voltar a ser string ISO, a comparação será incorreta silenciosamente (string < Date produz `false` por coerção inesperada).

---

## 6. TODOs / FIXMEs NÃO RESOLVIDOS

Não foram encontrados comentários `TODO`, `FIXME`, `HACK` ou `XXX` explícitos em nenhum dos arquivos.

Há, contudo, comentários que indicam intenções incompletas:

#### PENDENTE-1 (consulta_bot.py, em torno de L695)
No texto enviado ao usuário no estado não-confirmado:
```python
"🔄 LIMPAR = recomeçar"
```
O texto menciona uma ação "LIMPAR", mas o botão correspondente nunca é adicionado ao teclado em `_build_keyboard`. A funcionalidade foi planejada (existe handler `action == "reset"`) mas nunca foi exposta ao usuário.

#### PENDENTE-2 (index.html, L~2220)
```javascript
// Note: row 3 panels use overflow-y:auto individually
```
Comentário de design que sugere uma decisão de layout pendente de validação ou implementação uniforme.

---

## RESUMO EXECUTIVO

| Categoria | Quantidade | Severidade máxima |
|---|---|---|
| Bugs confirmados / potenciais | 8 | Alta |
| Código orphan / sem uso | 6 | Baixa |
| Inconsistências de estilo | 8 | Média |
| Segurança | 6 | **Crítica** (BOT_TOKEN) |
| Lógica frágil | 7 | Média |
| TODOs não resolvidos | 2 | Baixa |

**Prioridade imediata:** SEC-1 (token exposto), SEC-2 (API sem auth), BUG-5 (qualquer pessoa pode votar), BUG-4 (race condition no git sync).
