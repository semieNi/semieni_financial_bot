import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from database import adicionar_transacao, obter_resumo, obter_saldo
from database import exportar_transacoes, obter_totais_mes_atual

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou seu Assistente Financeiro.\n\n"
        "Use /add para registrar um gasto ou receita.\n"
        "Exemplo: /add gasto 25 mercado\n\n"
        "Use /report para ver seus gastos recentes.\n"
        "Use /balance para ver seu saldo atual."
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        tipo, valor, categoria = context.args
        valor = float(valor)

        adicionar_transacao(user_id, tipo.lower(), valor, categoria.lower())
        await update.message.reply_text(f"{tipo.capitalize()} de R${valor:.2f} em '{categoria}' registrado com sucesso!")

        # ⚠️ ALERTA AUTOMÁTICO
        receita_mes, gasto_mes = obter_totais_mes_atual(user_id)

        if receita_mes > 0 and gasto_mes >= receita_mes * 0.8:
            percentual = (gasto_mes / receita_mes) * 100
            await update.message.reply_text(
                f"⚠️ Atenção! Seus gastos neste mês já atingiram {percentual:.0f}% da sua receita.\n"
                "Considere reduzir os gastos para evitar ultrapassar seu orçamento."
            )

    except Exception:
        await update.message.reply_text("⚠️ Formato inválido. Use:\n/add [gasto|receita] [valor] [categoria]")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    resumo = obter_resumo(user_id)

    if not resumo:
        await update.message.reply_text("📭 Nenhuma transação registrada ainda.")
        return

    mensagem = "📊 *Resumo das transações nos últimos 7 dias:*\n"
    for tipo, categoria, total in resumo:
        emoji = "💸" if tipo == "gasto" else "💰"
        mensagem += f"{emoji} {tipo.capitalize()} - {categoria.capitalize()}: R${total:.2f}\n"

    await update.message.reply_text(mensagem, parse_mode="Markdown")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    saldo = obter_saldo(user_id)
    cor = "🟢" if saldo >= 0 else "🔴"
    await update.message.reply_text(f"{cor} Seu saldo atual é: R${saldo:.2f}")

async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    caminho = exportar_transacoes(user_id)

    if not caminho:
        await update.message.reply_text("📭 Você ainda não tem transações registradas para exportar.")
        return

    with open(caminho, "rb") as arquivo:
        await update.message.reply_document(document=arquivo, filename="transacoes.csv")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("exportar", exportar))

    app.run_polling()

print("🤖 Bot iniciado com sucesso!")
