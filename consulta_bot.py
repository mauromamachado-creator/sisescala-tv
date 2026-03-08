#!/usr/bin/env python3
"""
SISGOP BOT - Sistema de Consulta de Escala de Voo
Bot Telegram para consulta de disponibilidade de tripulações.
Fase 1 - Modo Teste (JSON local)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ─── Config ───────────────────────────────────────────────────────────────────
TEST_MODE = True
BOT_TOKEN = "8429586140:AAHZbra0vRJU-E4KQcNEp1ZvqkyGsQg2ShU"
AUTHORIZED_USERS = {673591486: {"name": "Major Machado", "rank": "MJ"}}
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "consultas.json"

# ConversationHandler states
TEXTO, MISSOES, PRAZO, CONFIRMAR = range(4)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.DEBUG if TEST_MODE else logging.INFO,
)
logger = logging.getLogger("SISGOP")

# ─── Data helpers ─────────────────────────────────────────────────────────────

def _load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"consultas": []}


def _save_data(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _active_consulta(data: dict) -> Optional[dict]:
    for c in reversed(data["consultas"]):
        if not c["archived"]:
            return c
    return None


def _next_id(data: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    count = sum(1 for c in data["consultas"] if c["id"].startswith(today))
    return f"{today}-{count+1:03d}"


def _tag() -> str:
    return "[MODO TESTE] " if TEST_MODE else ""


# ─── Keyboard builder ────────────────────────────────────────────────────────

def _build_keyboard(consulta_id: str, missions: list[str], responses: dict) -> InlineKeyboardMarkup:
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


# ─── Auth check ───────────────────────────────────────────────────────────────

def _is_authorized(user_id: int) -> bool:
    if TEST_MODE:
        return user_id in AUTHORIZED_USERS
    return user_id in AUTHORIZED_USERS


# ─── Command handlers ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context):
    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return
    await update.message.reply_text(
        f"{_tag()}🛩️ *SISGOP BOT - Sistema de Consulta de Escala*\n\n"
        "Bem-vindo ao sistema de consulta de disponibilidade.\n\n"
        "Use /ajuda para ver os comandos disponíveis.",
        parse_mode="Markdown",
    )


async def cmd_ajuda(update: Update, context):
    if not _is_authorized(update.effective_user.id):
        return
    await update.message.reply_text(
        f"{_tag()}📋 *COMANDOS DISPONÍVEIS*\n\n"
        "/nova\\_consulta — Criar nova consulta de disponibilidade\n"
        "/status — Ver status da consulta ativa\n"
        "/encerrar — Encerrar consulta (bloquear respostas)\n"
        "/arquivo — Arquivar consulta encerrada\n"
        "/ajuda — Esta mensagem\n"
        "/start — Mensagem de boas-vindas\n",
        parse_mode="Markdown",
    )


# ─── /nova_consulta conversation ─────────────────────────────────────────────

async def nova_consulta_start(update: Update, context):
    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return ConversationHandler.END
    await update.message.reply_text(
        f"{_tag()}📝 *NOVA CONSULTA*\n\n"
        "Envie o texto da consulta (ou encaminhe uma mensagem).\n"
        "Use /cancelar para abortar.",
        parse_mode="Markdown",
    )
    return TEXTO


async def nova_consulta_texto(update: Update, context):
    text = update.message.text or update.message.caption or ""
    if update.message.forward_date:
        text = f"[Msg encaminhada] {text}"
    if not text.strip():
        await update.message.reply_text("⚠️ Texto vazio. Envie novamente ou /cancelar.")
        return TEXTO
    context.user_data["consulta_texto"] = text.strip()
    await update.message.reply_text(
        "✈️ Informe as letras das missões separadas por vírgula.\n"
        "Exemplo: `A, B, C, D`",
        parse_mode="Markdown",
    )
    return MISSOES


async def nova_consulta_missoes(update: Update, context):
    raw = update.message.text.upper().replace(" ", "")
    missions = [m.strip() for m in raw.split(",") if m.strip()]
    if not missions:
        await update.message.reply_text("⚠️ Informe pelo menos uma missão. Exemplo: `A,B,C`", parse_mode="Markdown")
        return MISSOES
    context.user_data["consulta_missoes"] = missions
    await update.message.reply_text(
        "⏰ Informe o prazo para resposta.\n"
        "Formato: `DD/MM/AAAA HH:MM` ou digite `sem prazo`.",
        parse_mode="Markdown",
    )
    return PRAZO


async def nova_consulta_prazo(update: Update, context):
    raw = update.message.text.strip().lower()
    deadline = None
    if raw not in ("sem prazo", "sem", "-", "n", "nao", "não"):
        try:
            deadline = datetime.strptime(raw, "%d/%m/%Y %H:%M").isoformat()
        except ValueError:
            await update.message.reply_text("⚠️ Formato inválido. Use `DD/MM/AAAA HH:MM` ou `sem prazo`.", parse_mode="Markdown")
            return PRAZO
    context.user_data["consulta_prazo"] = deadline

    missions = context.user_data["consulta_missoes"]
    texto = context.user_data["consulta_texto"]
    prazo_str = deadline if deadline else "Sem prazo"
    recipients = "\n".join(f"  • {v['rank']} {v['name']}" for v in AUTHORIZED_USERS.values())

    await update.message.reply_text(
        f"{_tag()}📋 *PRÉVIA DA CONSULTA*\n\n"
        f"*Texto:*\n{texto}\n\n"
        f"*Missões:* {', '.join(missions)}\n"
        f"*Prazo:* {prazo_str}\n"
        f"*Destinatários:*\n{recipients}\n\n"
        "Envie *SIM* para confirmar e enviar, ou /cancelar.",
        parse_mode="Markdown",
    )
    return CONFIRMAR


async def nova_consulta_confirmar(update: Update, context):
    if update.message.text.strip().upper() not in ("SIM", "S", "CONFIRMAR"):
        await update.message.reply_text("Envie *SIM* para confirmar ou /cancelar.", parse_mode="Markdown")
        return CONFIRMAR

    data = _load_data()
    consulta_id = _next_id(data)
    missions = context.user_data["consulta_missoes"]
    texto = context.user_data["consulta_texto"]
    deadline = context.user_data.get("consulta_prazo")

    consulta = {
        "id": consulta_id,
        "created_at": datetime.now().isoformat(),
        "created_by": update.effective_user.id,
        "text": texto,
        "missions": missions,
        "deadline": deadline,
        "status": "active",
        "recipients": [],
        "locked": False,
        "archived": False,
    }

    # Send to all recipients
    prazo_str = deadline if deadline else "Sem prazo definido"
    for chat_id, info in AUTHORIZED_USERS.items():
        responses = {}
        keyboard = _build_keyboard(consulta_id, missions, responses)
        try:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"{_tag()}🛩️ *CONSULTA DE DISPONIBILIDADE*\n"
                    f"ID: `{consulta_id}`\n\n"
                    f"{texto}\n\n"
                    f"*Missões:* {', '.join(missions)}\n"
                    f"*Prazo:* {prazo_str}\n\n"
                    "Toque nas missões para indicar sua disponibilidade, "
                    "depois confirme."
                ),
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            consulta["recipients"].append({
                "chat_id": chat_id,
                "name": info["name"],
                "rank": info["rank"],
                "message_id": msg.message_id,
                "delivered": True,
                "responses": responses,
                "confirmed": False,
                "confirmed_at": None,
            })
            logger.info("Consulta %s enviada para %s (%s)", consulta_id, info["name"], chat_id)
        except Exception as e:
            logger.error("Erro ao enviar para %s: %s", chat_id, e)
            consulta["recipients"].append({
                "chat_id": chat_id,
                "name": info["name"],
                "rank": info["rank"],
                "message_id": None,
                "delivered": False,
                "responses": {},
                "confirmed": False,
                "confirmed_at": None,
            })

    data["consultas"].append(consulta)
    _save_data(data)

    sent = sum(1 for r in consulta["recipients"] if r["delivered"])
    total = len(consulta["recipients"])
    await update.message.reply_text(
        f"✅ Consulta `{consulta_id}` enviada!\n"
        f"Entregue: {sent}/{total} destinatários.",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def nova_consulta_cancelar(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text("❌ Consulta cancelada.")
    return ConversationHandler.END


# ─── /status ──────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, context):
    if not _is_authorized(update.effective_user.id):
        return
    data = _load_data()
    consulta = _active_consulta(data)
    if not consulta:
        await update.message.reply_text("ℹ️ Nenhuma consulta ativa no momento.")
        return

    lines = [
        f"{_tag()}📊 *STATUS DA CONSULTA* `{consulta['id']}`",
        f"Status: {'🔒 Encerrada' if consulta['locked'] else '🟢 Ativa'}",
        f"Missões: {', '.join(consulta['missions'])}",
        "",
    ]
    for r in consulta["recipients"]:
        if r["confirmed"]:
            avail = [m for m, v in r["responses"].items() if v]
            unavail = [m for m, v in r["responses"].items() if not v]
            status = f"✅ Confirmou — Disp: {','.join(avail) or 'nenhuma'} | Indisp: {','.join(unavail) or 'nenhuma'}"
        elif r["delivered"]:
            status = "⏳ Aguardando resposta"
        else:
            status = "❌ Não entregue"
        lines.append(f"• {r['rank']} {r['name']}: {status}")

    confirmed = sum(1 for r in consulta["recipients"] if r["confirmed"])
    total = len(consulta["recipients"])
    lines.append(f"\n📈 Respostas: {confirmed}/{total}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── /encerrar ────────────────────────────────────────────────────────────────

async def cmd_encerrar(update: Update, context):
    if not _is_authorized(update.effective_user.id):
        return
    data = _load_data()
    consulta = _active_consulta(data)
    if not consulta:
        await update.message.reply_text("ℹ️ Nenhuma consulta ativa.")
        return
    if consulta["locked"]:
        await update.message.reply_text("ℹ️ Consulta já encerrada.")
        return
    consulta["locked"] = True
    consulta["status"] = "locked"
    _save_data(data)
    logger.info("Consulta %s encerrada por %s", consulta["id"], update.effective_user.id)
    await update.message.reply_text(f"🔒 Consulta `{consulta['id']}` encerrada. Respostas bloqueadas.", parse_mode="Markdown")


# ─── /arquivo ─────────────────────────────────────────────────────────────────

async def cmd_arquivo(update: Update, context):
    if not _is_authorized(update.effective_user.id):
        return
    data = _load_data()
    consulta = _active_consulta(data)
    if not consulta:
        await update.message.reply_text("ℹ️ Nenhuma consulta para arquivar.")
        return
    consulta["archived"] = True
    consulta["status"] = "archived"
    _save_data(data)
    logger.info("Consulta %s arquivada", consulta["id"])
    await update.message.reply_text(f"📁 Consulta `{consulta['id']}` arquivada.", parse_mode="Markdown")


# ─── Callback: button presses ────────────────────────────────────────────────

async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    parts = query.data.split("|")
    action = parts[0]
    consulta_id = parts[1]

    data = _load_data()
    consulta = None
    for c in data["consultas"]:
        if c["id"] == consulta_id:
            consulta = c
            break
    if not consulta:
        await query.answer("⚠️ Consulta não encontrada.", show_alert=True)
        return

    if consulta["locked"]:
        await query.answer("🔒 Esta consulta já foi encerrada. Respostas bloqueadas.", show_alert=True)
        return

    # Find recipient
    recipient = None
    for r in consulta["recipients"]:
        if r["chat_id"] == user_id:
            recipient = r
            break
    if not recipient:
        await query.answer("⚠️ Você não é destinatário desta consulta.", show_alert=True)
        return

    if recipient["confirmed"]:
        await query.answer("✅ Você já confirmou sua resposta.", show_alert=True)
        return

    if action == "toggle":
        mission = parts[2]
        current = recipient["responses"].get(mission)
        recipient["responses"][mission] = not current if current is not None else True

    elif action == "allno":
        for m in consulta["missions"]:
            recipient["responses"][m] = False

    elif action == "confirm":
        # Check all missions have a response
        missing = [m for m in consulta["missions"] if m not in recipient["responses"]]
        if missing:
            await query.answer(f"⚠️ Responda todas as missões: {', '.join(missing)}", show_alert=True)
            return
        recipient["confirmed"] = True
        recipient["confirmed_at"] = datetime.now().isoformat()
        logger.info("Resposta confirmada: %s para consulta %s", recipient["name"], consulta_id)

    _save_data(data)

    # Update keyboard
    keyboard = _build_keyboard(consulta_id, consulta["missions"], recipient["responses"])
    if recipient["confirmed"]:
        avail = [m for m, v in recipient["responses"].items() if v]
        unavail = [m for m, v in recipient["responses"].items() if not v]
        text = (
            f"{_tag()}🛩️ *CONSULTA DE DISPONIBILIDADE*\n"
            f"ID: `{consulta_id}`\n\n"
            f"{consulta['text']}\n\n"
            f"*Missões:* {', '.join(consulta['missions'])}\n\n"
            f"✅ *RESPOSTA CONFIRMADA*\n"
            f"Disponível: {', '.join(avail) or 'nenhuma'}\n"
            f"Indisponível: {', '.join(unavail) or 'nenhuma'}"
        )
        await query.edit_message_text(text=text, parse_mode="Markdown")
    else:
        prazo_str = consulta.get("deadline") or "Sem prazo definido"
        text = (
            f"{_tag()}🛩️ *CONSULTA DE DISPONIBILIDADE*\n"
            f"ID: `{consulta_id}`\n\n"
            f"{consulta['text']}\n\n"
            f"*Missões:* {', '.join(consulta['missions'])}\n"
            f"*Prazo:* {prazo_str}\n\n"
            "Toque nas missões para indicar sua disponibilidade, "
            "depois confirme."
        )
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="Markdown")


# ─── Error handler ────────────────────────────────────────────────────────────

async def error_handler(update: Update, context):
    logger.error("Erro: %s", context.error, exc_info=context.error)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        _save_data({"consultas": []})

    logger.info("Iniciando SISGOP BOT %s", "[MODO TESTE]" if TEST_MODE else "")

    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation: nova consulta
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("nova_consulta", nova_consulta_start)],
        states={
            TEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, nova_consulta_texto)],
            MISSOES: [MessageHandler(filters.TEXT & ~filters.COMMAND, nova_consulta_missoes)],
            PRAZO: [MessageHandler(filters.TEXT & ~filters.COMMAND, nova_consulta_prazo)],
            CONFIRMAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, nova_consulta_confirmar),
                CommandHandler("cancelar", nova_consulta_cancelar),
            ],
        },
        fallbacks=[CommandHandler("cancelar", nova_consulta_cancelar)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("encerrar", cmd_encerrar))
    app.add_handler(CommandHandler("arquivo", cmd_arquivo))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_error_handler(error_handler)

    logger.info("Bot pronto. Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
