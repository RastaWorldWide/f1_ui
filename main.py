# f1_bot.py — F1 Team Control Bot + Web Dashboard (готов к работе)
import re
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === ГЛОБАЛЬНЫЕ ДАННЫЕ ===
ROUND = 1
MAX_ROUNDS = 11
ROUND_ANIMATION_TRIGGER = False
_reset_timer = None

# 🏁 Список команд — в точности как в твоём HTML
TEAMS = [
    {"id": 1, "name": "WILLIAMS",      "aliases": ["williams", "виллиамс", "вилл"], "score": 0},
    {"id": 2, "name": "MERCEDES",      "aliases": ["mercedes", "мерседес", "мерс"], "score": 0},
    {"id": 3, "name": "MCLAREN",       "aliases": ["mclaren", "макларен", "мак"],   "score": 0},
    {"id": 4, "name": "FERRARI",       "aliases": ["ferrari", "феррари", "скудерия"], "score": 0},
    {"id": 5, "name": "SITRAK",        "aliases": ["sitrak", "ситрак"],              "score": 0},
    {"id": 6, "name": "RED BULL",      "aliases": ["redbull", "ред булл", "булл"],   "score": 0},
    {"id": 7, "name": "HOWO",          "aliases": ["howo", "хоуо"],                  "score": 0},
    {"id": 8, "name": "ASTON MARTIN",  "aliases": ["aston", "астон", "астонмартин"], "score": 0},
    {"id": 9, "name": "LADA",          "aliases": ["лада", "lada", "ваз"],           "score": 0},
    {"id": 10, "name": "AURUS",        "aliases": ["aurus", "аурус"],                "score": 0},
    {"id": 11, "name": "БАЗ",          "aliases": ["баз", "baz", "камаз"],           "score": 0},
]

def normalize(text: str) -> str:
    return re.sub(r'[^а-яa-z0-9]', '', text.lower())

def find_team(query: str):
    q = normalize(query)
    for team in TEAMS:
        if q == str(team["id"]) or any(q == normalize(a) for a in team["aliases"]):
            return team
    return None

# === КОМАНДЫ ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏎️ *New Year'js Grand Prix — Live Control*\n\n"
        "`/add <команда> <баллы>` — изменить счёт\n"
        "`/table` — текущая таблица\n"
        "`/reset` — сбросить все баллы\n"
        "`/round` — запустить анимацию гонки!",
        parse_mode="Markdown"
    )

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Формат: `/add <команда> <баллы>`\nПример: `/add мерс 10`", parse_mode="Markdown")
        return
    *name_parts, pts_str = context.args
    team_name = " ".join(name_parts)
    team = find_team(team_name)
    if not team:
        names = ", ".join(t["name"] for t in TEAMS)
        await update.message.reply_text(f"❌ Не найдена команда «{team_name}».\nВозможные: {names}")
        return
    try:
        pts = int(pts_str)
    except ValueError:
        await update.message.reply_text("❌ Баллы должны быть целым числом.")
        return
    old = team["score"]
    team["score"] += pts
    sign = "+" if pts >= 0 else ""
    await update.message.reply_text(
        f"✅ *{team['name']}*: {old} → {team['score']} pts\nИзменение: {sign}{pts}",
        parse_mode="Markdown"
    )

async def show_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_teams = sorted(TEAMS, key=lambda t: t["score"], reverse=True)
    msg = f"🏆 *Раунд {ROUND} / {MAX_ROUNDS}*\n\n"
    for i, t in enumerate(sorted_teams, 1):
        medal = ""
        if i == 1: medal = "🥇 "
        elif i == 2: medal = "🥈 "
        elif i == 3: medal = "🥉 "
        msg += f"{i}. {medal}{t['name']}: *{t['score']}*\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reset_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for team in TEAMS:
        team["score"] = 0
    await update.message.reply_text("🔄 Все баллы сброшены!")

# === АНИМАЦИЯ /round ===


def _reset_round_flag():
    global ROUND_ANIMATION_TRIGGER
    ROUND_ANIMATION_TRIGGER = False
    print("🔄 Анимация /round: флаг сброшен")


async def trigger_round_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ROUND_ANIMATION_TRIGGER, _reset_timer

    # Отменяем предыдущий таймер, если он ещё не сработал
    if _reset_timer and _reset_timer.is_alive():
        _reset_timer.cancel()

    # Запускаем анимацию
    ROUND_ANIMATION_TRIGGER = True
    await update.message.reply_text(
        f"🏁 *Раунд {ROUND}: СТАРТ ГОНКИ!* 🏎️💨\n"
        "Табло на сайте начинает анимацию пересортировки…",
        parse_mode="Markdown"
    )
    print("▶️ Анимация /round: флаг ВКЛЮЧЁН")

    # Сбрасываем через 5 секунд
    _reset_timer = threading.Timer(5.0, _reset_round_flag)
    _reset_timer.start()

# === HTTP-СЕРВЕР ===

import os  # ← убедись, что импортировано

class ScoresHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Корень
        if self.path == "/":
            self.serve_file("index.html", "text/html")

        # 2. API
        elif self.path == "/api/scores":
            data = {
                "round": ROUND,
                "max_rounds": MAX_ROUNDS,
                "trigger_round": ROUND_ANIMATION_TRIGGER,
                "teams": [{"id": t["id"], "name": t["name"], "score": t["score"]} for t in TEAMS],
            }
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # 3. Статика: css/, img/, js/
        else:
            # Убираем начальный /
            path = self.path.lstrip('/')
            # Безопасность: запрещаем .. и /
            if ".." in path or path.startswith("/"):
                self.send_error(403, "Forbidden")
                return

            # Проверяем существование
            if os.path.isfile(path):
                self.serve_file(path)
            else:
                self.send_error(404, f"File not found: {path}")

    def serve_file(self, path, content_type=None):
        try:
            # Определяем Content-Type, если не задан
            if content_type is None:
                if path.endswith('.css'):
                    content_type = 'text/css'
                elif path.endswith('.js'):
                    content_type = 'application/javascript'
                elif path.endswith('.png'):
                    content_type = 'image/png'
                elif path.endswith('.jpg') or path.endswith('.jpeg'):
                    content_type = 'image/jpeg'
                else:
                    content_type = 'text/plain'

            with open(path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)

        except FileNotFoundError:
            self.send_error(404, f"File not found: {path}")
        except Exception as e:
            self.send_error(500, str(e))

def run_http_server():
    server = HTTPServer(("localhost", 8000), ScoresHandler)
    print("✅ HTTP-сервер запущен: http://localhost:8000")
    server.serve_forever()

# Запуск сервера в фоне
threading.Thread(target=run_http_server, daemon=True).start()

# === ЗАПУСК БОТА ===

def main():
    TOKEN = "8404196996:AAGZUfdlGNqZ6S-zmnaV7Tf5_WlaNYGq4cg"
    app = Application.builder().token(TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_points))
    app.add_handler(CommandHandler("table", show_table))
    app.add_handler(CommandHandler("reset", reset_scores))
    app.add_handler(CommandHandler("round", trigger_round_animation))

    print("✅ Бот запущен!")
    print("👉 Напишите в Telegram: /start")
    print("📺 Сайт: http://localhost:8000")
    app.run_polling()

if __name__ == "__main__":
    main()