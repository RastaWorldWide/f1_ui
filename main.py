# f1_bot.py — F1 Team Control Bot + Web Dashboard (локально)
import os
import re
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# === ГЛОБАЛЬНЫЕ ДАННЫЕ (в памяти) ===
TEAMS = []          # [{"id": 1, "name": "...", "aliases": [...], "score": 0}, ...]
ROUND = 1
MAX_ROUNDS = 11

def normalize(text: str) -> str:
    """Убирает пробелы, приводит к нижнему регистру, удаляет спецсимволы"""
    return re.sub(r'[^а-яa-z0-9]', '', text.lower())

def find_team(query: str):
    """Ищет команду по названию или алиасу"""
    q = normalize(query)
    for team in TEAMS:
        if q == str(team["id"]) or any(q == normalize(a) for a in team["aliases"]):
            return team
    return None

# === КОМАНДЫ ТЕЛЕГРАМ ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏎️ *F1 Team Control*\n\n"
        "Используйте:\n"
        "`/setup` — создать команды\n"
        "`/add <название> <баллы>` — изменить счёт\n"
        "`/table` — показать таблицу\n"
        "`/reset` — сбросить баллы\n"
        "`/round` — перейти к следующему раунду",
        parse_mode="Markdown"
    )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TEAMS
    TEAMS = []
    await update.message.reply_text(
        "🛠️ *Создание команд*\n\n"
        "Формат: `название, алиас1, алиас2, ...`\n"
        "Каждая команда — с новой строки.\n\n"
        "Пример:\n"
        "`ФЕРРАмоны, ферра, скудерия\n"
        "Кванториум, квант\n"
        "Питонята, питон`\n\n"
        "Отправьте список или `/done`.",
        parse_mode="Markdown"
    )
    context.user_data["awaiting_setup"] = True

async def handle_setup_lines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_setup"):
        return

    text = update.message.text.strip()
    lines = text.split("\n")

    for line in lines:
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if not parts:
            continue
        name = parts[0]
        aliases = parts[1:] if len(parts) > 1 else []
        TEAMS.append({
            "id": len(TEAMS) + 1,
            "name": name,
            "aliases": aliases,
            "score": 0
        })

    await update.message.reply_text(
        f"✅ Добавлено {len(lines)} команд(ы). Всего: {len(TEAMS)}\n"
        "Отправьте ещё или `/done` для завершения."
    )

async def done_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_setup"):
        await update.message.reply_text("Сначала вызовите /setup")
        return

    context.user_data["awaiting_setup"] = False
    if not TEAMS:
        await update.message.reply_text("⚠️ Не создано ни одной команды.")
        return

    msg = "🏁 *Команды готовы!*\n\n"
    for t in TEAMS:
        aliases = ", ".join(t["aliases"]) if t["aliases"] else "—"
        msg += f"`{t['id']}.` *{t['name']}* (алиасы: `{aliases}`)\n"
    msg += "\nТеперь можно использовать `/add`, `/table`, `/round`"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not TEAMS:
        await update.message.reply_text("❌ Сначала создайте команды: /setup")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Формат: `/add <название> <баллы>`\n"
            "Пример: `/add ферра 10` или `/add 1 -5`",
            parse_mode="Markdown"
        )
        return

    *name_parts, points_str = args
    team_name = " ".join(name_parts)
    try:
        points = int(points_str)
    except ValueError:
        await update.message.reply_text("❌ Баллы должны быть целым числом.")
        return

    team = find_team(team_name)
    if not team:
        names = ", ".join([t["name"] for t in TEAMS])
        await update.message.reply_text(
            f"❌ Команда «{team_name}» не найдена.\nДоступные: {names}"
        )
        return

    old_score = team["score"]
    team["score"] += points
    sign = "+" if points >= 0 else ""
    await update.message.reply_text(
        f"✅ *{team['name']}*: {old_score} → {team['score']} pts\n"
        f"Изменение: {sign}{points}",
        parse_mode="Markdown"
    )

async def show_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not TEAMS:
        await update.message.reply_text("❌ Сначала создайте команды: /setup")
        return

    sorted_teams = sorted(TEAMS, key=lambda t: t["score"], reverse=True)
    msg = f"🏆 *Раунд {ROUND} / {MAX_ROUNDS}*\n\n"
    for i, team in enumerate(sorted_teams, 1):
        medal = ""
        if i == 1: medal = "🥇 "
        elif i == 2: medal = "🥈 "
        elif i == 3: medal = "🥉 "
        msg += f"{i}. {medal}{team['name']}: *{team['score']}*\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reset_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for team in TEAMS:
        team["score"] = 0
    await update.message.reply_text("🔄 Все баллы сброшены!")

async def next_round(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ROUND
    if ROUND < MAX_ROUNDS:
        ROUND += 1
        await update.message.reply_text(f"⏭️ Раунд изменён на *{ROUND}*", parse_mode="Markdown")
    else:
        await update.message.reply_text("🏁 Достигнут последний раунд.")

# === HTTP-СЕРВЕР ДЛЯ САЙТА ===

class ScoresHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            # Отдаём index.html
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except FileNotFoundError:
                self.send_error(404, "index.html not found")
            except Exception as e:
                self.send_error(500, f"Server error: {e}")
        elif self.path == "/api/scores":
            # API: вернуть данные
            data = {
                "round": ROUND,
                "max_rounds": MAX_ROUNDS,
                "teams": [
                    {
                        "id": t["id"],
                        "name": t["name"],
                        "score": t["score"],
                    }
                    for t in TEAMS
                ],
            }
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        else:
            self.send_error(404)

def run_http_server(port=8000):
    server_address = ("localhost", port)
    httpd = HTTPServer(server_address, ScoresHandler)
    print(f"🌐 HTTP-сервер запущен: http://localhost:{port}")
    httpd.serve_forever()

# Запуск HTTP-сервера в фоновом потоке
http_thread = threading.Thread(target=run_http_server, daemon=True)
http_thread.start()

# === ЗАПУСК БОТА ===
def main():
    TELEGRAM_TOKEN = "8404196996:AAGZUfdlGNqZ6S-zmnaV7Tf5_WlaNYGq4cg"
    if not TELEGRAM_TOKEN:
        print("❗ Установите TELEGRAM_TOKEN")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("done", done_setup))
    app.add_handler(CommandHandler("add", add_points))
    app.add_handler(CommandHandler("table", show_table))
    app.add_handler(CommandHandler("reset", reset_scores))
    app.add_handler(CommandHandler("round", next_round))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setup_lines))

    print("✅ Бот запущен!")
    print("Откройте Telegram и напишите /start")
    print("Сайт: http://localhost:8000")
    app.run_polling()

if __name__ == "__main__":
    main()