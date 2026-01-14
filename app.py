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
st.set_page_config(
    page_title="SolidRules Enterprise", 
    page_icon="💠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS (PRO DESIGN) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        
        .stApp { background-color: #050505; }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { 
            background-color: #0c0c0c; 
            border-right: 1px solid #1e1e1e; 
        }
        
        /* GÓRNA NAWIGACJA */
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

        /* INFO BOX STYLING */
        .streamlit-expanderHeader {
            background-color: #1e1e2e;
            border-radius: 8px;
            color: #a5b4fc !important;
            font-weight: 600;
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
# 🧭 GŁÓWNA NAWIGACJA
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
# MODUŁ 1: INNOVATE
# ==============================================================================
if selected_module == "🚀 INNOVATE":
    
    # --- INFO BOX ---
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT: Jak to działa pod maską?"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🛠️ Stack Technologiczny:**")
            st.markdown("""
            * **AI Engine:** GPT-4o (Reasoning) - analiza logiczna i TRIZ.
            * **OCR:** LlamaParse (rozumie tabele i schematy) + Tesseract.
            * **Vision:** OpenAI Vision API (analiza obrazu technicznego).
            * **Vector DB:** FAISS (lokalnie) lub Pinecone (prod) do szukania w historii (RAG).
            """)
        with c2:
            st.markdown("**📦 Estymacja Wdrożenia (Prod):**")
            st.markdown("""
            * **Platforma:** Web App (Przeglądarka na PC/Tablet).
            * **Infrastruktura:** Docker Container na Azure App Service.
            * **Czas:** 2-3 miesiące (Dopracowanie promptów, testy bezpieczeństwa danych).
            * **Koszt chmury:** ok. 50-100 USD/miesiąc (zależy od użycia API).
            """)
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🚀 Panel Konstruktora")
        st.info("💡 **Cel:** Rozwiązywanie problemów inżynierskich, analiza norm i generowanie koncepcji.")
        st.markdown("### 🛡️ Watchdog Prawny")
        st.warning("⚠️ Wykryto zmianę w normie PN-EN ISO 12100!")
        uploaded_file = st.file_uploader("Wgraj Dokumentację (PDF)", type=["pdf"])

    # --- MAIN ---
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
                    st.error("Wykryto hotspot w strefie A (Współczynnik K > 2.5).")

    st.markdown("### 💬 Konsultacja Inżynierska")
    problem = st.text_area("Opisz problem techniczny lub zadaj pytanie:", height=100)
    
    if st.button("🚀 Generuj Rozwiązanie (TRIZ)", type="primary"):
        with st.spinner("🧠 Inżynier AI analizuje problem..."):
            history = search_lessons(problem)
            system_prompt = "Jesteś Głównym Inżynierem. Użyj TRIZ i historii firmy."
            user_msg = f"PYTANIE: {problem}\n\nHISTORIA: {history}"
            if has_file: user_msg += f"\n\nDOKUMENTACJA: {pdf_text[:20000]}"
            content = [{"type": "text", "text": user_msg}]
            if has_file and pdf_imgs:
                 for img in pdf_imgs[:3]: content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
            
            try:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}])
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
    
    # --- INFO BOX ---
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT: Jak to działa pod maską?"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🛠️ Stack Technologiczny:**")
            st.markdown("""
            * **BOM Extraction:** LayoutLMv3 (Model AI do czytania dokumentów) + Regex.
            * **Pricing Engine:** Python Pandas + API Hurtowni (REST API).
            * **Complexity Algo:** `opencv-python` (liczenie konturów/otworów).
            """)
        with c2:
            st.markdown("**📦 Estymacja Wdrożenia (Prod):**")
            st.markdown("""
            * **Platforma:** Web App (PC - Dział Handlowy).
            * **Integracja:** Wymaga spięcia z ERP (np. Comarch/SAP) przez API.
            * **Czas:** 4-6 miesięcy (Budowa parserów dla różnych typów rysunków).
            * **Trudność:** Wysoka (Wymaga precyzji 99.9% w odczycie liczb).
            """)

    with st.sidebar:
        st.header("💰 Panel Kosztorysanta")
        st.info("Automatyzacja wycen na podstawie rysunków PDF.")
        st.file_uploader("Wgraj Rysunek Złożeniowy (PDF)", disabled=True)

    st.title("SolidRules ESTIMATOR")
    st.subheader("Moduł Ofertowania")
    st.markdown("### ⚙️ Jak to działa?")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("1. Vision AI skanuje tabelę BOM.\n2. Python mapuje materiały na ceny.\n3. Algorytm szacuje czas CNC.")
        st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=80)
    with col2:
        st.warning("⚠️ Status: Wersja Beta.")
        st.button("Pobierz przykładowy raport (Demo)", disabled=True)

# ==============================================================================
# MODUŁ 3: METROLOGY
# ==============================================================================
elif selected_module == "📐 METROLOGY":
    
    # --- INFO BOX ---
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT: Jak to działa pod maską?"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🛠️ Stack Technologiczny:**")
            st.markdown("""
            * **3D Kernel:** CadQuery / OpenCascade (Analiza plików STEP/STL).
            * **2D Analysis:** Azure Form Recognizer (Czytanie tolerancji z PDF).
            * **Math:** `numpy` + `trimesh` (Obliczenia geometryczne).
            """)
        with c2:
            st.markdown("**📦 Estymacja Wdrożenia (Prod):**")
            st.markdown("""
            * **Platforma:** High-Performance Web App (Wymaga GPU w chmurze).
            * **Backend:** Worker Pythona do ciężkich obliczeń 3D.
            * **Czas:** 6-8 miesięcy (Skomplikowana matematyka).
            * **Uwaga:** Możliwe opóźnienia przy dużych złożeniach (>100MB).
            """)

    with st.sidebar:
        st.header("📐 Panel Jakości (QC)")
        st.file_uploader("1. Wgraj Model 3D (.STL)", disabled=True)
        st.file_uploader("2. Wgraj Rysunek 2D (.PDF)", disabled=True)

    st.title("SolidRules METROLOGY")
    st.subheader("Cyfrowa Kontrola Jakości")
    st.markdown("Porównanie modelu 3D z dokumentacją 2D i normami GD&T.")
    st.info("✅ Status: Silnik matematyczny gotowy.")

# ==============================================================================
# MODUŁ 4: FIELD
# ==============================================================================
elif selected_module == "🔧 FIELD":
    
    # --- INFO BOX ---
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT: Jak to działa pod maską?"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🛠️ Stack Technologiczny:**")
            st.markdown("""
            * **Mobile App:** PWA (Progressive Web App) lub Flutter (Native).
            * **Recognition:** MobileNetV2 (Szybka identyfikacja części na telefonie).
            * **Voice:** OpenAI Whisper (Speech-to-Text w hałasie).
            """)
        with c2:
            st.markdown("**📦 Estymacja Wdrożenia (Prod):**")
            st.markdown("""
            * **Platforma:** iOS / Android (Tablety serwisowe).
            * **Wdrożenie:** Streamlit nie nadaje się na 'Native Mobile'.
            * **Strategia:** MVP robimy w Streamlit (działa w przeglądarce mobilnej). Wersja 2.0 wymaga przepisania frontendu na React Native/Flutter (3-4 m-ce pracy developera).
            """)

    with st.sidebar:
        st.header("🔧 Panel Mobilny")
        st.success("Wersja na tablety/smartfony.")
        st.camera_input("Zrób zdjęcie", disabled=True)

    st.title("SolidRules FIELD")
    st.subheader("Asystent Utrzymania Ruchu")
    st.markdown("Identyfikacja części, dostęp do DTR i raportowanie głosowe.")
    st.warning("⚠️ Status: Prototyp interfejsu.")

# ==============================================================================
# MODUŁ 5: KNOWLEDGE
# ==============================================================================
elif selected_module == "🧠 KNOWLEDGE":
    
    # --- INFO BOX ---
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT: Jak to działa pod maską?"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🛠️ Stack Technologiczny:**")
            st.markdown("""
            * **Database:** Qdrant / Pinecone (Wektorowa Baza Danych).
            * **Embeddings:** OpenAI text-embedding-3-small.
            * **Search:** Semantic Search (Szukanie po znaczeniu, nie słowach).
            """)
        with c2:
            st.markdown("**📦 Estymacja Wdrożenia (Prod):**")
            st.markdown("""
            * **Platforma:** Backend API (Niewidoczny serwis).
            * **Integracja:** Działa jako 'mózg' dla wszystkich innych aplikacji.
            * **Czas:** 1 miesiąc (Konfiguracja bazy i importerów).
            * **Bezpieczeństwo:** Dane szyfrowane (Enterprise Grade).
            """)

    with st.sidebar:
        st.header("🧠 Panel Administratora")
        with st.expander("📥 Importuj Dane"):
            up = st.file_uploader("Wgraj plik", type=["csv", "xlsx"])
            if up: st.success("Plik wgrany (Demo)")

    st.title("SolidRules KNOWLEDGE CORE")
    st.subheader("Centralny Mózg Systemu")
    if os.path.exists(DB_FILE):
        st.dataframe(pd.read_csv(DB_FILE), use_container_width=True)

# ==============================================================================
# 📈 STRATEGIA & ROADMAP
# ==============================================================================
elif selected_module == "📈 STRATEGY & ROADMAP":
    
    with st.sidebar:
        st.header("📈 Centrum Dowodzenia")
        st.info("Zarządzanie wizją produktu.")
        st.markdown("---")
        st.caption("Wybierz zakładkę po prawej.")
    
    st.markdown("# 🗺️ Strategia Rozwoju Produktu")
    
    tab1a, tab1b, tab1c, tab1d, tab1e = st.tabs(["1A: TOOLBOX", "1B: PROCESS", "1C: AGENTS", "1D: FLOW (⭐ MVP)", "1E: EVOLVE"])
    
    # --- 1A ---
    with tab1a:
        with st.expander("ℹ️ TECH & DEPLOYMENT: Wariant 1A (Toolbox)", expanded=False):
            st.markdown("""
            * **Zasada:** Luźne skrypty Pythona spięte interfejsem. Brak wspólnej bazy danych.
            * **Tech:** Streamlit, Local Filesystem.
            * **Wdrożenie:** Natychmiastowe (Hosting na Streamlit Cloud).
            * **Werdykt:** Tanie demo, brak wartości enterprise.
            """)
        st.header("Wariant 1A: Rodzina Aplikacji")
        st.info("Status: Prototyp")
        
    # --- 1B ---
    with tab1b:
        with st.expander("ℹ️ TECH & DEPLOYMENT: Wariant 1B (Process)", expanded=False):
            st.markdown("""
            * **Zasada:** Przepływ danych (ETL). PDF -> JSON -> SQL.
            * **Tech:** OCR, SQL Database (PostgreSQL), Pandas.
            * **Wdrożenie:** 2-3 miesiące. Wymaga postawienia serwera bazodanowego.
            * **Werdykt:** Cyfryzacja biurokracji. Nuda.
            """)
        st.header("Wariant 1B: Engineering Ops")
        st.info("Status: Koncepcja")

    # --- 1C ---
    with tab1c:
        with st.expander("ℹ️ TECH & DEPLOYMENT: Wariant 1C (Agents)", expanded=False):
            st.markdown("""
            * **Zasada:** Autonomiczne Agenty (LangChain / AutoGPT). Pętle decyzyjne bez człowieka.
            * **Tech:** LLM Chains, API Integrations (Mail, ERP).
            * **Wdrożenie:** 6-12 miesięcy (R&D). Bardzo trudne testowanie stabilności.
            * **Werdykt:** Zbyt ryzykowne biznesowo.
            """)
        st.header("Wariant 1C: Autonomy")
        st.info("Status: Sci-Fi")

    # --- 1D ---
    with tab1d:
        with st.expander("ℹ️ TECH & DEPLOYMENT: Wariant 1D (Flow) - REKOMENDACJA", expanded=True):
            st.markdown("""
            * **Zasada:** Human-in-the-Loop. AI proponuje (Draft), Człowiek zatwierdza.
            * **Tech:**
                * **Confidence Scoring:** Probabilistyka modeli ML (pewność wyniku).
                * **State Machine:** Zarządzanie stanem (Nowy -> Do weryfikacji -> Zatwierdzony).
                * **Feedback Loop:** Zapisywanie korekt do bazy treningowej.
            * **Wdrożenie Produkcyjne (Cross-Platform):**
                * **Backend:** Python FastAPI (Logika biznesowa + AI).
                * **Frontend Web:** React.js (Dla biura/PC).
                * **Frontend Mobile:** PWA (Progressive Web App) - działa na iOS/Android bez AppStore.
                * **Infrastruktura:** Kubernetes (Skalowalność).
            * **Czas do rynku (MVP):** 3-4 miesiące.
            """)
        st.header("⭐ Wariant 1D: SolidRules FLOW")
        st.success("✅ REKOMENDOWANA STRATEGIA")
        st.markdown("**AI wykonuje 80% pracy, Człowiek 20% decyzji.**")

    # --- 1E ---
    with tab1e:
        with st.expander("ℹ️ TECH & DEPLOYMENT: Wariant 1E (Evolve)", expanded=False):
            st.markdown("""
            * **Zasada:** Optymalizacja biznesowa. Algorytmy predykcyjne.
            * **Tech:** Reinforcement Learning (Uczenie ze wzmocnieniem), Big Data Analytics.
            * **Wdrożenie:** +12 miesięcy od wdrożenia wersji 1D (wymaga dużej ilości danych historycznych).
            """)
        st.header("Wariant 1E: SolidRules EVOLVE")
        st.info("Status: Cel długoterminowy")
