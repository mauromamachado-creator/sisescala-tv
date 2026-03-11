#!/usr/bin/env python3
"""
SISGOP BOT v3 — Bot mínimo de consulta de escala de voo.

Funções:
  - /start: boas-vindas
  - Callbacks inline: toggle missão, INDISPONÍVEL TODAS, CONFIRMAR RESPOSTA, CIENTE
  - Mini API HTTP (porta 8085) para o SisGOPA gerenciar consultas

O SisGOPA (index.html) faz TUDO: criar, acompanhar, encerrar, enviar confirmações.
O bot só recebe respostas dos tripulantes via botões inline.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ─── Instalar aiohttp se necessário ──────────────────────────────────────────
try:
    from aiohttp import web
    from aiohttp.web import middleware
except ImportError:
    print("[SISGOP] Instalando aiohttp...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
    from aiohttp import web
    from aiohttp.web import middleware

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

# ─── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("SISGOP_BOT_TOKEN") or "8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU"
TELEFONE_CONTATO = "Escala GTE-1: (61) 99965-5801"

# ─── Escalantes autorizados a enviar raio e consultas ─────────────────────────
# Para adicionar: incluir chat_id e nome do escalante
ESCALANTES_AUTORIZADOS = {
    673591486: "MJ MACHADO",   # Mauro Machado (admin)
    1022713803: "MJ OSVALDO",  # MJ Osvaldo
    827091454: "CP BARCELOS",  # Escala GTE-1
}
GAS_URL = "https://script.google.com/macros/s/AKfycbyDdqWqCKLoCVwgajS3kr4o6q2MHx3UYxwe2o-28JbFCS__NhV2l2OqFlUT-cyRu-Vg/exec"
API_PORT = 8085
API_SECRET = os.environ.get("SISGOP_API_SECRET", "sisgopa-gte-2026")

DATA_DIR = Path(__file__).parent / "data"

# Cache temporário de file_ids pendentes de confirmação de VC
_raio_pending: dict = {}  # {"u{user_id}": file_id}
DATA_FILE = DATA_DIR / "consultas.json"

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("SISGOP")

# ─── Meses em português (usado pelo parser) ──────────────────────────────────
MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers de dados (JSON)
# ═══════════════════════════════════════════════════════════════════════════════

def _load_data() -> dict:
    """Carrega JSON: {vc1: null|consulta, vc2: null|consulta, archive: []}"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Migração de formato antigo
        if "consultas" in data and "vc1" not in data:
            return {"vc1": None, "vc2": None, "archive": data.get("consultas", [])}
        return data
    return {"vc1": None, "vc2": None, "archive": []}


def _save_data(data: dict):
    """Salva dados no JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def _backup_consulta_arquivada(consulta: dict):
    """Salva backup JSON da consulta arquivada no GitHub para auditoria futura."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        vc = consulta.get("vc_type", "vc?")
        filename = f"data/historico/consulta_{vc}_{ts}.json"
        filepath = DATA_DIR.parent / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(consulta, f, ensure_ascii=False, indent=2)
        import subprocess
        subprocess.run(["git", "add", str(filepath)], cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", f"backup: consulta {vc} arquivada {ts}"],
                       cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=str(DATA_DIR.parent), capture_output=True, timeout=30)
        logger.info("Backup consulta arquivada: %s", filename)
    except Exception as e:
        logger.error("Erro backup consulta: %s", e)

_gas_lock_cache: dict = {}  # {vc_key: (locked: bool, timestamp: float)}
_gas_consulta_cache: dict = {}  # {vc_key: (consulta: dict, timestamp: float)}

async def _gas_is_locked(vc_key: str) -> bool:
    """Consulta GAS se a consulta está encerrada. Cache de 30s."""
    import time
    cached = _gas_lock_cache.get(vc_key)
    if cached and (time.time() - cached[1]) < 30:
        return cached[0]
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(GAS_URL, params={"action": "get"}, follow_redirects=True)
        result = r.json()
        key = "locked_vc1" if vc_key == "vc1" else "locked_vc2"
        locked = bool(result.get(key, False))
        _gas_lock_cache[vc_key] = (locked, time.time())
        return locked
    except Exception:
        return False  # Em caso de erro, não bloqueia


async def _gas_get_consulta(vc_key: str) -> dict | None:
    """Busca dados da consulta no GAS (missões, texto, recipients). Cache 60s."""
    import time
    cached = _gas_consulta_cache.get(vc_key)
    if cached and (time.time() - cached[1]) < 60:
        return cached[0]
    try:
        import httpx
        vc_param = "vc1" if vc_key == "vc1" else "vc2"
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(GAS_URL, params={"action": "get_consulta", "vc": vc_param}, follow_redirects=True)
        result = r.json()
        if result.get("ok") and result.get("consulta"):
            consulta = result["consulta"]
            _gas_consulta_cache[vc_key] = (consulta, time.time())
            return consulta
    except Exception as e:
        logger.warning("_gas_get_consulta erro: %s", e)
    return None


async def _save_response_to_gas(vc_key: str, name: str, responses: dict):
    """Salva resposta confirmada na planilha via GAS (ação save_response)."""
    try:
        import httpx
        vc_sheet = "VC-1" if vc_key == "vc1" else "VC-2"
        respostas_str = json.dumps(responses, ensure_ascii=False)
        payload = {
            "action": "save_response",
            "vc": vc_sheet,
            "nome_guerra": name.upper(),
            "respostas": respostas_str,
            "confirmado": True,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(GAS_URL, json=payload, follow_redirects=True)
        resp = r.json() if r.status_code == 200 else {}
        logger.info("GAS save_response: %s %s → %s", vc_sheet, name, resp)
    except Exception as e:
        logger.error("Erro GAS save_response: %s", e)


async def _sync_response_to_sheet(vc_key: str, name: str, responses: dict, motivo: str = ""):
    """Sincroniza respostas publicando JSON no GitHub (raw) pra SisGOPA ler."""
    try:
        data = _load_data()
        # Gerar JSON público com respostas de ambas as consultas
        pub = {}
        for vk in ("vc1", "vc2"):
            c = data.get(vk)
            if c:
                pub[vk] = {
                    "id": c.get("id"),
                    "text": c.get("text", ""),
                    "missions": c.get("missions", []),
                    "locked": c.get("locked", False),
                    "recipients": [
                        {
                            "name": r.get("name"),
                            "responses": r.get("responses", {}),
                            "confirmed": r.get("confirmed", False),
                        }
                        for r in c.get("recipients", [])
                    ],
                }
        pub_path = DATA_DIR / "respostas_pub.json"
        with open(pub_path, "w", encoding="utf-8") as f:
            json.dump(pub, f, ensure_ascii=False, indent=2)
        # Git push (com pull --rebase antes para evitar conflito)
        import subprocess
        subprocess.run(
            ["git", "add", "data/respostas_pub.json"],
            cwd=str(DATA_DIR.parent), capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "commit", "-m", f"auto: resposta {name}"],
            cwd=str(DATA_DIR.parent), capture_output=True, timeout=10,
        )
        # Rebase remoto antes de push para evitar rejeição
        subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            cwd=str(DATA_DIR.parent), capture_output=True, timeout=30,
        )
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=str(DATA_DIR.parent), capture_output=True, timeout=30,
        )
        logger.info("GitHub sync: %s (rc=%d)", name, result.returncode)
    except Exception as e:
        logger.error("Erro sync GitHub: %s", e)


def _vc_display(vc_key: str) -> str:
    """vc1 -> VC-1, vc2 -> VC-2"""
    return "VC-1" if vc_key == "vc1" else "VC-2"


# ═══════════════════════════════════════════════════════════════════════════════
# Parser de mensagem de consulta
# ═══════════════════════════════════════════════════════════════════════════════

def parse_consulta_message(text: str) -> dict:
    """
    Extrai dados de uma mensagem de consulta colada pelo escalante.
    Retorna dict com: tipo, datas, missoes (lista de dicts), observacoes
    """
    result = {
        "tipo": None,
        "datas": [],
        "missoes": [],
        "observacoes": "",
        "texto_original": text,
    }

    # Tipo VC-1 ou VC-2
    vc_match = re.search(r'VC[-\s]?([12])', text, re.IGNORECASE)
    if vc_match:
        result["tipo"] = f"VC-{vc_match.group(1)}"

    # Datas: "dia 04 de março" ou "dias 08 e 09 de março"
    date_match = re.search(
        r'dias?\s+([\d]+(?:\s*[,e]\s*\d+)*)\s+de\s+(\w+)',
        text, re.IGNORECASE
    )
    if date_match:
        dias_str = date_match.group(1)
        mes_nome = date_match.group(2).lower().strip()
        mes_num = MESES.get(mes_nome, 0)
        ano = datetime.now().year
        dias = re.findall(r'\d+', dias_str)
        for d in dias:
            try:
                result["datas"].append(f"{int(d):02d}/{mes_num:02d}/{ano}")
            except ValueError:
                pass

    # Missões: "A)" seguido de descrição
    missao_pattern = re.compile(
        r'([A-Z])\s*\)\s*(.*?)(?=\n[A-Z]\s*\)|$)',
        re.DOTALL
    )
    for m in missao_pattern.finditer(text):
        letra = m.group(1)
        descricao = m.group(2).strip()
        missao = {
            "letra": letra,
            "descricao": descricao,
            "trechos": [],
            "is_saviso": False,
            "escalados": [],
            "om": None,
            "cientes": [],
        }
        if re.search(r'SAVISO', descricao, re.IGNORECASE):
            missao["is_saviso"] = True
            dia_semana = re.search(r'SAVISO\s+(\w+)', descricao, re.IGNORECASE)
            if dia_semana:
                missao["saviso_dia"] = dia_semana.group(1)
        else:
            trecho_lines = [l.strip() for l in descricao.split('\n') if l.strip()]
            missao["trechos"] = trecho_lines
        result["missoes"].append(missao)

    # Observações
    obs_match = re.search(r'OBS[:\s]+(.*?)$', text, re.IGNORECASE | re.DOTALL)
    if obs_match:
        result["observacoes"] = obs_match.group(1).strip()

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Construtores de teclado inline
# ═══════════════════════════════════════════════════════════════════════════════

PRIO_EMOJIS = {0: "❌", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"}

def _build_keyboard(consulta_id: str, missions: list[str], responses: dict, confirmed: bool = False) -> InlineKeyboardMarkup:
    """Monta teclado inline com botões de missão.
    responses[m] = int: 0=indisponível, 1+=prioridade, None=pendente
    Ordem de clique define prioridade automaticamente.
    """
    # Quando confirmado: só botão de editar (limpo)
    if confirmed:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ ALTERAR RESPOSTA", callback_data=f"alterar|{consulta_id}"),
        ]])

    buttons = []
    row = []
    for m in missions:
        prio = responses.get(m)
        if prio is None:
            label = f"⬜ {m}"
        elif prio == 0:
            label = f"❌ {m}"
        else:
            emoji = PRIO_EMOJIS.get(prio, f"#{prio}")
            label = f"{emoji} {m}"
        row.append(InlineKeyboardButton(label, callback_data=f"toggle|{consulta_id}|{m}"))
        if len(row) >= 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("✅ DISPONÍVEL TODAS", callback_data=f"allyes|{consulta_id}")])
    buttons.append([InlineKeyboardButton("❌ INDISPONÍVEL TODAS", callback_data=f"allno|{consulta_id}")])
    buttons.append([
        InlineKeyboardButton("📨 CONFIRMAR", callback_data=f"confirm|{consulta_id}"),
    ])
    return InlineKeyboardMarkup(buttons)


def _build_ciente_keyboard(consulta_id: str, missao_letra: str) -> InlineKeyboardMarkup:
    """Botão CIENTE para tripulante escalado."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "✅ CIENTE",
            callback_data=f"ciente|{consulta_id}|{missao_letra}"
        )
    ]])


# ═══════════════════════════════════════════════════════════════════════════════
# /start — Boas-vindas
# ═══════════════════════════════════════════════════════════════════════════════

async def raio_handler(update: Update, context):
    """Recebe PDF do raio enviado por escalante autorizado e atualiza GitHub."""
    user_id = update.effective_user.id
    if user_id not in ESCALANTES_AUTORIZADOS:
        await update.message.reply_text("⛔ Você não tem autorização para enviar o raio.")
        return

    # Detectar VC pelo caption: "/raio vc1" ou "/raio vc2"
    caption = (update.message.caption or "").strip().lower()
    logger.info("Raio recebido — caption: %r", caption)

    if re.search(r'vc[-\s]?2\b', caption):
        vc = "vc2"
    elif re.search(r'vc[-\s]?1\b', caption):
        vc = "vc1"
    else:
        # Sem caption — guardar file_id em memória e perguntar com botões
        _raio_pending[f"u{user_id}"] = update.message.document.file_id
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔵 Raio VC-1", callback_data=f"raio_vc|vc1|u{user_id}"),
                InlineKeyboardButton("🟢 Raio VC-2", callback_data=f"raio_vc|vc2|u{user_id}"),
            ],
            [
                InlineKeyboardButton("📋 Controlão", callback_data=f"pdf_tipo|controlao|pdf_{user_id}"),
            ],
        ])
        await update.message.reply_text("📄 PDF recebido! O que é esse arquivo?", reply_markup=keyboard)
        return

    await update.message.reply_text(f"📄 Processando raio {vc.upper()}...")

    try:
        # Baixar o PDF
        file = await context.bot.get_file(update.message.document.file_id)
        pdf_path = DATA_DIR / f"raio_{vc}_temp.pdf"
        await file.download_to_drive(str(pdf_path))

        # Extrair texto do PDF diretamente com pypdf
        import pypdf as _pypdf
        try:
            _reader = _pypdf.PdfReader(str(pdf_path))
            texto = "\n".join(
                p.extract_text() for p in _reader.pages if p.extract_text()
            )
        except Exception as _epdf:
            logger.error("pypdf erro: %s", _epdf)
            texto = ""

        if not texto.strip():
            await update.message.reply_text("❌ Não consegui extrair texto do PDF.")
            return

        # Parser: cada linha começa com número e contém data DD/MM/YYYY
        # Extrai posto e nome antes do qualificador (IN, 1P, etc.)
        POSTOS = ["TEN-BRIG", "MAJ-BRIG", "BRIG", "CEL", "TC", "MJ", "CP", "1T", "2T", "ST", "CB", "SD"]
        pilotos = []
        for linha in texto.split("\n"):
            linha = linha.strip()
            # Linha de piloto: começa com número e tem data no meio
            m = re.match(r'^(\d+)(.+?)\s+\d{2}/\d{2}/\d{4}', linha)
            if not m:
                continue
            pos = int(m.group(1))
            trecho = m.group(2).strip()
            # Extrai posto + nome (palavras em maiúsculas consecutivas após o posto)
            m2 = re.match(r'^((?:' + '|'.join(POSTOS) + r')\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜÇ]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜÇ]+)*)', trecho)
            if m2:
                nome_completo = m2.group(1).strip()
                partes = nome_completo.split(None, 1)
                posto = partes[0]
                nome = partes[1].strip() if len(partes) > 1 else ""
                pilotos.append({"pos": pos, "posto": posto, "nome": nome})

        if not pilotos:
            await update.message.reply_text("❌ Não encontrei pilotos no PDF. Verifique o formato.")
            return

        # Salvar raio JSON
        from datetime import datetime
        raio = {
            "vc": vc,
            "data_consulta": datetime.now().strftime("%Y-%m-%d"),
            "gerado_em": datetime.now().isoformat(),
            "enviado_por": ESCALANTES_AUTORIZADOS[user_id],
            "pilotos": pilotos
        }
        raio_path = DATA_DIR / f"raio_{vc}.json"
        with open(raio_path, "w", encoding="utf-8") as f:
            json.dump(raio, f, ensure_ascii=False, indent=2)

        # Git push
        import subprocess
        subprocess.run(["git", "add", f"data/raio_{vc}.json"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", f"raio: {vc.upper()} atualizado por {ESCALANTES_AUTORIZADOS[user_id]}"],
                       cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=30)

        nomes_lista = "\n".join([f"{p['pos']}. {p['posto']} {p['nome']}" for p in pilotos])
        await update.message.reply_text(
            f"✅ Raio {vc.upper()} atualizado! {len(pilotos)} pilotos:\n\n{nomes_lista}\n\nJá aparece no ESCALA V2."
        )
        pdf_path.unlink(missing_ok=True)

    except Exception as e:
        logger.error("Erro raio_handler: %s", e)
        await update.message.reply_text(f"❌ Erro ao processar PDF: {e}")


async def _register_tripulante(chat_id: int, tg_name: str, nome_guerra: str, posto: str = "", vc: str = ""):
    """Cadastra ou atualiza o tripulante na aba Tripulantes do GAS."""
    try:
        import httpx
        payload = {
            "action": "register",
            "chat_id": str(chat_id),
            "tg_name": tg_name,
            "posto": posto.upper().strip(),
            "nome_guerra": nome_guerra.upper().strip(),
            "vc": vc,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(GAS_URL, json=payload, follow_redirects=True)
        logger.info("Tripulante cadastrado no GAS: %s (%s) — %s", nome_guerra, chat_id, r.status_code)
    except Exception as e:
        logger.warning("Falha ao cadastrar tripulante no GAS: %s", e)


# Dicionário temporário para armazenar quem está em processo de cadastro
_aguardando_nome: dict = {}  # {chat_id: True}


async def cmd_start(update: Update, context):
    user = update.effective_user
    _aguardando_nome[user.id] = True
    await update.message.reply_text(
        "🛩️ *SISGOP BOT — Consulta de Escala*\n\n"
        "Para se cadastrar, digite seu *nome de guerra* (ex: SAMPAIO):",
        parse_mode="Markdown",
    )


async def _lookup_dados_tripulante(nome_guerra: str):
    """Busca posto e vc na aba dados tripulantes pelo nome de guerra."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(GAS_URL, params={"action": "get_dados_tripulantes"}, follow_redirects=True)
        lista = r.json().get("tripulantes", [])
        nome_up = nome_guerra.strip().upper()
        for t in lista:
            if t.get("nome_guerra", "").upper() == nome_up or t.get("trigrama", "").upper() == nome_up:
                return t.get("posto", ""), t.get("vc", "")
    except Exception as e:
        logger.warning("Erro lookup dados tripulante: %s", e)
    return "", ""


async def msg_handler(update: Update, context):
    """Recebe nome de guerra no cadastro inicial."""
    user = update.effective_user
    if user.id not in _aguardando_nome:
        return
    nome = update.message.text.strip().upper()
    if len(nome) < 2:
        await update.message.reply_text("Nome muito curto. Digite seu nome de guerra:")
        return
    del _aguardando_nome[user.id]

    # Busca posto e vc na aba dados tripulantes
    posto, vc = await _lookup_dados_tripulante(nome)

    await _register_tripulante(user.id, user.full_name or user.username or "", nome, posto=posto, vc=vc)

    nome_completo = f"{posto} {nome}".strip() if posto else nome
    vc_txt = f" — {vc}" if vc else ""
    await update.message.reply_text(
        f"✅ *{nome_completo}*{vc_txt} cadastrado com sucesso!\n\n"
        "Quando receber uma consulta, use os botões para responder.\n\n"
        f"Dúvidas: {TELEFONE_CONTATO}",
        parse_mode="Markdown",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Callback handler — Botões inline (toggle, allno, confirm, ciente)
# ═══════════════════════════════════════════════════════════════════════════════

async def callback_handler(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    logger.info("CALLBACK RECEBIDO: data=%s user=%s", query.data, user_id)

    parts = query.data.split("|")
    action = parts[0]

    # Feedback imediato — toast visível por 2s (exceto para ações com show_alert)
    _consulta_actions = {"toggle", "allyes", "allno", "confirm", "alterar", "reset"}
    if action in _consulta_actions:
        _feedback = {
            "toggle": "⏳ Processando...",
            "allyes": "⏳ Processando...",
            "allno": "⏳ Processando...",
            "confirm": "⏳ Confirmando...",
            "alterar": "⏳ Processando...",
            "reset": "⏳ Processando...",
        }
        await query.answer(_feedback.get(action, "⏳"))

    # ─── PDF_TIPO: controlão ──────────────────────────────────────────────
    if action == "pdf_tipo":
        if user_id not in ESCALANTES_AUTORIZADOS:
            await query.answer("⛔ Não autorizado.", show_alert=True)
            return
        tipo = parts[1]   # "controlao"
        cache_key = parts[2]  # "pdf_{user_id}"
        file_id = _raio_pending.pop(f"u{user_id}", None)
        if not file_id:
            await query.edit_message_text("❌ PDF expirou. Manda o arquivo de novo.")
            return
        if tipo == "controlao":
            await query.edit_message_text("📋 Controlão recebido! Processando...")
            try:
                import subprocess as _sp2
                import httpx as _httpx3
                file = await context.bot.get_file(file_id)
                pdf_path = DATA_DIR / f"controlao_{user_id}_temp.pdf"
                await file.download_to_drive(str(pdf_path))
                import pypdf as _pypdf3
                reader3 = _pypdf3.PdfReader(str(pdf_path))
                texto3 = "\n".join(p.extract_text() for p in reader3.pages if p.extract_text())
                pdf_path.unlink(missing_ok=True)
                # Salva texto extraído
                ctrl_path = DATA_DIR / "controlao_ultimo.txt"
                ctrl_path.write_text(texto3, encoding="utf-8")
                # Gera conf_missao.json para o SisGOPA ler na aba Confirmação
                POSTOS_RE2 = r'(?:TEN-BRIG|MAJ-BRIG|BRIG|CEL|TC|MJ|CP|1T|2T|ST|SO|CB|SD|1S|2S|3S)'
                om_m2 = re.search(r'ORDEM DE MISS[ÃA]O\s*\n(.*?)(?:\n(?:Origem|======))', texto3, re.DOTALL)
                conf_json_data = {}
                if om_m2:
                    ohdr = om_m2.group(1).strip()
                    anv_m2 = re.search(r'Aeronave:\s*(VC-\d+)\s*/\s*FAB\s*(\d+)', ohdr)
                    om_n2 = re.search(r'Ordem de Miss[ãa]o:\s*(\d+)\s*/\s*(GTE-\d+)\s*/\s*(\d+)', ohdr)
                    trip_raw2 = re.findall(r'^(IN|OC|CM|AD|SB|BJ|BO|PX|NA)\s+(' + POSTOS_RE2 + r')\s+(.+?)$', ohdr, re.MULTILINE)
                    perna_raw2 = re.findall(r'([A-Z]{4})\s+\([^)]+\)\s+([\d/]+ - [\d:]+ Z[^P\n]*?)\s+[\d:]+\s+([A-Z]{4})\s+\([^)]+\)\s+([\d/]+ - [\d:]+ Z[^\n]*)', texto3)
                    conf_json_data = {
                        "dados": {
                            "oms": [{
                                "om_num": om_n2.group(1) if om_n2 else '',
                                "esq": om_n2.group(2) if om_n2 else 'GTE-1',
                                "ano": om_n2.group(3) if om_n2 else '',
                                "anv": anv_m2.group(1) if anv_m2 else '',
                                "fab": anv_m2.group(2) if anv_m2 else '',
                                "tripulantes": [{"funcao": f, "posto": p, "nome": n.strip()} for f, p, n in trip_raw2],
                                "pernas": [f"{o} {etd.strip()} → {d} {eta.strip()}" for o, etd, d, eta in perna_raw2]
                            }],
                            "missao_ativa": (om_n2.group(1)+'/'+om_n2.group(2)+'/'+om_n2.group(3)) if om_n2 else '',
                            "anv": anv_m2.group(1) if anv_m2 else '',
                            "fab": anv_m2.group(2) if anv_m2 else '',
                            "tripulantes": [{"funcao": f, "posto": p, "nome": n.strip()} for f, p, n in trip_raw2],
                            "pernas": [f"{o} {etd.strip()} → {d} {eta.strip()}" for o, etd, d, eta in perna_raw2],
                            "gerado_em": datetime.now().isoformat()
                        }
                    }
                    conf_json_path = DATA_DIR / "conf_missao.json"
                    conf_json_path.write_text(json.dumps(conf_json_data, ensure_ascii=False, indent=2), encoding="utf-8")
                _sp2.run(["git","add","data/controlao_ultimo.txt","data/conf_missao.json"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
                _sp2.run(["git","commit","-m","controlao: atualizado + conf_missao.json"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
                _sp2.run(["git","push","origin","main"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=30)

                # ── Parser controlão → set_conf no GAS ──────────────────
                CONF_GAS_URL = "https://script.google.com/macros/s/AKfycbwAkuMtXPes8ciLZw_EYT6a4EAHz6wGwdBUj5Bqm5eM--rkO2Yj7uJy8USXTjTWNkEYhg/exec"
                POSTOS_RE = r'(?:TEN-BRIG|MAJ-BRIG|BRIG|CEL|TC|MJ|CP|1T|2T|ST|SO|CB|SD|1S|2S|3S)'

                # Extrai seção ORDEM DE MISSÃO
                om_match = re.search(r'ORDEM DE MISS[ÃA]O\s*\n(.*?)(?:\n(?:Origem|======))', texto3, re.DOTALL)
                if om_match:
                    om_header = om_match.group(1).strip()
                    # Linha: "Ordem de Missão: 102 / GTE-1 / 2026 Aeronave: VC-2 / FAB 2590 Situação: PREVISTA"
                    om_num_m = re.search(r'Ordem de Miss[ãa]o:\s*([\d]+\s*/\s*GTE-\d+\s*/\s*\d+)', om_header)
                    anv_m = re.search(r'Aeronave:\s*(VC-\d+\s*/\s*FAB\s*\d+)', om_header)
                    missao_num = om_num_m.group(1).replace(' ', '').strip() if om_num_m else ''
                    anv_str = anv_m.group(1).strip() if anv_m else ''

                    # Tripulantes: linhas "POSTO NOME_GUERRA" com função (IN/OC/CM etc)
                    oficiais = []
                    tripulantes_raw = re.findall(
                        r'^(?:IN|OC|CM|AD|SB|BJ|BO|PX|NA)\s+(' + POSTOS_RE + r')\s+(.+?)$',
                        om_header, re.MULTILINE
                    )
                    for posto, nome in tripulantes_raw:
                        nome_clean = nome.strip()
                        # Busca chat_id nos tripulantes cadastrados
                        chat_id = ''
                        try:
                            trip_data = json.loads((DATA_DIR / "tripulantes.json").read_text()) if (DATA_DIR / "tripulantes.json").exists() else {}
                            for tid, tinfo in trip_data.items():
                                nome_cad = (tinfo.get('nome_guerra') or tinfo.get('name') or '').upper()
                                if nome_clean.upper() in nome_cad or nome_cad in nome_clean.upper():
                                    chat_id = str(tid)
                                    break
                        except Exception:
                            pass
                        oficiais.append({"posto": posto, "nome": nome_clean, "chat_id": chat_id})

                    # Pernas de voo
                    perna_re = re.findall(
                        r'([A-Z]{4})\s+\([^)]+\)\s+([\d/]+ - [\d:]+ Z[^P\n]*?)\s+[\d:]+\s+([A-Z]{4})\s+\([^)]+\)\s+([\d/]+ - [\d:]+ Z[^\n]*)',
                        texto3
                    )
                    pernas_list = [f"{o} {etd} → {d} {eta}" for o, etd, d, eta in perna_re]

                    if oficiais:
                        payload_conf = {
                            "action": "set_conf",
                            "missao": missao_num,
                            "anv": anv_str,
                            "obs": "",
                            "pernas": pernas_list,
                            "oficiais": oficiais
                        }
                        try:
                            async with _httpx3.AsyncClient(follow_redirects=True, timeout=15) as _hc:
                                r_conf = await _hc.post(CONF_GAS_URL, json=payload_conf)
                            rj = r_conf.json()
                            logger.info("SISGOP: set_conf GAS: %s", rj)
                            n_conf = rj.get('count', len(oficiais))
                            await query.edit_message_text(f"✅ Controlão processado!\n📋 {n_conf} tripulantes registrados na aba Confirmação.")
                        except Exception as eg:
                            logger.error("SISGOP: set_conf GAS erro: %s", eg)
                            await query.edit_message_text("✅ Controlão salvo, mas falha ao enviar para planilha.")
                    else:
                        await query.edit_message_text("✅ Controlão salvo! (Nenhum tripulante extraído da OM)")
                else:
                    await query.edit_message_text("✅ Controlão salvo! (Seção OM não encontrada no PDF)")
            except Exception as e:
                logger.error("Erro controlão: %s", e)
                await query.edit_message_text(f"❌ Erro ao processar controlão: {e}")
        return

    # ─── RAIO_VC: usuário escolheu VC para o raio via botão ───────────────
    if action == "raio_vc":
        if user_id not in ESCALANTES_AUTORIZADOS:
            await query.answer("⛔ Não autorizado.", show_alert=True)
            return
        vc = parts[1]      # "vc1" ou "vc2"
        cache_key = parts[2]   # "u{user_id}"
        file_id = _raio_pending.pop(cache_key, None)
        if not file_id:
            await query.edit_message_text("❌ PDF expirou. Manda o arquivo de novo.")
            return
        await query.edit_message_text(f"📄 Processando raio {vc.upper()}...")
        try:
            file = await context.bot.get_file(file_id)
            pdf_path = DATA_DIR / f"raio_{vc}_temp.pdf"
            await file.download_to_drive(str(pdf_path))
            import pypdf as _pypdf2
            _reader2 = _pypdf2.PdfReader(str(pdf_path))
            texto2 = "\n".join(p.extract_text() for p in _reader2.pages if p.extract_text())
            pdf_path.unlink(missing_ok=True)
            if not texto2.strip():
                await query.edit_message_text("❌ Não consegui extrair texto do PDF.")
                return
            POSTOS2 = ["TEN-BRIG","MAJ-BRIG","BRIG","CEL","TC","MJ","CP","1T","2T","ST","CB","SD"]
            pilotos2 = []
            for linha2 in texto2.split("\n"):
                linha2 = linha2.strip()
                m2 = re.match(r'^(\d+)(.+?)\s+\d{2}/\d{2}/\d{4}', linha2)
                if not m2: continue
                trecho2 = m2.group(2).strip()
                mx = re.match(r'^((?:' + '|'.join(POSTOS2) + r')\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜÇ]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜÇ]+)*)', trecho2)
                if mx:
                    partes2 = mx.group(1).strip().split(None, 1)
                    pilotos2.append({"pos": int(m2.group(1)), "posto": partes2[0], "nome": partes2[1].strip() if len(partes2)>1 else ""})
            if not pilotos2:
                await query.edit_message_text("❌ Não encontrei pilotos no PDF.")
                return
            raio2 = {"vc": vc, "data_consulta": datetime.now().strftime("%Y-%m-%d"), "gerado_em": datetime.now().isoformat(),
                     "enviado_por": ESCALANTES_AUTORIZADOS[user_id], "pilotos": pilotos2}
            raio_path2 = DATA_DIR / f"raio_{vc}.json"
            with open(raio_path2, "w", encoding="utf-8") as f:
                json.dump(raio2, f, ensure_ascii=False, indent=2)
            import subprocess as _sp
            _sp.run(["git","add",f"data/raio_{vc}.json"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
            _sp.run(["git","commit","-m",f"raio: {vc.upper()} atualizado por {ESCALANTES_AUTORIZADOS[user_id]}"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=10)
            _sp.run(["git","push","origin","main"], cwd=str(DATA_DIR.parent), capture_output=True, timeout=30)
            lista2 = "\n".join(f"{p['pos']}. {p['posto']} {p['nome']}" for p in pilotos2)
            await query.edit_message_text(f"✅ Raio {vc.upper()} atualizado! {len(pilotos2)} pilotos:\n\n{lista2}\n\nJá aparece no ESCALA V2.")
        except Exception as e:
            logger.error("Erro raio_vc callback: %s", e)
            await query.edit_message_text(f"❌ Erro: {e}")
        return

    if len(parts) < 2:
        return

    consulta_id = parts[1]

    # Resolver vc_key: aceita "vc1"/"vc2" direto ou busca pelo id completo
    data = _load_data()
    _resolved_vc = None
    for _vk in ("vc1", "vc2"):
        _c = data[_vk]
        if _c and (_c["id"] == consulta_id or consulta_id == _vk):
            _resolved_vc = _vk
            break

    if not _resolved_vc:
        # Auto-criar consulta se callback veio com vc1/vc2 direto
        if consulta_id in ("vc1", "vc2"):
            logger.info("Consulta %s não encontrada localmente — buscando no GAS", consulta_id)
            gas_consulta = await _gas_get_consulta(consulta_id)
            now = datetime.now()
            if gas_consulta:
                missions = gas_consulta.get("missions", [])
                text_gas = gas_consulta.get("text", "")
                recipients_gas = gas_consulta.get("recipients", [])
                logger.info("Consulta recuperada do GAS: %s missões, %s recipients", len(missions), len(recipients_gas))
            else:
                # Fallback: extrai missões do reply_markup da mensagem
                missions = []
                if query.message and query.message.reply_markup:
                    for row in query.message.reply_markup.inline_keyboard:
                        for btn in row:
                            if btn.callback_data and btn.callback_data.startswith("toggle|"):
                                parts_btn = btn.callback_data.split("|")
                                if len(parts_btn) >= 3:
                                    missions.append(parts_btn[2])
                text_gas = ""
                recipients_gas = []
                logger.warning("GAS não retornou consulta para %s — usando fallback do reply_markup", consulta_id)
            # Monta recipients limpos
            clean_recipients = []
            for rec in recipients_gas:
                chat_id_r = rec.get("chat_id") or rec.get("chatId")
                if chat_id_r:
                    clean_recipients.append({
                        "chat_id": int(chat_id_r),
                        "name": rec.get("name", ""),
                        "rank": rec.get("rank", ""),
                        "responses": {},
                        "confirmed": False,
                        "confirmed_at": None,
                        "delivered": True,
                    })
            data[consulta_id] = {
                "id": consulta_id,
                "vc_type": consulta_id,
                "created_at": now.isoformat(),
                "text": text_gas,
                "missions": missions,
                "parsed": {},
                "status": "active",
                "locked": False,
                "deadline": None,
                "recipients": clean_recipients,
            }
            _save_data(data)
            _resolved_vc = consulta_id
        else:
            logger.warning("Consulta não encontrada: %s", consulta_id)
            return
    logger.info("Resolved: vc=%s action=%s", _resolved_vc, action)

    consulta = data[_resolved_vc]

    # Se texto da consulta estiver vazio, busca do GAS
    if not consulta.get("text"):
        gas_c = await _gas_get_consulta(_resolved_vc)
        if gas_c and gas_c.get("text"):
            consulta["text"] = gas_c["text"]
            if not consulta.get("missions") and gas_c.get("missions"):
                consulta["missions"] = gas_c["missions"]
            _save_data(data)
            logger.info("Texto da consulta recuperado do GAS: %s", _resolved_vc)

    # Sincroniza lock com GAS — força checagem sem cache se local está travado
    if consulta.get("locked"):
        _gas_lock_cache.pop(_resolved_vc, None)  # invalida cache para checar fresco
    gas_locked = await _gas_is_locked(_resolved_vc)
    if gas_locked and not consulta.get("locked"):
        consulta["locked"] = True
        consulta["status"] = "locked"
        _save_data(data)
        logger.info("Lock sincronizado do GAS (travou): %s", _resolved_vc)
    elif not gas_locked and consulta.get("locked"):
        consulta["locked"] = False
        consulta["status"] = "active"
        _save_data(data)
        logger.info("Lock sincronizado do GAS (destravou): %s", _resolved_vc)

    # Verificar se consulta está encerrada (vale pra todos os callbacks)
    if consulta.get("locked") and action != "ciente":
        await query.edit_message_text(
            f"🔒 Consulta encerrada.\nPara dúvidas--> {TELEFONE_CONTATO}"
        )
        return

    # ─── CIENTE ───────────────────────────────────────────────────────────
    if action == "ciente":
        missao_letra = parts[2] if len(parts) > 2 else ""
        if consulta.get("locked"):
            await query.answer(
                f"🔒 Consulta encerrada.\nPara dúvidas--> {TELEFONE_CONTATO}",
                show_alert=True,
            )
            return
        for m in consulta.get("parsed", {}).get("missoes", []):
            if m["letra"] == missao_letra:
                if user_id not in [ci.get("user_id") for ci in m.get("cientes", [])]:
                    user_name = query.from_user.full_name or str(user_id)
                    m["cientes"].append({
                        "user_id": user_id,
                        "name": user_name,
                        "at": datetime.now().isoformat(),
                    })
                    _save_data(data)
        await query.edit_message_text(
            query.message.text + f"\n\n✅ CIENTE REGISTRADO — {datetime.now().strftime('%d/%m %H:%M')}",
        )
        return

    # ─── Toggle / allno / confirm ─────────────────────────────────────────
    vc_key_found = _resolved_vc

    # Encontrar destinatário
    recipient = None
    for r in consulta.get("recipients", []):
        if r["chat_id"] == user_id:
            recipient = r
            break

    if not recipient:
        # Tripulante não está na lista — pode ser que o chat_id veio como string
        for r in consulta.get("recipients", []):
            if str(r["chat_id"]) == str(user_id):
                recipient = r
                break

    if not recipient:
        # Auto-adicionar tripulante como recipient
        user = query.from_user
        recipient = {
            "chat_id": user_id,
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user_id),
            "responses": {},
            "confirmed": False,
            "delivered": True,
        }
        consulta["recipients"].append(recipient)
        logger.info("Auto-adicionado recipient: %s (%s)", recipient["name"], user_id)

    logger.info("Recipient encontrado: %s, confirmed=%s", recipient.get("name"), recipient.get("confirmed"))

    # ALTERAR: reseta confirmação e exibe teclado de missões novamente
    if action == "alterar":
        recipient["confirmed"] = False
        recipient["confirmed_at"] = None
        _save_data(data)
        missions_alt = consulta.get("missions", [])
        responses_alt = recipient.get("responses", {})
        vc_display_alt = _vc_display(consulta.get("vc_type", _resolved_vc or "vc1"))
        keyboard_alt = _build_keyboard(consulta_id, missions_alt, responses_alt, confirmed=False)
        status_lines = []
        for m in missions_alt:
            p = responses_alt.get(m)
            if p is not None and p > 0:
                emoji = PRIO_EMOJIS.get(p, f"#{p}")
                status_lines.append(f"  {emoji} {m}")
            elif p == 0:
                status_lines.append(f"  ❌ {m} — Indisponível")
            else:
                status_lines.append(f"  ⬜ {m} — Pendente")
        status_text = "\n".join(status_lines) if status_lines else "  Nenhuma resposta ainda"
        text_alt = (
            f"🛩️ CONSULTA {vc_display_alt}\n\n"
            f"{consulta.get('text', '')}\n\n"
            f"Suas respostas:\n{status_text}\n\n"
            f"Altere e confirme novamente."
        )
        await query.edit_message_text(text=text_alt, reply_markup=keyboard_alt, parse_mode=None)
        return

    # Não bloqueia mais por confirmed=True — só locked=True bloqueia (tratado acima)

    missions = consulta.get("missions", [])

    # Se clicar em toggle/allno/allyes/reset após confirmar → reseta confirmação automaticamente
    if action in ("toggle", "allno", "allyes", "reset") and recipient.get("confirmed"):
        recipient["confirmed"] = False
        recipient["confirmed_at"] = None

    if action == "toggle":
        mission = parts[2] if len(parts) > 2 else ""
        if "responses" not in recipient:
            recipient["responses"] = {}
        current = recipient["responses"].get(mission)
        if current is not None and current > 0:
            # Já tem prioridade → remove (volta pra pendente) e reordena
            removed_prio = current
            recipient["responses"][mission] = None
            # Reordenar prioridades dos restantes
            for m2 in missions:
                p = recipient["responses"].get(m2)
                if p is not None and p > removed_prio:
                    recipient["responses"][m2] = p - 1
        else:
            # Pendente ou indisponível → atribui próxima prioridade
            max_prio = max([v for v in recipient["responses"].values() if v is not None and v > 0], default=0)
            recipient["responses"][mission] = max_prio + 1

    elif action == "allyes":
        if "responses" not in recipient:
            recipient["responses"] = {}
        for m in missions:
            recipient["responses"][m] = 1

    elif action == "allno":
        if "responses" not in recipient:
            recipient["responses"] = {}
        for m in missions:
            recipient["responses"][m] = 0

    elif action == "reset":
        recipient["responses"] = {}
        logger.info("Respostas resetadas: %s", recipient.get("name", user_id))

    elif action == "confirm":
        responses = recipient.get("responses", {})
        missing = [m for m in missions if responses.get(m) is None]
        if missing:
            await query.answer(f"⚠️ Responda primeiro: {', '.join(missing)}", show_alert=True)
            return
        recipient["confirmed"] = True
        recipient["confirmed_at"] = datetime.now().isoformat()
        logger.info("Resposta confirmada: %s para %s", recipient.get("name", user_id), consulta_id)
        # Salvar ANTES do sync para que confirmed=True apareça no JSON público
        _save_data(data)
        await _save_response_to_gas(
            vc_key_found,
            recipient.get("name", str(user_id)),
            responses,
        )
        await _sync_response_to_sheet(
            vc_key_found,
            recipient.get("name", str(user_id)),
            responses,
        )
        # Não faz return — deixa cair no bloco de atualização de mensagem abaixo

    _save_data(data)

    # Atualizar mensagem
    responses = recipient.get("responses", {})
    vc_display = _vc_display(consulta.get("vc_type", vc_key_found or "vc1"))

    try:
        if recipient.get("confirmed"):
            # Montar resumo com prioridades + botão ALTERAR
            prio_lines = []
            unavail_list = []
            for m in missions:
                p = responses.get(m)
                if p is not None and p > 0:
                    emoji = PRIO_EMOJIS.get(p, f"#{p}")
                    prio_lines.append((p, f"  {emoji} {m}"))
                elif p == 0:
                    unavail_list.append(m)
            prio_lines.sort(key=lambda x: x[0])
            lines = [l for _, l in prio_lines]
            if unavail_list:
                lines.append(f"  ❌ {', '.join(unavail_list)}")
            consulta_text = consulta.get('text', '')
            text = (
                f"🛩️ CONSULTA {vc_display}\n\n"
                + (f"{consulta_text}\n\n" if consulta_text else "")
                + f"✅ RESPOSTA CONFIRMADA\n\n"
                f"Suas prioridades:\n" + "\n".join(lines)
            )
            keyboard = _build_keyboard(consulta_id, missions, responses, confirmed=True)
            await query.edit_message_text(text=text, reply_markup=keyboard)
        else:
            keyboard = _build_keyboard(consulta_id, missions, responses)
            status_lines = []
            for m in missions:
                p = responses.get(m)
                if p is not None and p > 0:
                    emoji = PRIO_EMOJIS.get(p, f"#{p}")
                    status_lines.append(f"  {emoji} {m}")
                elif p == 0:
                    status_lines.append(f"  ❌ {m} — Indisponível")
                else:
                    status_lines.append(f"  ⬜ {m} — Pendente")
            status_text = "\n".join(status_lines)
            text = (
                f"🛩️ CONSULTA {vc_display}\n\n"
                f"{consulta.get('text', '')}\n\n"
                f"Suas respostas:\n{status_text}\n\n"
                f"Toque na missão = define prioridade (ordem do clique)\n"
                f"Toque de novo = remove"
            )
            await query.edit_message_text(text=text, reply_markup=keyboard)
    except Exception as e:
        logger.error("Erro ao editar mensagem: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# Mini API HTTP para o SisGOPA
# ═══════════════════════════════════════════════════════════════════════════════

# Referência global ao bot do Telegram (preenchida no main)
telegram_bot = None


@middleware
async def cors_middleware(request, handler):
    """Middleware CORS permissivo para o SisGOPA."""
    if request.method == "OPTIONS":
        resp = web.Response(status=200)
    else:
        try:
            resp = await handler(request)
        except web.HTTPException as ex:
            resp = ex
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


def _check_auth(request):
    """Verifica token de autenticação da API."""
    token = request.headers.get("X-API-Secret") or request.rel_url.query.get("secret")
    return token == API_SECRET

async def api_get_consultas(request):
    """GET /api/consultas — Retorna estado atual das consultas."""
    if not _check_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    data = _load_data()
    return web.json_response(data)


async def api_post_consulta(request):
    """
    POST /api/consulta — Ações de gestão do SisGOPA. Requer header X-API-Secret.

    Actions:
      create          — Cria consulta
      lock            — Encerra respostas
      archive         — Arquiva consulta
      update_om       — Adiciona OM a uma missão
      update_saviso   — Adiciona escalados a SAVISO
      update_escalados— Define escalados para missão
      send_confirmacao— Envia confirmação via Telegram
    """
    if not _check_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "JSON inválido"}, status=400)

    action = body.get("action")
    vc = body.get("vc", "vc1")
    data = _load_data()

    # ─── CREATE ───────────────────────────────────────────────────────────
    if action == "create":
        if data.get(vc) is not None:
            # Arquiva a consulta anterior automaticamente antes de criar nova
            old = data[vc].copy()
            old["archived_at"] = datetime.now().isoformat()
            data.setdefault("archive", []).append(old)
            data[vc] = None
            logger.info("Consulta anterior arquivada automaticamente para criar nova: %s", vc)

        text = body.get("text", "")
        missions_raw = body.get("missions", [])
        deadline = body.get("deadline")  # null ou ISO string
        recipients = body.get("recipients", [])

        # Gerar ID
        now = datetime.now()
        consulta_id = f"{vc.upper()}-{now.strftime('%Y-%m-%d-%H%M%S')}"

        # Parse da mensagem
        parsed = parse_consulta_message(text)

        # Usar missões do body se fornecidas; senão do parser
        if missions_raw:
            missions = [m.get("letra", m) if isinstance(m, dict) else m for m in missions_raw]
        else:
            missions = [m["letra"] for m in parsed.get("missoes", [])]

        # Garantir que parsed.missoes tem as letras corretas
        if missions_raw and isinstance(missions_raw[0], dict):
            parsed["missoes"] = missions_raw

        consulta = {
            "id": consulta_id,
            "vc_type": vc,
            "created_at": now.isoformat(),
            "text": text,
            "missions": missions,
            "parsed": parsed,
            "status": "active",
            "locked": False,
            "deadline": deadline,
            "recipients": [],
        }

        # Enviar via Telegram para cada destinatário
        for rec in recipients:
            chat_id = rec.get("chat_id") or rec.get("chatId")
            name = rec.get("name", "")
            rank = rec.get("rank", "")

            responses = {}
            keyboard = _build_keyboard(consulta_id, missions, responses)

            # Montar texto da mensagem
            msg_text = f"🛩️ *CONSULTA {_vc_display(vc)}*\nID: `{consulta_id}`\n\n{text}\n\n*Missões:* {', '.join(missions)}\n\nToque nas missões para indicar disponibilidade, depois confirme."

            # Adicionar prazo se existir
            if deadline:
                try:
                    dl = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                    dl_str = dl.strftime("%d/%m/%Y %H:%M")
                    msg_text += f"\n\n⏰ *Prazo para resposta:* {dl_str}"
                except Exception:
                    pass

            try:
                msg = await telegram_bot.send_message(
                    chat_id=int(chat_id),
                    text=msg_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                consulta["recipients"].append({
                    "chat_id": int(chat_id),
                    "name": name,
                    "rank": rank,
                    "message_id": msg.message_id,
                    "delivered": True,
                    "responses": {},
                    "confirmed": False,
                    "confirmed_at": None,
                })
                logger.info("Consulta %s enviada para %s %s (%s)", consulta_id, rank, name, chat_id)
            except Exception as e:
                logger.error("Erro ao enviar para %s: %s", chat_id, e)
                consulta["recipients"].append({
                    "chat_id": int(chat_id) if str(chat_id).isdigit() else chat_id,
                    "name": name,
                    "rank": rank,
                    "message_id": None,
                    "delivered": False,
                    "responses": {},
                    "confirmed": False,
                    "confirmed_at": None,
                })

        data[vc] = consulta
        _save_data(data)
        return web.json_response({"ok": True, "id": consulta_id})

    # ─── LOCK ─────────────────────────────────────────────────────────────
    elif action == "lock":
        if not data.get(vc):
            return web.json_response({"ok": False, "error": "Nenhuma consulta ativa"})
        data[vc]["locked"] = True
        data[vc]["status"] = "locked"
        data[vc]["locked_at"] = datetime.now().isoformat()
        _save_data(data)
        return web.json_response({"ok": True})

    elif action == "unlock":
        # SisGOPA chama antes de criar nova consulta — reseta lock e confirmed de todos
        if data.get(vc):
            data[vc]["locked"] = False
            data[vc]["status"] = "active"
            for r in data[vc].get("recipients", []):
                r["confirmed"] = False
                r["confirmed_at"] = None
                r["responses"] = {}
            _save_data(data)
        # Limpa cache GAS para forçar re-fetch na próxima consulta
        _gas_lock_cache.pop(vc, None)
        _gas_consulta_cache.pop(vc, None)
        return web.json_response({"ok": True})

    # ─── ARCHIVE ──────────────────────────────────────────────────────────
    elif action == "archive":
        if not data.get(vc):
            return web.json_response({"ok": False, "error": "Nenhuma consulta para arquivar"})
        consulta_arquivada = data[vc].copy()
        consulta_arquivada["archived_at"] = datetime.now().isoformat()
        data.setdefault("archive", []).append(consulta_arquivada)
        data[vc] = None
        _save_data(data)
        # Backup da consulta arquivada em arquivo separado no GitHub
        await _backup_consulta_arquivada(consulta_arquivada)
        # Limpa o VC arquivado do respostas_pub.json no GitHub
        await _sync_response_to_sheet(vc, "archive", {}, motivo="arquivado")
        # Envia mensagem de encerramento aos recipients se solicitado
        mensagem_enc = body.get("mensagem")
        if mensagem_enc:
            recipients = consulta_arquivada.get("recipients", [])
            for r in recipients:
                chat_id = r.get("chat_id")
                if not chat_id:
                    continue
                try:
                    await app.bot.send_message(chat_id=chat_id, text=mensagem_enc)
                    logger.info("Mensagem encerramento enviada para %s (%s)", r.get("name","?"), chat_id)
                except Exception as e:
                    logger.warning("Falha ao enviar encerramento para %s: %s", chat_id, e)
        return web.json_response({"ok": True})

    # ─── UPDATE_OM ────────────────────────────────────────────────────────
    elif action == "update_om":
        if not data.get(vc):
            return web.json_response({"ok": False, "error": "Nenhuma consulta ativa"})
        missao_letra = body.get("missao", "")
        om = body.get("om", {})
        for m in data[vc].get("parsed", {}).get("missoes", []):
            if m["letra"] == missao_letra:
                m["om"] = om
                break
        _save_data(data)
        return web.json_response({"ok": True})

    # ─── UPDATE_SAVISO ────────────────────────────────────────────────────
    elif action == "update_saviso":
        if not data.get(vc):
            return web.json_response({"ok": False, "error": "Nenhuma consulta ativa"})
        missao_letra = body.get("missao", "")
        escalados = body.get("escalados", [])
        for m in data[vc].get("parsed", {}).get("missoes", []):
            if m["letra"] == missao_letra:
                m["escalados"] = escalados
                break
        _save_data(data)
        return web.json_response({"ok": True})

    # ─── UPDATE_ESCALADOS ─────────────────────────────────────────────────
    elif action == "update_escalados":
        if not data.get(vc):
            return web.json_response({"ok": False, "error": "Nenhuma consulta ativa"})
        missao_letra = body.get("missao", "")
        escalados = body.get("escalados", [])
        for m in data[vc].get("parsed", {}).get("missoes", []):
            if m["letra"] == missao_letra:
                m["escalados"] = escalados
                break
        _save_data(data)
        return web.json_response({"ok": True})

    # ─── SEND_CONFIRMACAO ─────────────────────────────────────────────────
    elif action == "send_confirmacao":
        if not data.get(vc):
            return web.json_response({"ok": False, "error": "Nenhuma consulta ativa"})

        consulta = data[vc]
        missoes = consulta.get("parsed", {}).get("missoes", [])
        enviados = 0
        erros = 0

        # Mapear chat_ids dos destinatários por nome
        recipients_map = {}
        for r in consulta.get("recipients", []):
            key = f"{r.get('rank', '')} {r.get('name', '')}".strip().upper()
            recipients_map[key] = r.get("chat_id")
            # Também mapear só pelo nome
            recipients_map[r.get("name", "").strip().upper()] = r.get("chat_id")

        for m in missoes:
            escalados = m.get("escalados", [])
            if not escalados:
                continue

            if m.get("is_saviso"):
                texto = (
                    f"SR. TRIPULANTE, ESCALADO {m['letra']}) SAVISO {m.get('saviso_dia', '')}:\n\n"
                    f"{' / '.join(escalados)}\n\n"
                    "FAVOR ACUSAR CIENTE\n"
                    "OPR GTE-1"
                )
            else:
                trechos_str = "\n".join(m.get("trechos", []))
                om_info = ""
                if m.get("om"):
                    if isinstance(m["om"], dict):
                        om_trechos = m["om"].get("trechos", [])
                        om_anv = m["om"].get("anv", "")
                        om_obs = m["om"].get("obs", "")
                        om_info = f"\n\nTrechos: {' / '.join(om_trechos)}" if om_trechos else ""
                        if om_anv:
                            om_info += f"\nANV: {om_anv}"
                        if om_obs:
                            om_info += f"\nOBS: {om_obs}"
                    elif isinstance(m["om"], str):
                        om_info = f"\n\n{m['om'][:300]}"

                texto = (
                    f"SR. TRIPULANTE, ESCALADO MISSÃO {m['letra']}:\n\n"
                    f"{' / '.join(escalados)}\n\n"
                    f"{trechos_str}"
                    f"{om_info}\n\n"
                    "OBS: Aguarda QMA para confirmação.\n\n"
                    "FAVOR ACUSAR CIENTE\n"
                    "OPR GTE-1"
                )

            keyboard = _build_ciente_keyboard(consulta["id"], m["letra"])

            # Enviar para cada escalado
            for nome_escalado in escalados:
                nome_upper = nome_escalado.strip().upper()
                chat_id = recipients_map.get(nome_upper)

                if not chat_id:
                    # Tentar busca parcial
                    for key, cid in recipients_map.items():
                        if nome_upper in key or key in nome_upper:
                            chat_id = cid
                            break

                if chat_id:
                    try:
                        await telegram_bot.send_message(
                            chat_id=int(chat_id),
                            text=texto,
                            reply_markup=keyboard,
                        )
                        enviados += 1
                    except Exception as e:
                        logger.error("Erro ao enviar confirmação para %s: %s", chat_id, e)
                        erros += 1
                else:
                    logger.warning("Chat ID não encontrado para escalado: %s", nome_escalado)
                    erros += 1

        return web.json_response({"ok": True, "enviados": enviados, "erros": erros})

    # ─── SEND_CONF (controlão → mensagens individuais) ────────────────────────
    elif action == "send_conf":
        messages = body.get("messages", [])
        if not messages:
            return web.json_response({"ok": False, "error": "Nenhuma mensagem"})
        enviados = 0
        erros = 0
        for m in messages:
            chat_id = str(m.get("chat_id", ""))
            texto = m.get("texto", "")
            letra = m.get("letra", "A")
            if not chat_id or not texto:
                erros += 1
                continue
            try:
                kb = {"inline_keyboard": [[{"text": "✅ CIENTE", "callback_data": f"conf_ciente|{letra}"}]]}
                await application.bot.send_message(
                    chat_id=int(chat_id),
                    text=texto,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ CIENTE", callback_data=f"conf_ciente|{letra}")]]) 
                )
                enviados += 1
            except Exception as e_send:
                logger.error("send_conf erro chat_id=%s: %s", chat_id, e_send)
                erros += 1
        return web.json_response({"ok": True, "enviados": enviados, "erros": erros})

    else:
        return web.json_response({"ok": False, "error": f"Ação desconhecida: {action}"}, status=400)


async def start_api():
    """Inicia o servidor HTTP na porta 8085."""
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/api/consultas", api_get_consultas)
    app.router.add_post("/api/consulta", api_post_consulta)
    # Rota OPTIONS para CORS preflight
    app.router.add_route("OPTIONS", "/api/consultas", lambda r: web.Response())
    app.router.add_route("OPTIONS", "/api/consulta", lambda r: web.Response())

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", API_PORT)
    await site.start()
    logger.info("API HTTP rodando em http://127.0.0.1:%d", API_PORT)


# ─── Verificador de prazo (deadline) ─────────────────────────────────────────

async def check_deadlines(app):
    """Verifica periodicamente se alguma consulta expirou o prazo."""
    while True:
        await asyncio.sleep(30)  # Verifica a cada 30 segundos
        try:
            data = _load_data()
            now = datetime.now(timezone.utc)
            changed = False
            for vc_key in ("vc1", "vc2"):
                c = data.get(vc_key)
                if c and not c.get("locked") and c.get("deadline"):
                    try:
                        dl = datetime.fromisoformat(c["deadline"].replace("Z", "+00:00"))
                        if now >= dl:
                            c["locked"] = True
                            c["status"] = "locked"
                            c["locked_at"] = now.isoformat()
                            c["locked_reason"] = "deadline"
                            changed = True
                            logger.info("Consulta %s encerrada automaticamente (prazo expirado)", c["id"])
                    except Exception:
                        pass
            if changed:
                _save_data(data)
        except Exception as e:
            logger.error("Erro no check_deadlines: %s", e)


# ─── Error handler ────────────────────────────────────────────────────────────


async def error_handler(update: Update, context):
    logger.error("Erro: %s", context.error, exc_info=context.error)


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    global telegram_bot

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        _save_data({"vc1": None, "vc2": None, "archive": []})

    logger.info("Iniciando SISGOP BOT v3 (mínimo + API HTTP)")

    app = Application.builder().token(BOT_TOKEN).build()

    # Guardar referência ao bot para a API HTTP
    telegram_bot = app.bot

    # Handlers — apenas /start e callbacks inline
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Document.PDF, raio_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    app.add_error_handler(error_handler)

    # Iniciar API HTTP e verificador de prazos junto com o bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run_all():
        # Iniciar API HTTP
        await start_api()

        # Iniciar verificador de deadline
        asyncio.create_task(check_deadlines(app))



        # Iniciar bot Telegram
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot pronto. Polling + API HTTP rodando.")

        # Manter rodando
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    loop.run_until_complete(run_all())


if __name__ == "__main__":
    main()
