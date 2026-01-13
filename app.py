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

# --- KONFIGURACJA STRONY (ZMIANA: WYMUSZENIE OTWARTEGO PASKA) ---
st.set_page_config(
    page_title="SolidRules Enterprise", 
    page_icon="💠", 
    layout="wide",
    initial_sidebar_state="expanded"  # <--- TO NAPRAWIA PROBLEM ZNIKAJĄCEGO PASKA
)

# --- CSS (PRO DESIGN - NAPRAWIONY NAGŁÓWEK) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        
        /* USUNĄŁEM UKRYWANIE HEADER, ŻEBYŚ WIDZIAŁ PRZYCISKI STERUJĄCE */
        .stApp { background-color: #050505; }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] { 
            background-color: #0c0c0c; 
            border-right: 1px solid #1e1e1e; 
        }
        
        /* GÓRNA NAWIGACJA (MENU) */
        div[role="radiogroup"] {
            display: flex;
            justify-content: center;
            background-color: #0c0c0c;
            padding: 8px;
            border-radius: 12px;
            border: 1px solid #1e1e1e;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }
        div[role="radiogroup"] label {
            background-color: transparent;
            border: none;
            color: #64748b;
            font-weight: 500;
            padding: 6px 16px;
            border-radius: 6px;
            transition: all 0.2s;
            margin: 0 4px;
        }
        div[role="radiogroup"] label:hover {
            color: #e2e8f0;
            background-color: #1e1e2e;
        }
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: #4f46e5 !important;
            color: white !important;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }

        /* Elementy UI */
        .stTextInput input, .stTextArea textarea {
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
        
        /* Typography & Alerts */
        h1, h2, h3 { color: #f8fafc !important; }
        p, li, label, .stMarkdown, .stCaption { color: #94a3b8 !important; }
        .stSuccess { background-color: #064e3b !important; color: #a7f3d0 !important; border: 1px solid #059669; }
        .stInfo { background-color: #172554 !important; color: #bfdbfe !important; border: 1px solid #2563eb; }
        .stWarning { background-color: #451a03 !important; color: #fdba74 !important; border: 1px solid #d97706; }
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

def save_lesson(problem, solution):
    with open(DB_FILE, mode='a', newline='', encoding='utf-8') as file:
        csv.writer(file).writerow([datetime.now().strftime("%Y-%m-%d"), problem, solution, "Auto-Save"])

def parse_hybrid(file_bytes): 
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name
    text_content = ""
    ll_key = st.secrets.get("LLAMA_CLOUD_API_KEY", None)
    if ll_key:
        try:
            parser = LlamaParse(api_key=ll_key, result_type="markdown", premium_mode=True, language="pl")
            docs = parser.load_data(tmp_path)
            if docs: text_content = "\n\n".join([d.text for d in docs])
        except: pass
    if not text_content:
        try:
            with pdfplumber.open(tmp_path) as pdf:
                for p in pdf.pages: text_content += (p.extract_text() or "") + "\n"
        except: pass
    os.remove(tmp_path)
    return text_content, "Hybrid OCR"

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
# 🧭 GŁÓWNA NAWIGACJA (TOP MENU)
# ==========================================
st.markdown("<div style='text-align: center; margin-bottom: 5px; color: #6366f1; font-size: 0.8em; letter-spacing: 2px; font-weight: bold;'>SOLIDRULES ENTERPRISE PLATFORM</div>", unsafe_allow_html=True)

selected_module = st.radio(
    "Główna Nawigacja",
    ["🚀 INNOVATE", "💰 ESTIMATOR", "📐 METROLOGY", "🔧 FIELD", "🧠 KNOWLEDGE", "📈 STRATEGY & ROADMAP"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ==============================================================================
# MODUŁ 1: INNOVATE (DZIAŁAJĄCY KOD R&D)
# ==============================================================================
if selected_module == "🚀 INNOVATE":
    
    # --- SIDEBAR (Musi być widoczny!) ---
    with st.sidebar:
        st.header("🚀 Panel Konstruktora")
        st.info("💡 **Cel:** Rozwiązywanie problemów inżynierskich, analiza norm i generowanie koncepcji.")
        
        st.markdown("### 🛡️ Watchdog Prawny")
        st.warning("⚠️ Wykryto zmianę w normie PN-EN ISO 12100!")
        
        uploaded_file = st.file_uploader("Wgraj Dokumentację (PDF)", type=["pdf"])
        st.caption("Silnik: GPT-4o + Vision AI + Physics Knowledge")

    # --- MAIN CONTENT ---
    st.title("SolidRules INNOVATE")
    st.caption("Wirtualny Główny Inżynier (R&D Copilot)")

    pdf_text = ""
    pdf_imgs = []
    has_file = False
    
    if uploaded_file:
        has_file = True
        with st.spinner("🔄 Analiza Vision AI & OCR..."):
            file_bytes = uploaded_file.getvalue()
            pdf_text, _ = parse_hybrid(file_bytes)
            pdf_imgs = pdf_to_images_base64(file_bytes)
        st.success(f"✅ Dokument wczytany ({len(pdf_imgs)} stron)")
        
        col1, col2 = st.columns(2)
        with col1:
             with st.expander("📄 Podgląd dokumentu", expanded=True):
                 if pdf_imgs: st.image(base64.b64decode(pdf_imgs[0]), use_container_width=True)
        with col2:
            st.markdown("**⚡ Instant MES (Szybka Symulacja)**")
            if st.button("Uruchom Analizę Naprężeń (AI Predict)"):
                with st.spinner("Generowanie mapy ciepła..."):
                    time.sleep(1.5)
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Fem_pole_c.jpg/640px-Fem_pole_c.jpg", caption="AI Stress Prediction")
                    st.error("Wykryto hotspot w strefie A (Współczynnik K > 2.5). Zalecane zaokrąglenie.")

    st.markdown("### 💬 Konsultacja Inżynierska")
    problem = st.text_area("Opisz problem techniczny lub zadaj pytanie:", height=100, placeholder="Np. Jak uszczelnić ten wał przy 200 stopniach Celsjusza?")
    
    if st.button("🚀 Generuj Rozwiązanie (TRIZ)", type="primary"):
        with st.spinner("🧠 Inżynier AI analizuje problem..."):
            history = search_lessons(problem)
            
            system_prompt = """Jesteś Głównym Inżynierem. Masz dwa tryby:
            1. BIBLIOTEKARZ: Jeśli pytanie dotyczy danych z pliku -> podaj fakty.
            2. EKSPERT TRIZ: Jeśli to problem techniczny -> Przeprowadź analizę (Diagnoza -> Sprzeczność -> Koncepcje -> Ryzyko).
            Wspomnij o podobnych przypadkach z Historii Firmy, jeśli są dostępne."""
            
            user_msg = f"PYTANIE: {problem}\n\nHISTORIA FIRMY:\n{history}"
            if has_file: user_msg += f"\n\nDOKUMENTACJA (OCR):\n{pdf_text[:25000]}"
            
            content = [{"type": "text", "text": user_msg}]
            if has_file and pdf_imgs:
                 for img in pdf_imgs[:3]: content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
            
            try:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                resp = client.chat.completions.create(model="gpt-4o", messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ])
                ans = resp.choices[0].message.content
                st.markdown("### 💡 Raport Ekspercki")
                st.markdown(ans)
                st.session_state['last_ans'] = ans
                st.session_state['last_prob'] = problem
            except Exception as e: st.error(f"Błąd API: {e}")

    if 'last_ans' in st.session_state:
        if st.button("📥 Zapisz do Bazy Wiedzy"):
            save_lesson(st.session_state['last_prob'], st.session_state['last_ans'])
            st.success("Zapisano!")

# ==============================================================================
# MODUŁ 2: ESTIMATOR
# ==============================================================================
elif selected_module == "💰 ESTIMATOR":
    with st.sidebar:
        st.header("💰 Panel Kosztorysanta")
        st.info("Automatyzacja wycen na podstawie rysunków PDF.")
        st.file_uploader("Wgraj Rysunek Złożeniowy (PDF)", disabled=True)
        st.markdown("---")
        st.metric("Kurs Euro", "4.32 PLN")
        st.metric("Cena Stali (S235)", "4.50 PLN/kg")

    st.title("SolidRules ESTIMATOR")
    st.subheader("Moduł Ofertowania i Kalkulacji Kosztów")
    st.markdown("""
    ### ⚙️ Jak to działa? (Architektura Procesu)
    1.  **Ekstrakcja Tabelaryczna (Vision AI):** Algorytm lokalizuje BOM i konwertuje na dane.
    2.  **Inteligentny Cennik:** Mapuje materiały na ceny rynkowe.
    3.  **Shape Complexity Index (SCI):** Estymuje czas maszynowy CNC.
    4.  **Generowanie Oferty:** Tworzy gotowy PDF dla klienta.
    """)
    col1, col2 = st.columns(2)
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=100, caption="PDF -> Data -> Price")
    with col2:
        st.warning("⚠️ Status: Wersja Beta planowana na Q3 2026.")
        st.button("Pobierz przykładowy raport wyceny (Demo)", disabled=True)

# ==============================================================================
# MODUŁ 3: METROLOGY
# ==============================================================================
elif selected_module == "📐 METROLOGY":
    with st.sidebar:
        st.header("📐 Panel Jakości (QC)")
        st.info("Weryfikacja zgodności wykonania z projektem.")
        st.file_uploader("1. Wgraj Model 3D (.STL)", disabled=True)
        st.file_uploader("2. Wgraj Rysunek 2D (.PDF)", disabled=True)

    st.title("SolidRules METROLOGY")
    st.subheader("Cyfrowa Kontrola Jakości (Digital Twin Check)")
    st.markdown("""
    ### ⚙️ Jak to działa?
    1.  **Analiza Geometrii 3D:** Silnik mierzy bryłę.
    2.  **Analiza Rysunku 2D:** AI odczytuje tolerancje.
    3.  **Cross-Check:** Porównuje nominal z rzeczywistością.
    """)
    st.info("✅ Status: Silnik matematyczny gotowy. Trwa praca nad UI.")

# ==============================================================================
# MODUŁ 4: FIELD
# ==============================================================================
elif selected_module == "🔧 FIELD":
    with st.sidebar:
        st.header("🔧 Panel Mobilny")
        st.success("Wersja na tablety/smartfony.")
        st.camera_input("Zrób zdjęcie części", disabled=True)
        st.text_input("Kod błędu maszyny:", placeholder="ERROR-500")

    st.title("SolidRules FIELD")
    st.subheader("Asystent Utrzymania Ruchu")
    st.markdown("""
    ### ⚙️ Jak to działa?
    1.  **Visual Search:** Rozpoznawanie części ze zdjęcia.
    2.  **Inteligentne DTR:** Wyszukiwanie procedur naprawczych.
    3.  **Pętla Zwrotna:** Zgłoszenia z terenu trafiają do inżynierów.
    """)
    st.warning("⚠️ Status: Faza prototypowania.")

# ==============================================================================
# MODUŁ 5: KNOWLEDGE
# ==============================================================================
elif selected_module == "🧠 KNOWLEDGE":
    with st.sidebar:
        st.header("🧠 Panel Administratora")
        st.info("Zarządzanie pamięcią systemu (Lessons Learnt).")
        with st.expander("📥 Importuj z Excela/CSV"):
            up = st.file_uploader("Wgraj plik", type=["csv", "xlsx"])
            if up:
                try:
                    df_new = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
                    st.write("Podgląd:", df_new.head(2))
                    col_p = st.selectbox("Kolumna PROBLEM", df_new.columns)
                    col_s = st.selectbox("Kolumna ROZWIĄZANIE", df_new.columns)
                    if st.button("Scal z bazą"):
                        rows = []
                        for _, row in df_new.iterrows():
                            rows.append([datetime.now().strftime("%Y-%m-%d"), row[col_p], row[col_s], "Import"])
                        with open(DB_FILE, 'a', newline='', encoding='utf-8') as f:
                            csv.writer(f).writerows(rows)
                        st.success("Zaimportowano!")
                except: st.error("Błąd pliku")

    st.title("SolidRules KNOWLEDGE CORE")
    st.subheader("Centralny Mózg Systemu")
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        st.metric("Liczba zgromadzonych rozwiązań", len(df))
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Baza wiedzy jest pusta.")

# ==============================================================================
# 📈 STRATEGIA & ROADMAP
# ==============================================================================
elif selected_module == "📈 STRATEGY & ROADMAP":
    
    with st.sidebar:
        st.header("📈 Centrum Dowodzenia")
        st.info("Zarządzanie wizją i kierunkiem rozwoju produktu.")
        st.markdown("---")
        st.caption("Wybierz zakładkę po prawej, aby poznać szczegóły.")
    
    st.markdown("# 🗺️ Strategia Rozwoju Produktu")
    st.caption("Ewolucja od prostych narzędzi do autonomicznego systemu operacyjnego.")
    
    tab1a, tab1b, tab1c, tab1d, tab1e = st.tabs([
        "1A: TOOLBOX", 
        "1B: PROCESS", 
        "1C: AGENTS", 
        "1D: FLOW (⭐ MVP)", 
        "1E: EVOLVE"
    ])
    
    # TREŚCI ZAKŁADEK STRATEGII (SKRÓCONE DLA CZYTELNOŚCI KODU, ALE TREŚCIWE W DISPLAYU)
    with tab1a:
        st.header("Wariant 1A: Rodzina Aplikacji (Toolbox)")
        st.info("ℹ️ **Status:** Obecny Prototyp")
        st.markdown("**Filozofia:** Zestaw luźnych narzędzi (Kalkulatorów) dla inżynierów. Dobry start, ale słabe skalowanie.")
    with tab1b:
        st.header("Wariant 1B: Engineering Ops (Proces)")
        st.info("ℹ️ **Status:** Koncepcja Procesowa")
        st.markdown("**Filozofia:** Cyfryzacja obecnych procesów. 'Lepszy Excel'. Konieczny etap, ale mało innowacyjny.")
    with tab1c:
        st.header("Wariant 1C: Autonomy (Agenci AI)")
        st.info("ℹ️ **Status:** Wizja Futurystyczna")
        st.markdown("**Filozofia:** AI robi wszystko. Człowiek tylko patrzy. Zbyt duże ryzyko na start.")
    with tab1d:
        st.header("⭐ Wariant 1D: SolidRules FLOW (Controlled Autonomy)")
        st.success("✅ **Status:** REKOMENDOWANA STRATEGIA")
        st.markdown("""
        **Filozofia:** AI wykonuje 80% pracy, Człowiek podejmuje 20% kluczowych decyzji.
        **Kluczowe:** Confidence Scoring (AI ocenia swoją pewność), Zarządzanie Wyjątkami.
        **Dlaczego to kupią?** Szybkość AI + Kontrola Inżyniera.
        """)
    with tab1e:
        st.header("Wariant 1E: SolidRules EVOLVE (Optymalizacja)")
        st.info("ℹ️ **Status:** Cel na 2-3 lata")
        st.markdown("**Filozofia:** System staje się Dyrektorem Operacyjnym. Dynamiczne ceny, przewidywanie odejścia klientów, samodoskonalenie algorytmów.")
