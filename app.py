import streamlit as st
import os
import re
import time
import asyncio
import edge_tts
import google.generativeai as genai
from datetime import datetime, timedelta

# Налаштування сторінки Streamlit
st.set_page_config(page_title="Ostap Engine v4.7 PRO", page_icon="🎙️", layout="wide")

# --- СИСТЕМА МОНЕТИЗАЦІЇ ТА КОНТРОЛЮ ЧАСУ (15 ХВИЛИН) ---
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.now()

if "ad_watched" not in st.session_state:
    st.session_state.ad_watched = False

# Рахуємо, скільки часу залишилося до кінця 15-хвилинної сесії
time_elapsed = datetime.now() - st.session_state.session_start_time
time_left = timedelta(minutes=15) - time_elapsed
minutes_left = max(0, int(time_left.total_seconds() // 60))
seconds_left = max(0, int(time_left.total_seconds() % 60))

# Перевірка: якщо 15 хвилин минуло, блокуємо інтерфейс рекламою
is_blocked = time_left.total_seconds() <= 0

if is_blocked:
    st.error("🛑 ДОСТУП ТИМЧАСОВО ОБМЕЖЕНО")
    st.subheader("⌛ Ваша безкоштовна 15-хвилинна сесія використання 'Остапа' вичерпана.")
    st.write("Щоб продовжити безкоштовну чистку та озвучку тексту ще на 15 хвилин, будь ласка, перегляньте рекламний спонсорський ролик.")
    
    # Кнопка запуску імітації реклами для користувача додатка
    if st.button("📺 Подивитися рекламу (30 сек) і відкрити доступ", type="primary"):
        with st.spinner("🎬 Завантаження та перегляд рекламного ролика... Будь ласка, не закривайте сторінку."):
            # Імітуємо 5 секунд реклами, щоб користувач не збожеволів, але відчув обмеження
            time.sleep(5) 
        st.session_state.session_start_time = datetime.now()
        st.session_state.ad_watched = True
        st.success("✅ Дякуємо за перегляд! Доступ відновлено на 15 хвилин. Перезавантаження...")
        time.sleep(2)
        st.rerun()
        
    st.stop()  # Повністю зупиняємо рендеринг додатка нижче, поки не подивляться рекламу

# --- ОСНОВНИЙ ФУНКЦІОНАЛ ДОДАТКА ---
st.title("🎙️ Ostap Engine v4.7 PRO")
st.write(f"⏱️ Залишок вашої робочої сесії перед наступною рекламою: **{minutes_left} хв. {seconds_left} сек.**")

# Підхоплюємо ключ із закритих секретів сервера
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    st.sidebar.warning("⚠️ Ключ безпеки системи не налаштований у Secrets.")
    GEMINI_API_KEY = st.sidebar.text_input("Введіть ваш Gemini API Key для тесту:", type="password")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("Система очікує активації шлюзу Google API!")

# --- ФУНКЦІЇ ОБРОБКИ ТЕКСТУ ---
def pre_clean_text(text):
    text = re.sub(r'[\r\n]+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def clean_with_gemini(text_chunk):
    if not GEMINI_API_KEY:
        return text_chunk
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = (
        "Ти — елітний редактор українських аудіокниг. Перед тобою сирий текст, витягнутий з книги.\n"
        "ЗАВДАННЯ:\n"
        "1. Виправ розірвані слова та зліплені речення.\n"
        "2. Прибери колонтитули, номери сторінок та технічний непотріб.\n"
        "3. Розстав НАГОЛОСИ великою літерою в словах, де є ризик прочитати неправильно (наприклад: зАмок чи замОк, дорогОй чи дорОго).\n"
        "Поверни ТІЛЬКИ чистий відредагований текст книги. Без жодних твоїх коментарів чи вступів!"
    )
    
    try:
        response = model.generate_content(f"{prompt}\n\nТЕКСТ ДЛЯ ОБРОБКИ:\n{text_chunk}")
        return response.text.strip()
    except Exception as e:
        return f"Помилка шлюзу обробки тексту: {str(e)}"

# --- ФУНКЦІЇ ОЗВУЧКИ ---
async def text_to_speech_async(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_audio(text, voice="uk-UA-OstapNeural"):
    output_filename = "ostap_output.mp3"
    asyncio.run(text_to_speech_async(text, voice, output_filename))
    return output_filename

# --- ІНТЕРФЕЙС РОБОТИ З ТЕКСТОМ ---
text_input = st.text_area("Вставте текст книги або глави сюди для автоматичної обробки:", height=250)

col1, col2 = st.columns(2)
with col1:
    voice_option = st.selectbox(
        "Виберіть голос конвертації:",
        ["uk-UA-OstapNeural", "uk-UA-PolinaNeural"]
)
with col2:
    process_button = st.button("🚀 Обробити та конвертувати", type="primary")

if process_button and text_input:
    if not GEMINI_API_KEY:
        st.error("Неможливо почати обробку без активного API ключа!")
    else:
        with st.spinner("🤖 Остап чистить текст від сміття та виставляє наголоси..."):
            raw_clean = pre_clean_text(text_input)
            final_text = clean_with_gemini(raw_clean)
            
        st.subheader("📝 Текст готовий до читки:")
        st.info(final_text)
        
        with st.spinner("🎙️ Синтезатор мовлення генерує аудіопотік..."):
            audio_file = generate_audio(final_text, voice_option)
            
        st.success("🎉 Результат успішно згенеровано!")
        st.audio(audio_file)
        
        with open(audio_file, "rb") as file:
            st.download_button(
                label="📥 Скачати готовий MP3",
                data=file,
                file_name="ostap_book.mp3",
                mime="audio/mp3"
            )
