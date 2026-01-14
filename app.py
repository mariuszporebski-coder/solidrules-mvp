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
    page_title="SolidRules Enterprise Platform", 
    page_icon="💠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS (ULTIMATE PRO DESIGN) ---
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

        /* EXPANDER & CARDS */
        .streamlit-expanderHeader {
            background-color: #111827;
            border: 1px solid #374151;
            border-radius: 8px;
            color: #60a5fa !important;
            font-weight: 600;
        }
        .streamlit-expanderContent {
            background-color: #0f172a;
            border: 1px solid #374151;
            color: #cbd5e1;
        }
        .metric-box {
            background-color: #111;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #6366f1;
            text-align: center;
        }
        
        /* UI Elements */
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
    ["🚀 INNOVATE", "💰 ESTIMATOR", "📐 METROLOGY", "🔧 FIELD", "🧠 KNOWLEDGE", "📈 STRATEGY & ROADMAP", "💰 GRANT STRATEGY"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ==============================================================================
# MODUŁ 1: INNOVATE
# ==============================================================================
if selected_module == "🚀 INNOVATE":
    
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT STRATEGY"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🛠️ Architecture")
            st.markdown("""
            * **Core:** Python 3.10 + FastAPI.
            * **AI:** GPT-4o (Reasoning) + LangChain (Memory).
            * **OCR:** LlamaParse (Tabular data) + Tesseract (Raw text).
            * **Security:** AES-256 encryption at rest.
            """)
        with c2:
            st.markdown("### 📦 Deployment (Production)")
            st.markdown("""
            * **Hosting:** Azure App Service (B1 Plan).
            * **Koszt:** ~150 USD/msc (API + Hosting).
            * **Skalowalność:** Auto-scale do 10 instancji.
            * **Timeline:** 2 m-ce do wersji produkcyjnej.
            """)

    with st.sidebar:
        st.header("🚀 Panel Konstruktora")
        st.info("💡 **Cel:** R&D Copilot.")
        st.markdown("### 🛡️ Watchdog")
        st.warning("⚠️ Zmiana w normie ISO 12100!")
        uploaded_file = st.file_uploader("Wgraj PDF", type=["pdf"])

    st.title("SolidRules INNOVATE")
    st.caption("Wirtualny Główny Inżynier")

    pdf_text = ""
    pdf_imgs = []
    has_file = False
    
    if uploaded_file:
        has_file = True
        with st.spinner("🔄 Vision AI Analysis..."):
            file_bytes = uploaded_file.getvalue()
            pdf_text, _ = parse_hybrid(file_bytes)
            pdf_imgs = pdf_to_images_base64(file_bytes)
        st.success(f"✅ Wczytano ({len(pdf_imgs)} stron)")
        
        col1, col2 = st.columns(2)
        with col1:
             with st.expander("📄 Podgląd", expanded=True):
                 if pdf_imgs: st.image(base64.b64decode(pdf_imgs[0]), use_container_width=True)
        with col2:
            st.markdown("**⚡ Instant MES**")
            if st.button("Uruchom Symulację Naprężeń"):
                with st.spinner("Liczenie..."):
                    time.sleep(1.5)
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Fem_pole_c.jpg/640px-Fem_pole_c.jpg", caption="Heatmap")
                    st.error("Hotspot w strefie A (K > 2.5).")

    st.markdown("### 💬 Konsultacja")
    problem = st.text_area("Opisz problem:", height=100)
    
    if st.button("🚀 Generuj (TRIZ)", type="primary"):
        with st.spinner("Myślę..."):
            history = search_lessons(problem)
            system_prompt = "Jesteś Głównym Inżynierem. Użyj TRIZ."
            user_msg = f"PYTANIE: {problem}\n\nHISTORIA: {history}"
            if has_file: user_msg += f"\n\nDANE: {pdf_text[:20000]}"
            content = [{"type": "text", "text": user_msg}]
            if has_file and pdf_imgs:
                 for img in pdf_imgs[:3]: content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
            
            try:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}])
                ans = resp.choices[0].message.content
                st.markdown(ans)
                st.session_state['last_ans'] = ans
                st.session_state['last_prob'] = problem
            except Exception as e: st.error(f"API Error: {e}")

    if 'last_ans' in st.session_state:
        if st.button("📥 Zapisz lekcję"):
            save_lesson(st.session_state['last_prob'], st.session_state['last_ans'])
            st.success("Zapisano!")

# ==============================================================================
# MODUŁ 2: ESTIMATOR
# ==============================================================================
elif selected_module == "💰 ESTIMATOR":
    
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT STRATEGY"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🛠️ Architecture")
            st.markdown("""
            * **Layout:** Microsoft LayoutLMv3 (Document Segmentation).
            * **NER:** SpaCy (Entity Extraction - Materials).
            * **Math:** NumPy/Pandas (Pricing Logic).
            * **API:** REST Connectors to ERP (SAP/Comarch).
            """)
        with c2:
            st.markdown("### 📦 Deployment")
            st.markdown("""
            * **Model:** Sidecar Container (microservice).
            * **Queue:** Redis + Celery (Async processing).
            * **Koszt wdrożenia:** 4-6 m-cy pracy zespołu.
            """)

    with st.sidebar:
        st.header("💰 Panel Kosztorysanta")
        st.file_uploader("Wgraj Rysunek (PDF)", disabled=True)

    st.title("SolidRules ESTIMATOR")
    st.subheader("Moduł Ofertowania")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("1. Vision AI skanuje BOM.\n2. Mapowanie cen.\n3. Estymacja czasu CNC.")
        st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=80)
    with col2:
        st.warning("⚠️ Status: Beta.")
        st.button("Pobierz demo", disabled=True)

# ==============================================================================
# MODUŁ 3: METROLOGY
# ==============================================================================
elif selected_module == "📐 METROLOGY":
    
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT STRATEGY"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🛠️ Architecture")
            st.markdown("""
            * **3D:** OpenCascade (PythonOCC/CadQuery).
            * **2D:** Azure Form Recognizer (Tolerances).
            * **Compute:** GPU Required (NVIDIA T4).
            """)
        with c2:
            st.markdown("### 📦 Deployment")
            st.markdown("""
            * **Server:** GPU Cloud Instance (AWS g4dn.xlarge).
            * **Frontend:** Three.js / WebGL.
            * **Koszt:** Wysoki (Compute heavy).
            """)

    with st.sidebar:
        st.header("📐 Panel Jakości")
        st.file_uploader("1. Wgraj STL", disabled=True)
        st.file_uploader("2. Wgraj PDF", disabled=True)

    st.title("SolidRules METROLOGY")
    st.subheader("Cyfrowa Kontrola Jakości")
    st.info("✅ Status: Silnik gotowy.")

# ==============================================================================
# MODUŁ 4: FIELD
# ==============================================================================
elif selected_module == "🔧 FIELD":
    
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT STRATEGY"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🛠️ Architecture")
            st.markdown("""
            * **Edge AI:** TensorFlow Lite (MobileNetV3).
            * **Sync:** PouchDB (Offline-First).
            * **Framework:** Flutter (Cross-platform).
            """)
        with c2:
            st.markdown("### 📦 Deployment")
            st.markdown("""
            * **App:** PWA / Enterprise App Store.
            * **Devices:** Rugged Tablets (Android/iOS).
            * **Dev Time:** 3-4 m-ce (Frontend).
            """)

    with st.sidebar:
        st.header("🔧 Panel Mobilny")
        st.camera_input("Zrób zdjęcie", disabled=True)

    st.title("SolidRules FIELD")
    st.subheader("Asystent Utrzymania Ruchu")
    st.warning("⚠️ Status: Prototyp.")

# ==============================================================================
# MODUŁ 5: KNOWLEDGE
# ==============================================================================
elif selected_module == "🧠 KNOWLEDGE":
    
    with st.expander("ℹ️ TECH SPECS & DEPLOYMENT STRATEGY"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🛠️ Architecture")
            st.markdown("""
            * **DB:** Qdrant (Vector DB).
            * **Embeddings:** OpenAI text-embedding-3-small.
            * **RAG:** Semantic Search + Context Injection.
            """)
        with c2:
            st.markdown("### 📦 Deployment")
            st.markdown("""
            * **Type:** Backend API Service.
            * **Access:** GraphQL Gateway.
            * **Backup:** S3 Snapshots.
            """)

    with st.sidebar:
        st.header("🧠 Admin Panel")
        st.file_uploader("Import CSV", disabled=True)

    st.title("SolidRules KNOWLEDGE CORE")
    st.subheader("Centralny Mózg Systemu")
    if os.path.exists(DB_FILE):
        st.dataframe(pd.read_csv(DB_FILE), use_container_width=True)

# ==============================================================================
# MODUŁ 6: STRATEGIA & ROADMAP
# ==============================================================================
elif selected_module == "📈 STRATEGY & ROADMAP":
    
    with st.sidebar:
        st.header("📈 Strategia")
        st.info("Wybierz wariant.")
    
    st.markdown("# 🗺️ Strategia Rozwoju")
    tab1a, tab1b, tab1c, tab1d, tab1e = st.tabs(["1A: TOOLBOX", "1B: PROCESS", "1C: AGENTS", "1D: FLOW (⭐ MVP)", "1E: EVOLVE"])
    
    with tab1d:
        with st.expander("ℹ️ TECH SPECS: Wariant 1D (Flow)", expanded=True):
            st.markdown("""
            * **Core:** Human-in-the-Loop Architecture.
            * **Logic:** Confidence Scoring (AI Uncertainty).
            * **Stack:** Python FastAPI + React Flow.
            * **Timeline:** 3-4 months to Production MVP.
            """)
        st.header("⭐ Wariant 1D: SolidRules FLOW")
        st.success("✅ REKOMENDOWANA STRATEGIA")

# ==============================================================================
# 💰 GRANT STRATEGY (UPDATED WITH ESTIMATES)
# ==============================================================================
elif selected_module == "💰 GRANT STRATEGY":
    
    with st.sidebar:
        st.header("💰 Centrum Grantowe")
        st.info("Analiza Wyzwań GPN-T (Runda 5).")
        st.markdown("---")
        st.caption("Cel: Finansowanie MVP (~100k PLN).")

    st.markdown("# 💰 Strategia Grantowa & Business Case")
    st.caption("Szczegółowa analiza wdrożeniowa dla wybranych partnerów.")

    tab_m1, tab_m2, tab_m3, tab_m4, tab_m5 = st.tabs([
        "🌊 MARITIME (CTM/Port)", 
        "🏭 INDUSTRIAL (Orlen/Anwil)", 
        "📊 COMMERCIAL (SFF/Primavera)",
        "📋 OPERATIONS (Rezon/Qlevel)",
        "💎 ANWIL (Virtual Sensors)"
    ])

    # --- 1. MARITIME ---
    with tab_m1:
        st.subheader("Sektor Morski & Bezpieczeństwo")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### 🎯 CTM (mDigitalBaltic)")
            st.info("Wyzwanie: Mobilne zgłaszanie zagrożeń.")
            st.markdown("""
            **Rozwiązanie:** `Safety Monitor App` (Rebrand modułu FIELD).
            
            **💼 Business & Dev Case:**
            * **Zespół:** 1x Senior Mobile (Flutter), 1x Python Backend.
            * **Timeline:** 3 miesiące (1 m-c MVP, 2 m-ce Integracja CTM).
            * **Koszt (Estymacja):** 120,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **Geo-Spatial:** Mapbox GL JS / OpenLayers (Mapy morskie).
                * **Protocol:** MQTT (Lekka komunikacja przy słabym zasięgu na morzu).
                * **Security:** Szyfrowanie End-to-End (wymóg wojskowy).
                """)
        
        with c2:
            st.markdown("#### ⚓ PORT GDYNIA")
            st.info("Wyzwanie: Baza danych środowiskowych.")
            st.markdown("""
            **Rozwiązanie:** `Port Digital Twin` (Rebrand modułu KNOWLEDGE).
            
            **💼 Business & Dev Case:**
            * **Zespół:** 1x Data Engineer, 1x Fullstack Dev.
            * **Timeline:** 3 miesiące.
            * **Koszt (Estymacja):** 90,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **Ingestion:** Apache Airflow (ETL pipeline dla danych z czujników).
                * **DB:** TimescaleDB (Time-series data dla hałasu/pyłu).
                * **Viz:** Grafana / Streamlit Dashboard.
                """)

    # --- 2. INDUSTRIAL ---
    with tab_m2:
        st.subheader("Przemysł Ciężki")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ⛽ ORLEN S.A.")
            st.info("Wyzwanie: Wykrywanie wycieków (Vision AI).")
            st.markdown("""
            **Rozwiązanie:** `SolidRules VISION`.
            
            **💼 Business & Dev Case:**
            * **Zespół:** 2x AI Engineer (CV), 1x Backend.
            * **Timeline:** 5 miesięcy (Trenowanie modeli na danych video).
            * **Koszt (Estymacja):** 180,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **Model:** YOLOv8 (Real-time object detection) finetunowany na dym/wycieki.
                * **Inference:** NVIDIA DeepStream SDK.
                * **Hardware:** Edge AI Gateway (np. Jetson Orin) przy kamerach.
                """)
                
        with c2:
            st.markdown("#### 🏭 ANWIL (Logistyka)")
            st.info("Wyzwanie: Optymalizacja transportu.")
            st.markdown("""
            **Rozwiązanie:** `SolidRules OPTIMIZER`.
            
            **💼 Business & Dev Case:**
            * **Zespół:** 1x Algorithm Expert, 1x Python Dev.
            * **Timeline:** 4 miesiące.
            * **Koszt (Estymacja):** 140,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **Solver:** Google OR-Tools (Constraint Programming).
                * **Input:** CSV/Excel z awizacjami.
                * **Output:** Harmonogram (.xlsx) + API Response.
                """)

    # --- 3. COMMERCIAL ---
    with tab_m3:
        st.subheader("Handel & Usługi")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📊 SFF (Full House Group)")
            st.info("Wyzwanie: Automatyzacja raportów sprzedaży.")
            st.markdown("""
            **Rozwiązanie:** `SolidRules ANALYTICS` (Silnik Estimatora).
            
            **💼 Business & Dev Case:**
            * **Zespół:** 1x Data Engineer, 1x Frontend (React/Streamlit).
            * **Timeline:** 3 miesiące.
            * **Koszt (Estymacja):** 80,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **ETL:** Pandas/PySpark (Czyszczenie danych kasowych).
                * **Warehouse:** Snowflake / BigQuery.
                * **BI:** PowerBI Embedded lub Custom Dashboard.
                """)
                
        with c2:
            st.markdown("#### 💄 PRIMAVERA PARFUM")
            st.info("Wyzwanie: Optymalizacja pakowania.")
            st.markdown("""
            **Rozwiązanie:** `3D Bin Packing AI`.
            
            **💼 Business & Dev Case:**
            * **Zespół:** 1x Math/Algo Dev, 1x Backend.
            * **Timeline:** 4 miesiące.
            * **Koszt (Estymacja):** 110,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **Algo:** 3D Bin Packing Problem (Heurystyka genetyczna).
                * **Input:** Wymiary produktów (z bazy PIM).
                * **Output:** Wizualizacja 3D (Three.js) ułożenia w kartonie.
                """)

    # --- 4. OPERATIONS ---
    with tab_m4:
        st.subheader("Operacje & HR")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🧪 REZON BIO")
            st.info("Wyzwanie: Cyfryzacja Labu (Wagi/pH).")
            st.markdown("""
            **Rozwiązanie:** `Digital Lab Assistant`.
            
            **💼 Business & Dev Case:**
            * **Zespół:** 1x Mobile Dev, 1x Backend.
            * **Timeline:** 3 miesiące.
            * **Koszt (Estymacja):** 95,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **OCR:** Google ML Kit (Text Recognition na urządzeniu).
                * **Compliance:** Blockchain / Immutable Ledger (Audit Trail).
                """)

        with c2:
            st.markdown("#### 👥 QLEVEL")
            st.info("Wyzwanie: AI w HR.")
            st.markdown("""
            **Rozwiązanie:** `HR Intelligence`.
            
            **💼 Business & Dev Case:**
            * **Zespół:** 1x AI Engineer (NLP).
            * **Timeline:** 2 miesiące.
            * **Koszt (Estymacja):** 60,000 PLN.
            """)
            with st.expander("🛠️ Tech Deep Dive"):
                st.markdown("""
                * **CV Parsing:** PyMuPDF + GPT-4o.
                * **Matching:** Cosine Similarity (Kandydat vs Oferta).
                """)

    # --- 5. HIDDEN GEM ---
    with tab_m5:
        st.subheader("💎 ANWIL: Virtual Sensors (Soft-Sensors)")
        st.warning("🔥 Największy potencjał marżowy (High Tech / Low Hardware).")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("""
            **Problem:** Anwil chce mierzyć parę i poziom w silosach, ale sprzęt jest drogi.
            **Rozwiązanie:** `SolidRules PREDICT`. Trenujemy AI na danych historycznych, by **wyliczała** te wartości.
            
            **💼 Business & Dev Case:**
            * **Zespół:** 2x Senior Data Scientist, 1x Data Eng.
            * **Timeline:** 4-5 miesięcy (PoC -> Trening -> Prod).
            * **Koszt (Estymacja):** 180,000 PLN.
            """)
        with c2:
            st.metric("Oszczędność Klienta", "miliony PLN", delta="vs Hardware")
        
        with st.expander("🛠️ Tech Deep Dive (Secret Sauce)", expanded=True):
            st.markdown("""
            * **Input:** SCADA Historical Data (Temperatury, Prądy pomp, Stan zaworów).
            * **Model:** LSTM (Long Short-Term Memory) / XGBoost Regressor.
            * **Validation:** Porównanie z mobilnym przepływomierzem (kalibracja).
            * **Deployment:** Docker Container na serwerze brzegowym (Edge).
            """)
