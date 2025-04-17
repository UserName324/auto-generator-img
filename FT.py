import tkinter as tk
from tkinter import messagebox, PhotoImage
from PIL import Image, ImageTk
import requests
import datetime
import os
import base64
import openai

API_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
SAVE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_images")
MODELS = ["dreamshaper8", "revAnimated", "realisticVisionV51"]

API_KEY_FILE = "API.txt"
if os.path.exists(API_KEY_FILE):
    with open(API_KEY_FILE, "r") as f:
        OPENAI_API_KEY = f.read().strip()
else:
    raise FileNotFoundError("Файл API.txt не найден в текущей директории.")

client = openai.OpenAI(api_key=OPENAI_API_KEY)
os.makedirs(SAVE_FOLDER, exist_ok=True)

current_images = []

def check_openai_status():
    try:
        client.models.list()
        return True
    except Exception as e:
        print("OpenAI API недоступен:", e)
        return False

def generate_prompt(topic):
    try:
        system_prompt = (
            "Ты генератор визуальных промптов для Stable Diffusion. "
            "Твоя задача — создавать глубокие, проработанные промпты, соответствующие best practices prompt engineering. "
            "Упор на: композицию, ракурс, окружение, эмоции, стиль, освещение, материалы, атмосферу. "
            "Формат вывода: Prompt: [визуальные теги через запятую, от главного к второстепенному]; Negative prompt: [исключения, через запятую]. "
            "Не добавляй описаний или пояснений. Начинай Prompt с: 'masterpiece, best quality, high detail, 8k, cinematic lighting'."
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Создай промпт для: {topic}"}
            ]
        )

        full_reply = response.choices[0].message.content.strip()
        parts = full_reply.split("Negative prompt:")

        prompt = parts[0].replace("Prompt:", "").strip()
        negative_prompt = parts[1].strip() if len(parts) > 1 else ""
        return prompt, negative_prompt

    except Exception as e:
        print("Ошибка при обращении к OpenAI:", e)
        return topic, ""

def send_to_sd(prompt, negative_prompt, mode, model):
    if mode == "Портрет":
        width, height = 768, 960
    else:
        width, height = 768, 768

    enable_hr = True
    hr_scale = 2
    hr_upscaler = "Latent"

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": 30,
        "cfg_scale": 7.5,
        "width": width,
        "height": height,
        "sampler_index": "DPM++ 2M Karras"
    }
    response = requests.post(API_URL, json=payload)
    try:
        r = response.json()
    except Exception as e:
        print("❌ Ошибка при разборе ответа JSON:", e)
        print("Ответ:", response.text)
        return None

    print("🔍 Ответ от SD API:", r)

    if "images" not in r or not r["images"]:
        print("❌ Нет изображений в ответе:", r)
        return None

    b64_img = r["images"][0]
    if b64_img.startswith("data:image"):
        b64_img = b64_img.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(b64_img)
    except Exception as e:
        print("❌ Ошибка декодирования base64:", e)
        return None

    filename = datetime.datetime.now().strftime(f"%Y-%m-%d_%H-%M-%S_{model}.png")
    path = os.path.join(SAVE_FOLDER, filename)

    try:
        with open(path, "wb") as f:
            f.write(image_bytes)
    except Exception as e:
        print("❌ Ошибка при сохранении файла:", e)
        return None

    return path

    if "images" in r:
        b64_img = r["images"][0]
        if b64_img.startswith("data:image"):
            b64_img = b64_img.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_img)

        filename = datetime.datetime.now().strftime(f"%Y-%m-%d_%H-%M-%S_{model}.png")
        path = os.path.join(SAVE_FOLDER, filename)

        with open(path, "wb") as f:
            f.write(image_bytes)

        return path
    else:
        return None

def show_image(path):
    img = Image.open(path).resize((256, 256))
    img_tk = ImageTk.PhotoImage(img)

    container = tk.Frame(image_frame, bg="#1e1e1e")
    label = tk.Label(container, image=img_tk, bg="#1e1e1e")
    label.image = img_tk
    label.pack()
    caption = tk.Label(container, text=os.path.basename(path), bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 8))
    caption.pack(pady=5)
    container.pack(side=tk.LEFT, padx=10)

    def open_fullscreen():
        top = tk.Toplevel()
        top.title("Полный размер")
        full_img = Image.open(path)
        full_tk = ImageTk.PhotoImage(full_img)
        lbl = tk.Label(top, image=full_tk)
        lbl.image = full_tk
        lbl.pack()

    label.bind("<Button-1>", lambda e: open_fullscreen())
    image_frame.pack(pady=10)

def generate():
    topic = entry.get()
    mode = mode_var.get()

    if not topic:
        messagebox.showwarning("Внимание", "Введите тему для генерации.")
        return

    btn.config(state="disabled")
    status_label.config(text="Проверка подключения к OpenAI...")

    if not check_openai_status():
        status_label.config(text="❌ Ошибка: нет доступа к OpenAI API")
        btn.config(state="normal")
        return
    else:
        status_label.config(text="✅ Подключение к OpenAI в порядке")

    prompt, negative = generate_prompt(topic)
    prompt_display.delete("1.0", tk.END)
    prompt_display.insert(tk.END, f"Prompt:\n{prompt}\n\nNegative prompt:\n{negative}")
    status_label.config(text="Генерация изображений с тремя моделями...")

    for widget in image_frame.winfo_children():
        widget.destroy()

    for model in MODELS:
        path = send_to_sd(prompt, negative, mode, model)
        if path:
            show_image(path)

    status_label.config(text="Готово! Все изображения сгенерированы.")
    btn.config(state="normal")

root = tk.Tk()
root.title("AI Prompt to SD")
root.geometry("900x680")
root.configure(bg="#1e1e1e")

style_options = {"bg": "#1e1e1e", "fg": "#ffffff", "font": ("Segoe UI", 10)}

label = tk.Label(root, text="Введите тему для генерации изображения:", **style_options)
label.pack(pady=10)

entry = tk.Entry(root, width=60, bg="#2d2d2d", fg="#ffffff", insertbackground="white", font=("Segoe UI", 10))
entry.pack(pady=5)

mode_var = tk.StringVar(value="Портрет")
mode_label = tk.Label(root, text="Выберите режим:", **style_options)
mode_label.pack()
mode_dropdown = tk.OptionMenu(root, mode_var, "Портрет", "Композиция")
mode_dropdown.config(bg="#2d2d2d", fg="#ffffff", font=("Segoe UI", 10), activebackground="#3a3a3a")
mode_dropdown.pack(pady=5)

btn = tk.Button(root, text="Сгенерировать", command=generate, bg="#3a72ff", fg="white", font=("Segoe UI", 10, "bold"))
btn.pack(pady=10)

open_folder_btn = tk.Button(root, text="Открыть папку с изображениями", command=lambda: os.startfile(SAVE_FOLDER), bg="#2d2d2d", fg="white", font=("Segoe UI", 9))
open_folder_btn.pack(pady=5)

status_label = tk.Label(root, text="", **style_options)
status_label.pack(pady=5)

prompt_display = tk.Text(root, height=10, width=80, wrap="word", bg="#2d2d2d", fg="#ffffff", insertbackground="white", font=("Consolas", 10))
prompt_display.pack(pady=5)

image_frame = tk.Frame(root, bg="#1e1e1e")
image_frame.pack(pady=10)

root.mainloop()
