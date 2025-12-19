# f1_bot.py — F1 Team Control Bot + Web Dashboard
import re
import json
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import nest_asyncio

# === Исправляем event loop для работы с Jupyter/PyCharm ===
nest_asyncio.apply()

# === ГЛОБАЛЬНЫЕ ДАННЫЕ ===
ROUND = 1
MAX_ROUNDS = 11
ROUND_ANIMATION_TRIGGER = False
FINAL_INDEX = None  # None = анимация не активна
_reset_timer = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # путь к папке с main.py

# 🏁 Список команд
TEAMS = [
    {"id": 1, "name": "WILLIAMS", "aliases": ["williams", "виллиамс", "вилл"], "score": 0},
    {"id": 2, "name": "MERCEDES", "aliases": ["mercedes", "мерседес", "мерс"], "score": 0},
    {"id": 3, "name": "MCLAREN", "aliases": ["mclaren", "макларен", "мак"], "score": 0},
    {"id": 4, "name": "FERRARI", "aliases": ["ferrari", "феррари", "скудерия"], "score": 0},
    {"id": 5, "name": "SITRAK", "aliases": ["sitrak", "ситрак"], "score": 0},
    {"id": 6, "name": "RED BULL", "aliases": ["redbull", "ред булл", "булл"], "score": 0},
    {"id": 7, "name": "HOWO", "aliases": ["howo", "хоуо"], "score": 0},
    {"id": 8, "name": "ASTON MARTIN", "aliases": ["aston", "астон", "астонмартин"], "score": 0},
    {"id": 9, "name": "LADA", "aliases": ["лада", "lada", "ваз"], "score": 0},
    {"id": 10, "name": "AURUS", "aliases": ["aurus", "аурус"], "score": 0},
    {"id": 11, "name": "БАЗ", "aliases": ["баз", "baz", "камаз"], "score": 0},
]

def normalize(text: str) -> str:
    return re.sub(r'[^а-яa-z0-9]', '', text.lower())

def find_team(name: str):
    """Ищем команду по названию или алиасам"""
    name = name.lower()
    for t in TEAMS:
        if name == t["name"].lower() or name in [a.lower() for a in t["aliases"]]:
            return t
    return None

# === КОМАНДЫ БОТА ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏎️ *New Year'js Grand Prix — Live Control*\n\n"
        "`/add <команда> <баллы>` — изменить счёт\n"
        "`/table` — текущая таблица\n"
        "`/reset` — сбросить все баллы\n"
        "`/round` — запустить анимацию гонки!\n"
        "`/final` — финальный отсчёт\n"
        "`/next` — показать следующую команду в финале",
        parse_mode="Markdown"
    )

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Формат: `/add <команда> <баллы>`", parse_mode="Markdown")
        return

    *name_parts, pts_str = context.args
    team_name = " ".join(name_parts)
    team = find_team(team_name)

    if not team:
        names = "\n".join([f"`{t['id']}.` {t['name']}" for t in TEAMS])
        await update.message.reply_text(
            f"❌ Команда «{team_name}» не найдена.\nДоступные команды:\n{names}",
            parse_mode="Markdown"
        )
        return

    try:
        pts = int(pts_str)
    except ValueError:
        await update.message.reply_text("❌ Баллы должны быть целым числом.")
        return

    old_score = team["score"]
    team["score"] += pts
    await update.message.reply_text(
        f"✅ *{team['name']}*: {old_score} → {team['score']} pts",
        parse_mode="Markdown"
    )

async def trigger_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FINAL_INDEX
    FINAL_INDEX = -2  # сброс
    await update.message.reply_text(
        "🎬 *ФИНАЛЬНЫЙ ОТСЧЁТ ЗАПУЩЕН!* \n"
        "➡️ Теперь используйте `/next`, чтобы раскрыть таблицу — с 11-го места до 1-го!",
        parse_mode="Markdown"
    )

async def next_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FINAL_INDEX

    sorted_teams = sorted(TEAMS, key=lambda t: t["score"], reverse=True)
    n = len(sorted_teams)  # = 11

    # Случай 1: финал ещё не начат — инициализируем и показываем первую команду (11-е место)
    if FINAL_INDEX == -2:
        FINAL_INDEX = n - 1  # 10 → 11-е место
        team = sorted_teams[FINAL_INDEX]
        position = FINAL_INDEX + 1
        await update.message.reply_text(f"🎬 *Финал начался!* \n➡️ {position}-е место: *{team['name']}*", parse_mode="Markdown")
        FINAL_INDEX -= 1  # готовимся к следующему вызову
        return

    # Случай 2: финал завершён
    if FINAL_INDEX < 0:
        await update.message.reply_text("🏁 Финал уже завершён. Используйте `/final`, чтобы начать заново.", parse_mode="Markdown")
        return

    # Случай 3: индекс вне диапазона (защита)
    if FINAL_INDEX >= n:
        await update.message.reply_text("❌ Ошибка: индекс вне диапазона.", parse_mode="Markdown")
        FINAL_INDEX = -2  # сброс к начальному состоянию
        return

    # Случай 4: нормальный шаг — показываем команду
    team = sorted_teams[FINAL_INDEX]
    position = FINAL_INDEX + 1
    await update.message.reply_text(f"➡️ {position}-е место: *{team['name']}*", parse_mode="Markdown")

    # Переход к следующей (выше)
    FINAL_INDEX -= 1

    # Проверка завершения после шага
    if FINAL_INDEX < 0:
        await update.message.reply_text("🏆 *Финал завершён! Победитель объявлен!*", parse_mode="Markdown")

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_teams = sorted(TEAMS, key=lambda t: t["score"], reverse=True)
    msg = "🏆 *Leaderboard*\n\n"
    for i, t in enumerate(sorted_teams, 1):
        medal = "   "
        if i == 1: medal = "🥇 "
        elif i == 2: medal = "🥈 "
        elif i == 3: medal = "🥉 "
        msg += f"{i:2}. {medal}{t['name']:<15} — *{t['score']:3}*\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reset_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for team in TEAMS:
        team["score"] = 0
    await update.message.reply_text("🔄 Все баллы сброшены!")

def _reset_round_flag():
    global ROUND_ANIMATION_TRIGGER
    ROUND_ANIMATION_TRIGGER = False
    print("🔄 Анимация /round: флаг сброшен")

async def trigger_round_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ROUND_ANIMATION_TRIGGER, _reset_timer
    if _reset_timer and _reset_timer.is_alive():
        _reset_timer.cancel()
    ROUND_ANIMATION_TRIGGER = True
    await update.message.reply_text(f"🏁 *Раунд {ROUND}: СТАРТ ГОНКИ!* 🏎️💨", parse_mode="Markdown")
    print("▶️ Анимация /round: флаг ВКЛЮЧЁН")
    _reset_timer = threading.Timer(5.0, _reset_round_flag)
    _reset_timer.start()

# === HTTP-СЕРВЕР ===
class ScoresHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path == "/":
            self.serve_file(os.path.join(BASE_DIR, "index.html"), "text/html")
        elif path == "/api/scores":
            data = {
                "round": ROUND,
                "max_rounds": MAX_ROUNDS,
                "trigger_round": ROUND_ANIMATION_TRIGGER,
                "teams": [{"id": t["id"], "name": t["name"], "score": t["score"]} for t in TEAMS],
            }
            self.send_json(data)
        elif path == "/api/final":
            data = {"final_index": FINAL_INDEX if FINAL_INDEX is not None else -1}
            self.send_json(data)
        else:
            file_path = os.path.join(BASE_DIR, path.lstrip("/"))
            if os.path.isfile(file_path):
                self.serve_file(file_path)
            else:
                self.send_error(404, f"File not found: {file_path}")

    def serve_file(self, path, content_type=None):
        try:
            if content_type is None:
                if path.endswith('.css'): content_type = 'text/css'
                elif path.endswith('.js'): content_type = 'application/javascript'
                elif path.endswith('.png'): content_type = 'image/png'
                else: content_type = 'text/plain'
            with open(path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

def run_http_server():
    server = HTTPServer(("localhost", 8000), ScoresHandler)
    print("✅ HTTP-сервер запущен: http://localhost:8000")
    server.serve_forever()

# === ЗАПУСК ===
async def main_async():
    # Запуск сервера в фоне
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, run_http_server)

    TOKEN = "8404196996:AAGZUfdlGNqZ6S-zmnaV7Tf5_WlaNYGq4cg"
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_points))
    app.add_handler(CommandHandler("round", trigger_round_animation))
    app.add_handler(CommandHandler("final", trigger_final))
    app.add_handler(CommandHandler("next", next_final))
    app.add_handler(CommandHandler("reset", reset_scores))
    app.add_handler(CommandHandler("leaderboard", show_leaderboard))

    print("✅ Бот запущен! /start")
    print("📺 Сайт: http://localhost:8000")

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main_async())
