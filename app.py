import streamlit as st
import tempfile
import os
import nest_asyncio
import pdfplumber
import fitz  # PyMuPDF
import base64
import hmac
from openai import OpenAI
from llama_parse import LlamaParse

# --- NAPRAWA ASYNCIO ---
nest_asyncio.apply()

# --- KONFIGURACJA ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    LLAMA_CLOUD_API_KEY = st.secrets.get("LLAMA_CLOUD_API_KEY", None)
except:
    st.error("Brak kluczy API! Ustaw je w Streamlit Cloud Secrets.")
    st.stop()

st.set_page_config(page_title="SolidRules AI Workspace", page_icon="🛡️", layout="wide")

# --- CSS: PRO DESIGN ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp { background-color: #050505; }
        section[data-testid="stSidebar"] { background-color: #0c0c0c; border-right: 1px solid #1e1e1e; }
        .stTextInput input, .stTextArea textarea {
            background-color: #111111 !important; color: #e2e8f0 !important;
            border: 1px solid #333 !important; border-radius: 8px !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: #6366f1 !important; box-shadow: 0 0 0 1px #6366f1 !important;
        }
        div.stButton > button {
            background-color: #1e1e2e; color: white; border: 1px solid #333;
            border-radius: 8px; padding: 0.5rem 1rem; transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #6366f1; border-color: #6366f1; color: white;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(to right, #4f46e5, #6366f1); border: none;
        }
        h1, h2, h3 { color: #f8fafc !important; font-weight: 600 !important; }
        p, li, label, .stMarkdown { color: #94a3b8 !important; }
        .stAlert { background-color: #0c0c0c; border: 1px solid #333; color: #cbd5e1; }
        .stSpinner > div { border-top-color: #6366f1 !important; }
    </style>
""", unsafe_allow_html=True)

# --- ZABEZPIECZENIE HASŁEM ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["APP_PASSWORD"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("### 🔒 SolidRules Protected Workspace")
    st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Invalid Access Code.")
    return False

if not check_password():
    st.stop()

# --- TŁUMACZENIA & PROMPT ---
translations = {
    "PL": {
        "title": "SolidRules: Inżynierski Workspace AI",
        "sidebar_title": "🛡️ SolidRules v4.0 (Universal)",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Twoje zapytanie inżynierskie:",
        "placeholder": "Np. Jak obliczyć wytrzymałość spoiny pachwinowej? ALBO (jeśli wgrałeś plik): Jaki gwint ma ta śruba?",
        "button": "🚀 Generuj Odpowiedź",
        "upload_label": "📂 (Opcjonalnie) Wgraj Dokumentację / Rysunek (PDF)",
        "status_no_file": "🧠 Tryb: Wiedza Ogólna (GPT-4o)",
        "status_file": "📄 Tryb: Analiza Dokumentacji ({pages} str.)",
        "report_header": "### 💡 Raport Inżynierski",
        "disclaimer": "⚠️ **Nota prawna:** System wspomagania decyzji. Wymagana weryfikacja inżynierska.",
        
        # --- PROMPT UNIWERSALNY (Z OBSŁUGĄ BRAKU PLIKU) ---
        "system_prompt": """Jesteś Głównym Inżynierem. 
        
        STATUS DANYCH WEJŚCIOWYCH:
        - Dokumentacja: {has_docs}
        
        TWOJE TRYBY DZIAŁANIA (Wybierz sam):

        TRYB A: WIEDZA OGÓLNA (Gdy brak dokumentacji lub pytanie jest ogólne)
        - Użyj swojej wiedzy inżynierskiej (normy ISO, DIN, fizyka, materiałoznawstwo).
        - Bądź precyzyjny. Podawaj wzory i typowe wartości.

        TRYB B: BIBLIOTEKARZ (Gdy jest dokumentacja i pytanie o dane)
        - Odczytaj dane z wgranego tekstu/wykresu.
        - Cytuj źródło (np. "Wg Tabeli na stronie 2").
        - Nie zmyślaj danych, których nie ma w pliku.

        TRYB C: EKSPERT TRIZ (Gdy jest problem/awaria)
        - Zdefiniuj sprzeczność.
        - Wybierz zasady TRIZ.
        - Jeśli jest plik: Sprawdź zgodność pomysłu z wgraną normą (Krytyk).
        
        FORMAT ODPOWIEDZI (Markdown):
        Bądź konkretny. Jeśli używasz TRIZ, zachowaj strukturę: Diagnoza -> Sprzeczność -> Koncepcje -> Ryzyko.
        Odpowiadaj po POLSKU."""
    },
    "EN": {
        "title": "SolidRules: Engineering AI Workspace",
        "sidebar_title": "🛡️ SolidRules v4.0 (Universal)",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Your engineering query:",
        "placeholder": "E.g. How to calculate weld strength? OR (if file uploaded): What is the thread pitch?",
        "button": "🚀 Generate Response",
        "upload_label": "📂 (Optional) Upload Docs / Drawing (PDF)",
        "status_no_file": "🧠 Mode: General Knowledge (GPT-4o)",
        "status_file": "📄 Mode: Document Analysis ({pages} pages)",
        "report_header": "### 💡 Engineering Report",
        "disclaimer": "⚠️ **Disclaimer:** AI Decision Support. Verification required.",
        
        "system_prompt": """You are a Chief Engineer.
        
        INPUT STATUS:
        - Documentation Provided: {has_docs}
        
        YOUR MODES:
        MODE A: GENERAL KNOWLEDGE (No docs or general question)
        - Use engineering knowledge (ISO, DIN, Physics).
        
        MODE B: LIBRARIAN (Docs present + Data lookup)
        - Read specific data from text/vision.
        - Cite source.
        
        MODE C: TRIZ EXPERT (Problem Solving)
        - Define contradiction.
        - Apply TRIZ principles.
        - If docs present: Check compliance.
        
        Answer in ENGLISH."""
    }
}

# --- FUNKCJE BACKENDOWE ---
def pdf_to_images_base64(file_bytes):
    images_base64 = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            images_base64.append(img_b64)
    except Exception as e: st.error(f"Img Error: {e}")
    return images_base64

@st.cache_data(show_spinner=False)
def parse_hybrid(file_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name
    text_content = ""
    engine_used = "PDFPlumber"
    if LLAMA_CLOUD_API_KEY:
        try:
            parser = LlamaParse(api_key=LLAMA_CLOUD_API_KEY, result_type="markdown", premium_mode=True, language="pl")
            docs = parser.load_data(tmp_path)
            if docs:
                text_content = "\n\n".join([d.text for d in docs])
                engine_used = "LlamaParse"
        except: pass
    if not text_content or len(text_content) < 50:
        try:
            with pdfplumber.open(tmp_path) as pdf:
                for p in pdf.pages: text_content += (p.extract_text() or "") + "\n"
        except: pass
    os.remove(tmp_path)
    return text_content, engine_used

# --- UI ---
with st.sidebar:
    lang = st.radio("Language / Język:", ["PL", "EN"], horizontal=True)
    t = translations[lang]
    st.header(t["sidebar_title"])
    st.markdown("---")
    
    # 1. WGRYWANIE (Teraz w Sidebarze dla czystości)
    uploaded_file = st.file_uploader(t["upload_label"], type=["pdf"])
    
    st.markdown("---")
    st.caption(t["footer"])

# --- GŁÓWNA STRONA ---
st.title(t["title"])

# ZMIENNE STANU (DLA LOGIKI BEZ PLIKU)
pdf_text_context = ""
pdf_images_list = []
has_file = False

# PRZETWARZANIE PLIKU (TYLKO JEŚLI JEST)
if uploaded_file is not None:
    has_file = True
    with st.spinner("⚙️ Analiza dokumentacji..."):
        file_bytes = uploaded_file.getvalue()
        pdf_text_context, engine_name = parse_hybrid(file_bytes)
        pdf_images_list = pdf_to_images_base64(file_bytes)
        
    # Wskaźnik statusu
    st.info(t["status_file"].format(pages=len(pdf_images_list)))
    with st.expander("Podgląd (Vision AI)"):
        if pdf_images_list: st.image(base64.b64decode(pdf_images_list[0]), width=300)
else:
    # Wskaźnik statusu "Bez pliku"
    st.info(t["status_no_file"])

# 2. SEKCJA PYTANIA (ZAWSZE WIDOCZNA)
problem = st.text_area(t["label_problem"], height=100, placeholder=t["placeholder"])
generate_button = st.button(t["button"], type="primary", use_container_width=True)

if generate_button and problem:
    with st.spinner("🧠 Analiza..."):
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Formatowanie Promptu
        doc_status = "TAK (Używaj danych z pliku)" if has_file else "NIE (Używaj wiedzy ogólnej)"
        final_system_prompt = t["system_prompt"].format(has_docs=doc_status)
        
        messages = [{"role": "system", "content": final_system_prompt}]
        
        # Budowanie treści użytkownika
        user_text = f"PYTANIE: {problem}\n"
        if has_file and pdf_text_context:
            user_text += f"\n--- KONTEKST PLIKU (OCR) ---\n{pdf_text_context[:40000]}\n"
            
        user_content = [{"type": "text", "text": user_text}]
        
        # Dodawanie obrazów (Tylko jeśli są)
        if has_file and pdf_images_list:
            for i, img in enumerate(pdf_images_list[:3]):
                user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
                
        messages.append({"role": "user", "content": user_content})

        # Wywołanie API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.4 # Balans: Kreatywność (TRIZ) vs Fakty (Normy)
        )
        
        # Wyświetlanie
        st.markdown(t["report_header"])
        report_text = response.choices[0].message.content
        st.markdown(report_text)
        
        # Pobieranie
        st.download_button("📥 Pobierz Raport", report_text, "SolidRules_Report.md", "text/markdown")
        
        st.warning(t["disclaimer"])
        
elif generate_button:
    st.warning("⚠️ Wpisz pytanie, aby rozpocząć.")
