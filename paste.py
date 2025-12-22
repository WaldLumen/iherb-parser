import os
import time
import pyautogui
import pyperclip
from PIL import Image
import io
import win32clipboard

def copy_image_to_clipboard(image_path):
    try:
        image = Image.open(image_path)
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"Ошибка при копировании изображения: {e}")

dir_path = os.path.expanduser("C:/Users/sylv/Documents/iherb_parser_data")
files = sorted(f for f in os.listdir(dir_path) if f.endswith('.jpg'))

for i in range(len(files)):
    jpg_path = os.path.join(dir_path, f"{i}.jpg")
    txt_path = os.path.join(dir_path, f"{i}.txt")

    if os.path.exists(jpg_path) and os.path.exists(txt_path):
        print(f"Отправляется {i}.jpg и {i}.txt")
        copy_image_to_clipboard(jpg_path)
        time.sleep(2)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(2)

        # Можно убрать правые клики, если они не нужны
        pyautogui.rightClick()
        time.sleep(2)
        pyautogui.click()
        time.sleep(2)

        with open(txt_path, encoding='utf-8') as f:
            pyperclip.copy(f.read())

        time.sleep(1)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)
