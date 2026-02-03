import asyncio
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types.input_file import FSInputFile

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = "8312766603:AAH2e00Ga-PxCLpaT1ef_eAG4kjl75yNEjs"

# путь к python (лучше из venv)
PYTHON_BIN = r"C:\Users\rika\Documents\code\iherb_parser\.venv\Scripts\python.exe"
# PYTHON_BIN = "python3"  # если без venv

SCRIPT_PATH = r"C:\Users\rika\Documents\code\iherb_parser\main.py"

DATA_DIR = Path("C:/Users/rika/Documents/iherb_parser_data")

# ===============================================


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def find_latest_zip(folder: Path) -> Path | None:
    folder = Path(folder)
    zips = list(folder.glob("*.zip"))
    if not zips:
        return None
    return max(zips, key=lambda f: f.stat().st_mtime)



@dp.message(Command("parse"))
async def parse_command(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ Формат: /parse <URL> <КІЛЬКІСТЬ>")
        return

    url = args[1]

    try:
        count = int(args[2])
        if count <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Кількість має бути додатнім числом")
        return

    await message.answer(f"⏳ Запускаю парсер...\n🔗 {url}\n📦 Кількість: {count}")

    # запускаем скрипт с неблокирующим stdout (-u чтобы лог был без буферизации)
    process = await asyncio.create_subprocess_exec(
        PYTHON_BIN, "-u",
        SCRIPT_PATH,
        str(count),
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # лог в реальном времени
    log_buffer = []
    while True:
        line = await process.stdout.readline()
        if not line:
            break

        text = line.decode(errors="ignore").strip()
        if text:
            log_buffer.append(text)

        # отправляем каждые 5 строк, чтобы не спамить
        if len(log_buffer) >= 5:
            await message.answer("📝 Лог:\n```\n" + "\n".join(log_buffer) + "\n```")
            log_buffer.clear()

    await process.wait()

    # отправляем оставшийся лог
    if log_buffer:
        await message.answer("📝 Лог:\n```\n" + "\n".join(log_buffer) + "\n```")

    # проверяем на ошибки
    if process.returncode != 0:
        stderr = await process.stderr.read()
        await message.answer(f"❌ Помилка виконання скрипта:\n```\n{stderr.decode()}\n```")
        return

    # ======= Отправка архива =======
    archive_path = find_latest_zip(DATA_DIR)
    if not archive_path or not archive_path.exists():
        await message.answer("⚠️ Архів не знайдено після парсингу")
        return

    try:
        # ⚡ Используем FSInputFile вместо InputFile
        file_to_send = FSInputFile(str(archive_path))
        await message.answer_document(
            document=file_to_send,
            caption=f"📦 Архів готовий: {archive_path.name}"
        )
    except Exception as e:
        await message.answer(f"⚠️ Не вдалося надіслати архів: {e}")
    await message.answer("✅ Парсинг завершено")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
