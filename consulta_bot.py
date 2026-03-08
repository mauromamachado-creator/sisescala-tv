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
)

# ─── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN = "8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU"
TELEFONE_CONTATO = "(21) 99524-2702"
API_PORT = 8085

DATA_DIR = Path(__file__).parent / "data"
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

def _build_keyboard(consulta_id: str, missions: list[str], responses: dict) -> InlineKeyboardMarkup:
    """Monta teclado inline com botões de missão."""
    buttons = []
    row = []
    for m in missions:
        available = responses.get(m)
        if available is True:
            label = f"✅ {m}"
        elif available is False:
            label = f"❌ {m}"
        else:
            label = f"⬜ {m}"
        row.append(InlineKeyboardButton(label, callback_data=f"toggle|{consulta_id}|{m}"))
        if len(row) >= 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("❌ INDISPONÍVEL TODAS", callback_data=f"allno|{consulta_id}"),
    ])
    buttons.append([
        InlineKeyboardButton("✅ CONFIRMAR RESPOSTA", callback_data=f"confirm|{consulta_id}"),
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

async def cmd_start(update: Update, context):
    await update.message.reply_text(
        "🛩️ *SISGOP BOT — Consulta de Escala*\n\n"
        "Este bot recebe suas respostas de disponibilidade para missões.\n"
        "Quando receber uma consulta, use os botões para responder.\n\n"
        f"Para dúvidas: {TELEFONE_CONTATO}",
        parse_mode="Markdown",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Callback handler — Botões inline (toggle, allno, confirm, ciente)
# ═══════════════════════════════════════════════════════════════════════════════

async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    parts = query.data.split("|")
    action = parts[0]

    if len(parts) < 2:
        return

    consulta_id = parts[1]

    # ─── CIENTE ───────────────────────────────────────────────────────────
    if action == "ciente":
        missao_letra = parts[2] if len(parts) > 2 else ""
        data = _load_data()
        for vc_key in ("vc1", "vc2"):
            c = data[vc_key]
            if c and c["id"] == consulta_id:
                # Verificar se consulta está encerrada
                if c.get("locked"):
                    await query.answer(
                        f"🔒 Consulta encerrada. Para dúvidas: {TELEFONE_CONTATO}",
                        show_alert=True,
                    )
                    return
                for m in c.get("parsed", {}).get("missoes", []):
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
        await query.answer("⚠️ Consulta não encontrada.", show_alert=True)
        return

    # ─── Toggle / allno / confirm ─────────────────────────────────────────
    data = _load_data()
    consulta = None
    vc_key_found = None
    for vc_key in ("vc1", "vc2"):
        c = data[vc_key]
        if c and c["id"] == consulta_id:
            consulta = c
            vc_key_found = vc_key
            break

    if not consulta:
        await query.answer("⚠️ Consulta não encontrada.", show_alert=True)
        return

    # Consulta encerrada
    if consulta.get("locked"):
        await query.answer(
            f"🔒 Consulta encerrada. Para dúvidas, entre em contato: {TELEFONE_CONTATO}",
            show_alert=True,
        )
        return

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
        await query.answer("⚠️ Você não é destinatário desta consulta.", show_alert=True)
        return

    if recipient.get("confirmed"):
        await query.answer("✅ Você já confirmou sua resposta.", show_alert=True)
        return

    missions = consulta.get("missions", [])

    if action == "toggle":
        mission = parts[2] if len(parts) > 2 else ""
        current = recipient.get("responses", {}).get(mission)
        if "responses" not in recipient:
            recipient["responses"] = {}
        recipient["responses"][mission] = not current if current is not None else True

    elif action == "allno":
        if "responses" not in recipient:
            recipient["responses"] = {}
        for m in missions:
            recipient["responses"][m] = False

    elif action == "confirm":
        responses = recipient.get("responses", {})
        missing = [m for m in missions if m not in responses]
        if missing:
            await query.answer(f"⚠️ Responda primeiro: {', '.join(missing)}", show_alert=True)
            return
        recipient["confirmed"] = True
        recipient["confirmed_at"] = datetime.now().isoformat()
        logger.info("Resposta confirmada: %s para %s", recipient.get("name", user_id), consulta_id)

    _save_data(data)

    # Atualizar mensagem
    responses = recipient.get("responses", {})
    vc_display = _vc_display(consulta.get("vc_type", vc_key_found or "vc1"))

    if recipient.get("confirmed"):
        avail = [m for m, v in responses.items() if v]
        unavail = [m for m, v in responses.items() if not v]
        text = (
            f"🛩️ *CONSULTA {vc_display}*\n"
            f"ID: `{consulta_id}`\n\n"
            f"✅ *RESPOSTA CONFIRMADA*\n"
            f"Disponível: {', '.join(avail) or 'nenhuma'}\n"
            f"Indisponível: {', '.join(unavail) or 'nenhuma'}"
        )
        await query.edit_message_text(text=text, parse_mode="Markdown")
    else:
        keyboard = _build_keyboard(consulta_id, missions, responses)
        text = (
            f"🛩️ *CONSULTA {vc_display}*\n"
            f"ID: `{consulta_id}`\n\n"
            f"{consulta.get('text', '')}\n\n"
            f"*Missões:* {', '.join(missions)}\n\n"
            "Toque nas missões, depois confirme."
        )
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="Markdown")


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


async def api_get_consultas(request):
    """GET /api/consultas — Retorna estado atual das consultas."""
    data = _load_data()
    return web.json_response(data)


async def api_post_consulta(request):
    """
    POST /api/consulta — Ações de gestão do SisGOPA.

    Actions:
      create          — Cria consulta
      lock            — Encerra respostas
      archive         — Arquiva consulta
      update_om       — Adiciona OM a uma missão
      update_saviso   — Adiciona escalados a SAVISO
      update_escalados— Define escalados para missão
      send_confirmacao— Envia confirmação via Telegram
    """
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
            return web.json_response({"ok": False, "error": f"Já existe consulta ativa em {_vc_display(vc)}"})

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

    # ─── ARCHIVE ──────────────────────────────────────────────────────────
    elif action == "archive":
        if not data.get(vc):
            return web.json_response({"ok": False, "error": "Nenhuma consulta para arquivar"})
        data[vc]["archived_at"] = datetime.now().isoformat()
        data.setdefault("archive", []).append(data[vc])
        data[vc] = None
        _save_data(data)
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
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    logger.info("API HTTP rodando em http://0.0.0.0:%d", API_PORT)


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
