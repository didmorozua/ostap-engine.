import streamlit as st
import os
import re
import asyncio
import edge_tts
import google.generativeai as genai

# Налаштування сторінки Streamlit
st.set_page_config(page_title="Ostap Engine v4.6", page_icon="🎙️", layout="wide")

st.title("🎙️ Ostap Engine v4.6 — Автономна Студія")
st.write("Професійна чистка тексту через Gemini API та ультрашвидка озвучка")

# Отримуємо токен Gemini зі змінних оточення сервера або з поля введення
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    st.sidebar.warning("⚠️ Ключ Gemini API не знайдено в системі.")
    GEMINI_API_KEY = st.sidebar.text_input("Введіть ваш Gemini API Key вручну:", type="password")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("Будь ласка, додайте ваш золотий ключ Gemini API в бічній панелі, щоб додаток міг працювати!")

# --- ФУНКЦІЇ ОБРОБКИ ТЕКСТУ ---
def pre_clean_text(text):
    """ Базова технічна чистка від сміття """
    text = re.sub(r'[\r\n]+', '\n', text)  # Нормалізація переносу рядків
    text = re.sub(r'[ \t]+', ' ', text)    # Прибирання подвійних пробілів
    return text.strip()

def clean_with_gemini(text_chunk):
    """ Чистка тексту та розстановка наголосів через безкоштовну модель Gemini 1.5 Flash """
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
        return text_chunk  # Якщо впало — повертаємо оригінал, щоб черга не зупинялась

# --- ФУНКЦІЇ ОЗВУЧКИ ---
async def text_to_speech_async(text, voice, output_path):
    """ Асинхронний рендеринг звуку через Edge-TTS """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_audio(text, voice="uk-UA-OstapNeural"):
    """ Запуск озвучки та повернення результату """
    output_filename = "ostap_output.mp3"
    asyncio.run(text_to_speech_async(text, voice, output_filename))
    return output_filename

# --- ІНТЕРФЕЙС ДОДАТКА ---
text_input = st.text_area("Вставте текст книги або глави сюди:", height=300)

col1, col2 = st.columns(2)
with col1:
    voice_option = st.selectbox(
        "Виберіть голос для озвучки:",
        ["uk-UA-OstapNeural", "uk-UA-PolinaNeural"]
    )
with col2:
    process_button = st.button("🚀 Запустити Остапа на повну", type="primary")

if process_button and text_input:
    if not GEMINI_API_KEY:
        st.error("Неможливо почати обробку без API ключа!")
    else:
        with st.spinner("🤖 Остап зв'язується з мізками Google для чистки тексту..."):
            raw_clean = pre_clean_text(text_input)
            # Обробка через Gemini
            final_text = clean_with_gemini(raw_clean)
            
        st.subheader("📝 Результат чистки тексту та наголосів:")
        st.info(final_text)
        
        with st.spinner("🎙️ Запуск генерації звуку через сервери обробки..."):
            # Генерація MP3
            audio_file = generate_audio(final_text, voice_option)
            
        st.success("🎉 Аудіокнига готова! Можна слухати або скачати:")
        st.audio(audio_file)
        
        with open(audio_file, "rb") as file:
            st.download_button(
                label="📥 Скачати готовий MP3 файл",
                data=file,
                file_name="ostap_book.mp3",
                mime="audio/mp3"
            )                            
