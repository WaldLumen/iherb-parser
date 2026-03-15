import asyncio
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types.input_file import FSInputFile

BOT_TOKEN = "8312766603:AAEvChLHAh9WE35hROu92Uv2yvkzqaKi5Xo"

PYTHON_BIN = r"C:\Users\rika\Documents\iherb-parser-main\.venv\Scripts\python.exe"
SCRIPT_PATH = r"C:\Users\rika\Documents\iherb-parser-main\main.py"

DATA_DIR = Path("C:/Users/rika/Documents/iherb_parser_data")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_state = {}
parser_lock = asyncio.Lock()


def find_latest_zip(folder: Path):

    zips = list(folder.glob("*.zip"))

    if not zips:
        return None

    return max(zips, key=lambda f: f.stat().st_mtime)


@dp.message(Command("parse"))
async def start_parse(message: Message):

    user_state[message.from_user.id] = {"step": "url"}

    await message.answer("🔗 Введіть URL категорії iHerb")


@dp.message()
async def dialog(message: Message):

    uid = message.from_user.id

    if uid not in user_state:
        return

    state = user_state[uid]

    if state["step"] == "url":

        state["url"] = message.text
        state["step"] = "count"

        await message.answer("📦 Скільки товарів парсити?")

        return

    if state["step"] == "count":

        try:
            state["count"] = int(message.text)
        except:
            await message.answer("❌ Введіть число")
            return

        state["step"] = "discount"

        await message.answer(
            "💸 Введіть знижку %\n"
            "0 = автоматично"
        )

        return

    if state["step"] == "discount":

        try:
            discount = int(message.text)
        except:
            await message.answer("❌ Введіть число")
            return

        url = state["url"]
        count = state["count"]

        del user_state[uid]

        if parser_lock.locked():
            await message.answer("⏳ Парсер вже працює")
            return

        async with parser_lock:

            await message.answer("🚀 Запускаю парсер...")

            process = await asyncio.create_subprocess_exec(
                PYTHON_BIN,
                "-u",
                SCRIPT_PATH,
                str(count),
                url,
                str(discount),
                stdout=asyncio.subprocess.PIPE
            )

            while True:

                line = await process.stdout.readline()

                if not line:
                    break

                print(line.decode().strip())

            await process.wait()

            archive = find_latest_zip(DATA_DIR)

            if archive:
                await message.answer_document(
                    FSInputFile(str(archive)),
                    caption="📦 Архів готовий"
                )

            await message.answer("✅ Парсинг завершено")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())