import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import (
    adicionar_transacao, obter_resumo, obter_saldo,
    exportar_transacoes, obter_totais_mes_atual,
    registrar_usuario, listar_usuarios,
    listar_transacoes_recentes, deletar_transacao
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# 🗕️ Agendador global
scheduler = AsyncIOScheduler()

# Categorias predefinidas
CATEGORIAS = ["mercado", "transporte", "lazer", "salario", "outros"]

async def iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registrar_usuario(user_id)
    await update.message.reply_text(
        "👋 Olá! Eu sou seu Assistente Financeiro.\n\n"
        "Use /registrar para adicionar um gasto ou receita com botões interativos.\n"
        "Use /resumo para ver seus gastos recentes.\n"
        "Use /saldo para ver seu saldo atual.\n"
        "Use /planilha para exportar uma planilha com todos os dados registrados.\n"
        "Use /painel para acessar seu painel com gráficos online.\n"
        "Use /ultimos para ver e deletar transações recentes."
    )

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💸 Gasto", callback_data="tipo_gasto")],
        [InlineKeyboardButton("💰 Receita", callback_data="tipo_receita")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Escolha o tipo de transação:", reply_markup=reply_markup)

def escolher_categoria(tipo):
    botoes = [[InlineKeyboardButton(cat.capitalize(), callback_data=f"categoria_{cat}")]
              for cat in CATEGORIAS if cat != "outros"]
    botoes.append([InlineKeyboardButton("➕ Outra categoria...", callback_data="categoria_outros")])
    return InlineKeyboardMarkup(botoes)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("tipo_"):
        tipo = data.split("_")[1]
        context.user_data["tipo"] = tipo
        await query.edit_message_text(f"Tipo escolhido: {tipo.capitalize()}\nAgora escolha uma categoria:",
                                      reply_markup=escolher_categoria(tipo))

    elif data.startswith("categoria_"):
        cat = data.split("_")[1]
        if cat == "outros":
            context.user_data["categoria_custom"] = True
            await query.edit_message_text("Digite o nome da categoria personalizada:")
        else:
            context.user_data["categoria"] = cat
            context.user_data["categoria_custom"] = False
            await query.edit_message_text(f"Categoria escolhida: {cat.capitalize()}\nAgora envie o valor:")

    elif data.startswith("deletar_"):
        transacao_id = int(data.split("_")[1])
        user_id = query.from_user.id
        sucesso = deletar_transacao(transacao_id, user_id)
        if sucesso:
            await query.edit_message_text("✅ Transação deletada com sucesso.")
        else:
            await query.edit_message_text("⚠️ Erro: transação não encontrada ou não pertence a você.")

async def mensagem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if context.user_data.get("categoria_custom") and "categoria" not in context.user_data:
        context.user_data["categoria"] = text.lower()
        await update.message.reply_text("Agora envie o valor:")
        return

    if "categoria" in context.user_data and "tipo" in context.user_data:
        try:
            valor = float(text.replace(",", "."))
            adicionar_transacao(user_id, context.user_data["tipo"], valor, context.user_data["categoria"])
            await update.message.reply_text(f"✅ {context.user_data['tipo'].capitalize()} de R${valor:.2f} registrado em '{context.user_data['categoria']}'.")
        except ValueError:
            await update.message.reply_text("⚠️ Valor inválido. Envie apenas números. Ex: 25.90")
            return

        context.user_data.clear()
    else:
        await update.message.reply_text("Use /registrar para iniciar um novo registro.")

async def ultimos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    transacoes = listar_transacoes_recentes(user_id)

    if not transacoes:
        await update.message.reply_text("📍 Nenhuma transação recente encontrada.")
        return

    for t in transacoes:
        id_, tipo, valor, categoria, data = t
        texto = f"ID: {id_}\nTipo: {tipo.capitalize()}\nValor: R${valor:.2f}\nCategoria: {categoria.capitalize()}\nData: {data}"
        teclado = InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("🗑 Deletar", callback_data=f"deletar_{id_}")
        )
        await update.message.reply_text(texto, reply_markup=teclado)

async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registrar_usuario(user_id)
    resumo = obter_resumo(user_id)

    if not resumo:
        await update.message.reply_text("👭 Nenhuma transação registrada ainda.")
        return

    mensagem = "📊 *Resumo das transações nos últimos 7 dias:*\n"
    for tipo, categoria, total in resumo:
        emoji = "💸" if tipo == "gasto" else "💰"
        mensagem += f"{emoji} {tipo.capitalize()} - {categoria.capitalize()}: R${total:.2f}\n"

    await update.message.reply_text(mensagem, parse_mode="Markdown")

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registrar_usuario(user_id)
    saldo = obter_saldo(user_id)
    cor = "🟢" if saldo >= 0 else "🔴"
    await update.message.reply_text(f"{cor} Seu saldo atual é: R${saldo:.2f}")

async def planilha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registrar_usuario(user_id)
    caminho = exportar_transacoes(user_id)

    if not caminho:
        await update.message.reply_text("📬 Você ainda não tem transações registradas para exportar.")
        return

    with open(caminho, "rb") as arquivo:
        await update.message.reply_document(document=arquivo, filename="transacoes.csv")

async def painel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registrar_usuario(user_id)

    url_base = "https://dashboard-financeiro-3l8yw3xux3u4iztqermk3v.streamlit.app/"
    link = f"{url_base}?user_id={user_id}"

    await update.message.reply_text(f"📊 Aqui está seu painel de finanças:\n{link}")

# 🔔 Lembrete semanal: toda segunda às 08h
async def enviar_resumo_semanal(app):
    for user_id in listar_usuarios():
        resumo = obter_resumo(user_id)
        if resumo:
            mensagem = "📊 *Resumo semanal:*\n"
            for tipo, categoria, total in resumo:
                emoji = "💸" if tipo == "gasto" else "💰"
                mensagem += f"{emoji} {tipo.capitalize()} - {categoria.capitalize()}: R${total:.2f}\n"
            await app.bot.send_message(chat_id=user_id, text=mensagem, parse_mode="Markdown")

# 🔔 Lembrete mensal: dia 1 às 08h
async def enviar_saldo_mensal(app):
    for user_id in listar_usuarios():
        saldo_valor = obter_saldo(user_id)
        cor = "🟢" if saldo_valor >= 0 else "🔴"
        await app.bot.send_message(chat_id=user_id, text=f"{cor} Seu saldo atual neste início de mês é: R${saldo_valor:.2f}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # ⏰ Agendamentos automáticos
    scheduler.add_job(enviar_resumo_semanal, "cron", day_of_week="mon", hour=8, minute=0, args=[app])
    scheduler.add_job(enviar_saldo_mensal, "cron", day=1, hour=8, minute=0, args=[app])
    scheduler.start()

    # Handlers
    app.add_handler(CommandHandler(["iniciar", "start"], iniciar))
    app.add_handler(MessageHandler(filters.Regex("^/start$"), iniciar))
    app.add_handler(CommandHandler(["iniciar", "start"], iniciar))
    app.add_handler(CommandHandler("registrar", registrar))
    app.add_handler(CommandHandler("ultimos", ultimos))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(tipo_|categoria_|deletar_)", block=False))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem_handler))
    app.add_handler(CommandHandler("resumo", resumo))
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("planilha", planilha))
    app.add_handler(CommandHandler("painel", painel))

    app.run_polling()

print("🤖 Bot iniciado com sucesso!")
