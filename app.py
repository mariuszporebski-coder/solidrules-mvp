import streamlit as st
import tempfile
import os
import nest_asyncio
import pdfplumber
import fitz  # PyMuPDF
import base64
import hmac
import pandas as pd
import csv
from datetime import datetime
from openai import OpenAI
from llama_parse import LlamaParse

# --- NAPRAWA ASYNCIO ---
nest_asyncio.apply()

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SolidRules Ecosystem", page_icon="💠", layout="wide")

# --- CSS (PRO DESIGN) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        header {visibility: hidden;}
        .stApp { background-color: #050505; }
        section[data-testid="stSidebar"] { background-color: #0c0c0c; border-right: 1px solid #1e1e1e; }
        
        /* Stylizacja Nawigacji (Radio Buttony jako Menu) */
        .stRadio > div { gap: 10px; }
        .stRadio label {
            background-color: #1a1a1a;
            padding: 10px 15px;
            border-radius: 8px;
            border: 1px solid #333;
            color: #ccc;
            width: 100%;
            cursor: pointer;
            transition: all 0.2s;
        }
        .stRadio label:hover {
            border-color: #6366f1;
            color: white;
            background-color: #1e1e2e;
        }
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: #6366f1 !important;
            color: white !important;
            border-color: #6366f1 !important;
            font-weight: 600;
        }

        /* Reszta styli */
        .stTextInput input, .stTextArea textarea {
            background-color: #111111 !important; color: #e2e8f0 !important;
            border: 1px solid #333 !important; border-radius: 8px !important;
        }
        div.stButton > button {
            background-color: #1e1e2e; color: white; border: 1px solid #333;
            border-radius: 8px; transition: all 0.3s ease;
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(to right, #4f46e5, #6366f1); border: none;
        }
        h1, h2, h3 { color: #f8fafc !important; }
        p, li, label, .stMarkdown { color: #94a3b8 !important; }
        .stSuccess { background-color: #064e3b !important; color: #a7f3d0 !important; }
        .stInfo { background-color: #1e293b !important; color: #94a3b8 !important; }
    </style>
""", unsafe_allow_html=True)

# --- ZABEZPIECZENIE HASŁEM ---
def check_password():
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["APP_PASSWORD"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else: st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    st.markdown("### 🔒 SolidRules Enterprise Access")
    st.text_input("Access Code:", type="password", on_change=password_entered, key="password")
    return False

if not check_password(): st.stop()

# --- FUNKCJE POMOCNICZE (DB, OCR) ---
DB_FILE = "lessons_learnt.csv"
def init_db():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=["date", "problem", "solution", "tags"]).to_csv(DB_FILE, index=False)
def search_lessons(query):
    if not os.path.exists(DB_FILE): return ""
    try:
        df = pd.read_csv(DB_FILE)
        keywords = query.lower().split()
        matches = []
        for index, row in df.iterrows():
            if any(k in str(row['problem']).lower() for k in keywords if len(k) > 3):
                matches.append(f"- [CASE: {row['date']}] {str(row['solution'])[:200]}...")
        return "\n".join(matches[:3]) if matches else ""
    except: return ""
def save_lesson(problem, solution):
    with open(DB_FILE, mode='a', newline='', encoding='utf-8') as file:
        csv.writer(file).writerow([datetime.now().strftime("%Y-%m-%d"), problem, solution, "Auto-Save"])
def parse_hybrid(file_bytes): # Uproszczona wersja dla czytelności launchera
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name
    text_content = ""
    try:
        with pdfplumber.open(tmp_path) as pdf:
            for p in pdf.pages: text_content += (p.extract_text() or "") + "\n"
    except: pass
    os.remove(tmp_path)
    return text_content, "Standard OCR"
def pdf_to_images_base64(file_bytes):
    images_base64 = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            pix = doc.load_page(page_num).get_pixmap(matrix=fitz.Matrix(2, 2))
            images_base64.append(base64.b64encode(pix.tobytes("png")).decode("utf-8"))
    except: pass
    return images_base64

init_db()

# ==========================================
# 🧭 NAWIGACJA (SIDEBAR MENU)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=60)
    st.markdown("### SolidRules Ecosystem")
    
    # TO JEST MENU DLA WSPÓLNIKÓW
    selected_module = st.radio(
        "Wybierz Aplikację:",
        [
            "🚀 INNOVATE (Konstrukcja)", 
            "💰 ESTIMATOR (Wyceny)", 
            "📐 METROLOGY (Jakość)", 
            "🔧 FIELD (Serwis)",
            "🧠 KNOWLEDGE (Baza)"
        ],
        index=0 # Domyślnie startujemy z Innovate
    )
    
    st.markdown("---")
    st.caption(f"Zalogowano jako: Admin\nSesja aktywna.")

# ==========================================
# 🧠 MODUŁ 1: INNOVATE (TWÓJ GŁÓWNY KOD)
# ==========================================
if selected_module == "🚀 INNOVATE (Konstrukcja)":
    st.title("🚀 SolidRules INNOVATE")
    st.caption("AI-Powered R&D & Problem Solving")
    
    # --- UPLOADER W GLOWNYM OKNIE DLA TEGO MODULU ---
    with st.expander("📂 Kontekst: Wgraj Dokumentację (PDF)", expanded=True):
        uploaded_file = st.file_uploader("Rysunek / Norma / DTR", type=["pdf"])
    
    pdf_text = ""
    pdf_imgs = []
    has_file = False
    
    if uploaded_file:
        has_file = True
        with st.spinner("Analiza Vision AI..."):
            file_bytes = uploaded_file.getvalue()
            pdf_text, _ = parse_hybrid(file_bytes)
            pdf_imgs = pdf_to_images_base64(file_bytes)
        st.success(f"Wczytano dokument ({len(pdf_imgs)} stron)")
        
    problem = st.text_area("Opisz problem inżynierski lub zadaj pytanie:", height=120)
    
    if st.button("Generuj Rozwiązanie (TRIZ)", type="primary"):
        history = search_lessons(problem)
        messages = [{"role": "system", "content": "Jesteś Głównym Inżynierem. Użyj wiedzy ogólnej, wgranego pliku oraz bazy 'Lessons Learnt', aby rozwiązać problem."}]
        
        user_msg = f"PYTANIE: {problem}\n\nHISTORIA FIRMY:\n{history}"
        if has_file: user_msg += f"\n\nDOKUMENTACJA:\n{pdf_text[:20000]}"
        
        content = [{"type": "text", "text": user_msg}]
        if has_file and pdf_imgs:
             for img in pdf_imgs[:3]: content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
        
        messages.append({"role": "user", "content": content})
        
        try:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            with st.spinner("Analiza sprzeczności i generowanie raportu..."):
                resp = client.chat.completions.create(model="gpt-4o", messages=messages)
                ans = resp.choices[0].message.content
                st.markdown("### 💡 Raport Ekspercki")
                st.markdown(ans)
                st.session_state['last_ans'] = ans
                st.session_state['last_prob'] = problem
        except Exception as e: st.error(str(e))

    if 'last_ans' in st.session_state:
        if st.button("📥 Zapisz do Bazy Wiedzy"):
            save_lesson(st.session_state['last_prob'], st.session_state['last_ans'])
            st.success("Zapisano!")

# ==========================================
# 💰 MODUŁ 2: ESTIMATOR (MOCKUP / WIZJA)
# ==========================================
elif selected_module == "💰 ESTIMATOR (Wyceny)":
    st.title("💰 SolidRules ESTIMATOR")
    st.info("🚧 Moduł w trakcie wdrażania (Roadmapa Q3 2026)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Co to robi?")
        st.markdown("""
        Automatyczny inżynier sprzedaży.
        1. **Wgrywasz PDF** (Rysunek złożeniowy).
        2. **Vision AI** skanuje tabelę części (BOM).
        3. System automatycznie:
           * Rozpoznaje materiały.
           * Liczy wagę netto.
           * Szacuje czas obróbki na podstawie geometrii.
           * Generuje Excela z wyceną.
        """)
        st.button("Pobierz przykładową wycenę (Demo)", disabled=True)
    
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=150, caption="Engine: Pandas + Pricing API")

# ==========================================
# 📐 MODUŁ 3: METROLOGY (MOCKUP / WIZJA)
# ==========================================
elif selected_module == "📐 METROLOGY (Jakość)":
    st.title("📐 SolidRules METROLOGY")
    st.info("🚧 Moduł w trakcie wdrażania (Roadmapa Q4 2026)")
    
    st.markdown("### Cyfrowa Kontrola Jakości")
    st.write("Porównywanie modeli 3D z dokumentacją 2D w czasie rzeczywistym.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.file_uploader("1. Wgraj Model 3D (.STL / .STEP)", disabled=True)
    with c2:
        st.file_uploader("2. Wgraj Rysunek (.PDF)", disabled=True)
        
    st.warning("Silnik geometryczny (CadQuery) jest obecnie konfigurowany na serwerze GPU.")

# ==========================================
# 🔧 MODUŁ 4: FIELD (MOCKUP / WIZJA)
# ==========================================
elif selected_module == "🔧 FIELD (Serwis)":
    st.title("🔧 SolidRules FIELD (Mobile)")
    st.success("📱 Dostępne w wersji mobilnej (PWA)")
    
    st.markdown("""
    **Asystent Serwisanta.**
    Zrób zdjęcie uszkodzonej części telefonem, a system:
    1. Rozpozna element.
    2. Znajdzie procedurę wymiany w DTR.
    3. Sprawdzi stan magazynowy części zamiennych.
    """)
    st.text_input("Szukaj po kodzie błędu maszyny:", placeholder="np. ERROR 504")
    st.button("🔍 Szukaj w DTR")

# ==========================================
# 🧠 MODUŁ 5: KNOWLEDGE (BAZA DANYCH)
# ==========================================
elif selected_module == "🧠 KNOWLEDGE (Baza)":
    st.title("🧠 Centralna Baza Wiedzy")
    
    st.markdown("Tu zarządzasz pamięcią wszystkich aplikacji.")
    
    tab1, tab2 = st.tabs(["Przeglądaj Bazę", "Importuj Dane"])
    
    with tab1:
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            st.metric("Liczba lekcji w systemie", len(df))
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Baza pusta.")
            
    with tab2:
        st.write("Import z Excela firmowego:")
        st.file_uploader("Wgraj plik .xlsx", key="db_upload")
        st.button("Scal z systemem SolidRules", disabled=True)
