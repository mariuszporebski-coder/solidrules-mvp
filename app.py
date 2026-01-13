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
import time
import json
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        header {visibility: hidden;}
        .stApp { background-color: #050505; }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { 
            background-color: #0c0c0c; 
            border-right: 1px solid #1e1e1e; 
        }
        
        /* Tabs (Zakładki) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: #0c0c0c;
            padding: 10px;
            border-radius: 12px;
            border: 1px solid #1e1e1e;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border: none;
            color: #94a3b8;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1e1e2e !important;
            color: #6366f1 !important;
            border-bottom: 2px solid #6366f1 !important;
        }

        /* UI Elements */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {
            background-color: #111111 !important; color: #e2e8f0 !important;
            border: 1px solid #333 !important; border-radius: 8px !important;
        }
        div.stButton > button {
            background-color: #1e1e2e; color: white; border: 1px solid #333;
            border-radius: 8px; transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #6366f1; border-color: #6366f1;
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(to right, #4f46e5, #6366f1); border: none;
        }
        
        /* Typography */
        h1, h2, h3 { color: #f8fafc !important; }
        p, li, label, .stMarkdown, .stCaption { color: #94a3b8 !important; }
        
        /* Alerts */
        .stSuccess { background-color: #064e3b !important; color: #a7f3d0 !important; }
        .stInfo { background-color: #172554 !important; color: #bfdbfe !important; }
        .stWarning { background-color: #451a03 !important; color: #fdba74 !important; }
        
        /* JSON View */
        .json-formatter-container { background-color: #111 !important; color: #eee !important; }
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
    st.markdown("### 🔒 SolidRules Access")
    st.text_input("Access Code:", type="password", on_change=password_entered, key="password")
    return False

if not check_password(): st.stop()

# --- FUNKCJE BACKENDOWE ---
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
                matches.append(f"- [CASE: {row['date']}] {str(row['solution'])[:300]}...")
        return "\n".join(matches[:3]) if matches else ""
    except: return ""
def parse_hybrid(file_bytes): 
    # Mockup dla szybkości, normalnie tutaj byłby LlamaParse
    return "Treść dokumentu wyekstrahowana z PDF...", "OCR Standard"
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
# 🎛️ PRZEŁĄCZNIK WARIANTÓW (STRATEGIA)
# ==========================================
with st.sidebar:
    st.markdown("### 🏗️ Architektura Systemu")
    variant = st.selectbox(
        "Wybierz Koncepcję:",
        ["WARIANT 1B: EngOps AI (Nowy)", "WARIANT 1A: Rodzina Aplikacji (Stary)"],
        index=0
    )
    st.markdown("---")

# ==============================================================================
# WARIANT 1B: ENGINEERING OPS AI (Cashflow First)
# ==============================================================================
if variant == "WARIANT 1B: EngOps AI (Nowy)":
    
    # Header
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.markdown("# 🏗️ Engineering Ops AI")
        st.caption("System operacyjny dla firm technicznych | Data-Driven Approach")
    with c2:
        st.metric("Status Core", "ONLINE", delta_color="normal")

    # GŁÓWNE ZAKŁADKI (STRATEGIA CASHFLOW FIRST)
    tab_data, tab_quote, tab_field, tab_review, tab_core = st.tabs([
        "1️⃣ DRAWING → DATA", 
        "2️⃣ QUOTE → ORDER", 
        "3️⃣ FIELD NOTES", 
        "4️⃣ DESIGN REVIEW", 
        "🧠 KNOWLEDGE CORE"
    ])

    # --- MODUŁ 1: DIGITALIZACJA (DRAWING -> DATA) ---
    with tab_data:
        st.markdown("### 📄 Automatyczna Digitalizacja Rysunków")
        st.info("Zamieniamy 'martwe' PDF-y w dane JSON/CSV dla systemów ERP i CNC.")
        
        col_up, col_json = st.columns([1, 1])
        with col_up:
            uploaded_dwg = st.file_uploader("Wgraj Rysunek (PDF)", key="v1b_dwg")
            if uploaded_dwg:
                st.success("Plik przyjęty. Rozpoczynam ekstrakcję Vision AI...")
                st.image("https://cdn-icons-png.flaticon.com/512/337/337946.png", width=50) # Placeholder
                
        with col_json:
            st.markdown("**Wynik Ekstrakcji (Dane Strukturalne):**")
            # Mockup danych JSON
            mock_data = {
                "part_name": "Wspornik_V2",
                "material": "S355J2",
                "quantity": 50,
                "dimensions": {"L": 200, "W": 100, "H": 15},
                "tolerances": ["H7", "+/- 0.1"],
                "surface_treatment": "Ocynk ogniowy"
            }
            if uploaded_dwg:
                st.json(mock_data)
                st.download_button("📥 Pobierz JSON", json.dumps(mock_data), "data.json")
                st.download_button("📥 Pobierz CSV", "part,mat,qty\nWspornik,S355,50", "data.csv")
            else:
                st.caption("Oczekiwanie na plik...")

    # --- MODUŁ 2: OFERTOWANIE (QUOTE -> ORDER) ---
    with tab_quote:
        
        st.markdown("### 💰 Inteligentne Ofertowanie (Cashflow Engine)")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**1. Wsad (BOM)**")
            st.file_uploader("Wgraj Złożenie/BOM", key="v1b_quote")
        with c2:
            st.markdown("**2. Parametry Biznesowe**")
            margin = st.slider("Marża (%)", 0, 100, 30)
            hourly_rate = st.number_input("Stawka CNC (PLN/h)", value=150)
        with c3:
            st.markdown("**3. Wynik (Estymacja)**")
            if st.button("Przelicz Ofertę"):
                with st.spinner("Analiza geometrii i cen rynkowych..."):
                    time.sleep(1)
                    st.metric("Sugerowana Cena", "12 450 PLN", delta=f"Marża: {margin}%")
                    st.progress(70, text="Prawdopodobieństwo wygrania oferty: Wysokie")

        st.markdown("#### 📜 Historia Ofert (CRM)")
        df_quotes = pd.DataFrame({
            "Klient": ["TechCorp", "BuildPol", "AgroMech"],
            "Projekt": ["Silos X", "Rama Y", "Wał Z"],
            "Wartość": ["15k", "4k", "22k"],
            "Status": ["Wysłana", "Akceptacja", "Odrzucona"]
        })
        st.dataframe(df_quotes, use_container_width=True)

    # --- MODUŁ 3: WIEDZA Z TERENU (FIELD NOTES) ---
    with tab_field:
        st.markdown("### 🛠️ Field Notes AI (Zbieranie wiedzy z terenu)")
        st.caption("Serwisant nie pisze raportów. On mówi do telefonu.")
        
        c_mob1, c_mob2 = st.columns([1, 2])
        with c_mob1:
            st.markdown("#### 📱 Interfejs Mobilny")
            st.info("Nagraj notatkę głosową:")
            st.audio(None) # Placeholder
            st.camera_input("Zrób zdjęcie awarii")
            
        with c_mob2:
            st.markdown("#### 🧠 AI Processing (Backend)")
            st.markdown("""
            **Transkrypcja:** *"Klient zgłasza wibracje pompy. Na moje oko to sprzęgło kłowe, guma jest sparciała."*
            
            **Strukturyzacja Danych:**
            * **Problem:** Wibracje pompy
            * **Przyczyna:** Zużycie sprzęgła (element elastyczny)
            * **Tagi:** #Maintenance #Coupling #Vibration
            * **Akcja:** Zamówić wkładkę sprzęgła typ B.
            """)
            st.button("Zapisz do Knowledge Core", type="primary")

    # --- MODUŁ 4: AUDYT (DESIGN REVIEW) ---
    with tab_review:
        st.markdown("### 🔍 Design Review AI (Audyt Dokumentacji)")
        st.info("Sprawdzamy spójność i błędy 'szkolne' przed wysłaniem na produkcję.")
        
        u_rev = st.file_uploader("Wgraj PDF do weryfikacji", key="v1b_rev")
        
        if u_rev:
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown("**Znalezione Błędy (Checklist):**")
                st.error("❌ Brak tolerancji ogólnej w tabelce.")
                st.warning("⚠️ Gwint M20 oznaczony jako 'fi 20'.")
                st.success("✅ Rzuty zgodne (Europejskie).")
            with col_r:
                st.markdown("**Zalecenia:**")
                st.write("Dodać normę ISO 2768-mK. Poprawić oznaczenie gwintu.")

    # --- MODUŁ 5: KNOWLEDGE CORE ---
    with tab_core:
        st.markdown("### 🧠 Knowledge Core (Fundament)")
        st.write("Jedno źródło prawdy. Tu trafiają dane z ofert, serwisu i audytów.")
        
        query = st.text_input("Przeszukaj pamięć firmy (RAG):", placeholder="np. Dlaczego pękają wały w projekcie X?")
        if query:
            st.write(f"Szukam w wektorowej bazie danych dla: '{query}'...")
            st.info("💡 Znaleziono 3 powiązane notatki z serwisu (Field Notes) i 1 odrzuconą ofertę.")


# ==============================================================================
# WARIANT 1A: RODZINA APLIKACJI (Oryginalna Koncepcja)
# ==============================================================================
elif variant == "WARIANT 1A: Rodzina Aplikacji (Stary)":
    
    # --- STARY KOD (ZAWINIĘTY W BLOK) ---
    st.markdown("<div style='text-align: center; margin-bottom: 5px; color: #666; font-size: 0.8em;'>SOLIDRULES ECOSYSTEM v4.5 (Legacy View)</div>", unsafe_allow_html=True)

    selected_app = st.radio(
        "Nawigacja",
        ["🚀 INNOVATE", "💰 ESTIMATOR", "📐 METROLOGY", "🔧 FIELD", "🧠 KNOWLEDGE"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("---")

    if selected_app == "🚀 INNOVATE":
        with st.sidebar:
            st.header("🚀 Panel Konstruktora")
            st.markdown("### 🛡️ Watchdog Status")
            st.warning("⚠️ Wykryto zmiany w prawie!")
            uploaded_file = st.file_uploader("Rysunek / Norma / DTR (PDF)", type=["pdf"])

        st.title("SolidRules INNOVATE")
        st.caption("AI-Powered R&D: Rozwiązywanie problemów & Szybka Symulacja")

        pdf_text = ""
        pdf_imgs = []
        has_file = False
        
        if uploaded_file:
            has_file = True
            with st.spinner("Analiza Vision AI..."):
                file_bytes = uploaded_file.getvalue()
                pdf_text, _ = parse_hybrid(file_bytes)
                pdf_imgs = pdf_to_images_base64(file_bytes)
            st.success(f"✅ Dokument wczytany ({len(pdf_imgs)} stron)")
            
            c1, c2 = st.columns(2)
            with c1: 
                if pdf_imgs: st.image(base64.b64decode(pdf_imgs[0]), use_container_width=True)
            with c2:
                if st.button("Uruchom Instant MES"):
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Fem_pole_c.jpg/640px-Fem_pole_c.jpg", caption="Heatmap Naprężeń")
                    st.error("Hotspot w narożniku A!")

        problem = st.text_area("Opisz problem techniczny:", height=100)
        
        if st.button("Generuj Rozwiązanie (TRIZ)", type="primary"):
            history = search_lessons(problem)
            system_prompt = "Jesteś Głównym Inżynierem. Użyj TRIZ i historii firmy."
            user_msg = f"PYTANIE: {problem}\n\nHISTORIA: {history}"
            if has_file: user_msg += f"\n\nDOKUMENTY: {pdf_text[:10000]}"
            
            # Mockup odpowiedzi dla szybkości działania launchera
            st.markdown("### 💡 Raport Ekspercki")
            st.markdown(f"**Diagnoza:** Problem dotyczy '{problem}'.\n\n**TRIZ:** Zastosuj zasadę segmentacji.\n\n**Historia:** W 2024 mieliśmy podobny przypadek.")
            
            if st.button("Zapisz do Bazy"):
                save_lesson(problem, "Rozwiązanie TRIZ...")
                st.success("Zapisano!")

    elif selected_app == "💰 ESTIMATOR":
        st.title("💰 SolidRules ESTIMATOR")
        st.info("Wariant 1A: Klasyczny kalkulator")
        st.write("Wersja w Wariancie 1B jest znacznie bardziej rozbudowana (Quote -> Order).")

    elif selected_app == "📐 METROLOGY":
        st.title("📐 SolidRules METROLOGY")
        st.write("Porównywanie 3D (STL) vs 2D (PDF).")
        st.file_uploader("Model 3D", disabled=True)
        st.file_uploader("Rysunek 2D", disabled=True)

    elif selected_app == "🔧 FIELD":
        st.title("🔧 SolidRules FIELD")
        st.write("Wersja mobilna dla utrzymania ruchu.")
        st.camera_input("Zdjęcie")

    elif selected_app == "🧠 KNOWLEDGE":
        st.title("🧠 Centralna Baza Wiedzy")
        if os.path.exists(DB_FILE):
            st.dataframe(pd.read_csv(DB_FILE))
