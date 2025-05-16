import streamlit as st
from PIL import Image
import tempfile
import os
from ultralytics import YOLO, RTDETR
import cv2
import sqlite3
import datetime
import base64
from io import BytesIO

# Интерфейс
st.set_page_config(page_title="Детекция строительной техники", layout="centered")
st.title("🚧 Детекция строительной техники")

import requests
import os

# Функция для скачивания файла с Google Drive
def download_file_from_google_drive(file_id, destination):
    URL = "https://drive.google.com/uc?id={}&export=download".format(file_id)
    session = requests.Session()
    response = session.get(URL, stream=True)
    token = None

    # Проверка на подтверждение большого файла
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            token = value
            break

    if token:
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    # Скачивание файла
    CHUNK_SIZE = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                f.write(chunk)

# ID файлов из Google Drive ссылок
MODEL_FILE_IDS = {
    "YOLOv11": "13dVgKfjX87HmKc1nwnQDqASOY0n0m-XQ",
    "RT-DETR": "1-qPgDJHoR5iEiFuYbiWgZs7sOFMN0yrk"
}

# Локальные пути к файлам весов
MODEL_PATHS = {
    "YOLOv11": "epoch60.pt",
    "RT-DETR": "best-24.pt",
}

# Проверка и скачивание весов
for model_name, file_id in MODEL_FILE_IDS.items():
    if not os.path.exists(MODEL_PATHS[model_name]):
        print(f"Скачивание весов для модели {model_name}...")
        download_file_from_google_drive(file_id, MODEL_PATHS[model_name])
        print(f"✅ Веса для {model_name} скачаны!")

@st.cache_resource
def load_model(path: str, option: str):
    if option == "RT-DETR":
        return RTDETR(path)
    else:
        return YOLO(path)

# Выбор модели и порога уверенности
# ———————————————————————————————————————————————
model_option = st.selectbox("Выберите модель детекции", list(MODEL_PATHS.keys()))
conf_threshold = st.slider(
    "Порог уверенности (confidence threshold)",
    min_value=0.0, max_value=1.0, value=0.25, step=0.05
)

# ———————————————————————————————————————————————
# Загружаем выбранную модель
# ———————————————————————————————————————————————
model = load_model(MODEL_PATHS[model_option], model_option)

# Подключение к БД SQLite
DB_PATH = "detections.db"

def save_detection_to_db(detected_class, confidence, img_pil):
    # Конвертация изображения в Base64
    buffered = BytesIO()
    img_pil.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Запись в БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections (detected_class, confidence, detection_datetime, image_base64)
        VALUES (?, ?, ?, ?)
    """, (detected_class, confidence, datetime.datetime.now().isoformat(), img_str))

    conn.commit()
    conn.close()

# ———————————————————————————————————————————————
# Загрузка и отображение изображения
# ———————————————————————————————————————————————
uploaded_file = st.file_uploader(
    "📤 Перетащите или выберите изображение",
    type=["jpg", "jpeg", "png"]
)


if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    st.image(img, caption="Загруженное изображение", use_container_width=True)

    if st.button("🚀 Запустить детекцию"):
        with st.spinner("Распознавание..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                img.save(tmp.name)
                results = model(tmp.name, conf=conf_threshold)[0]
                annotated = results.plot()
            os.remove(tmp.name)

        annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        annotated_pil = Image.fromarray(annotated_rgb)

        st.image(annotated_rgb, caption=f"Результат детекции ({model_option})", use_container_width=True)

        st.subheader("📋 Детекции:")
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if conf >= conf_threshold:
                label = results.names.get(cls_id, f"Class {cls_id}")
                st.write(f"- {label} (ID: {cls_id}): {conf:.2%}")

                # Записываем в базу каждую детекцию вместе с изображением
                save_detection_to_db(label, conf, annotated_pil)

        st.success("✅ Результаты и изображения успешно записаны в базу данных!")


