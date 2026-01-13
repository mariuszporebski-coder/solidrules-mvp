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
from datetime import datetime
from openai import OpenAI
from llama_parse import LlamaParse

# --- NAPRAWA ASYNCIO (DLA JUPYTER/STREAMLIT CLOUD) ---
nest_asyncio.apply()

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SolidRules Ecosystem", page_icon="💠", layout="wide")

# --- CSS (PRO DESIGN & TOP MENU) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        header {visibility: hidden;}
        .stApp { background-color: #050505; }
        
        /* Pasek Boczny */
        section[data-testid="stSidebar"] { 
            background-color: #0c0c0c; 
            border-right: 1px solid #1e1e1e; 
        }
        
        /* GÓRNE MENU (Nawigacja) */
        div[role="radiogroup"] {
            display: flex;
            justify-content: center;
            background-color: #0c0c0c;
            padding: 10px;
            border-radius: 12px;
            border: 1px solid #1e1e1e;
            margin-bottom: 20px;
        }
        div[role="radiogroup"] label {
            background-color: transparent;
            border: none;
            color: #94a3b8;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 6px;
            transition: all 0.2s;
            margin: 0 5px;
        }
        div[role="radiogroup"] label:hover {
            color: white;
            background-color: #1e1e2e;
        }
        /* Aktywna zakładka */
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: #6366f1 !important;
            color: white !important;
            font-weight: 600;
            box-shadow: 0 2px 10px rgba(99, 102, 241, 0.3);
        }

        /* Elementy UI */
        .stTextInput input, .stTextArea textarea {
            background-color: #111111 !important; color: #e2e8f0 !important;
            border: 1px solid #333 !important; border-radius: 8px !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: #6366f1 !important; box-shadow: 0 0 0 1px #6366f1 !important;
        }
        div.stButton > button {
            background-color: #1e1e2e; color: white; border: 1px solid #333;
            border-radius: 8px; transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #6366f1; border-color: #6366f1; color: white;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(to right, #4f46e5, #6366f1); border: none;
        }
        h1, h2, h3 { color: #f8fafc !important; }
        p, li, label, .stMarkdown { color: #94a3b8 !important; }
        .stSuccess { background-color: #064e3b !important; color: #a7f3d0 !important; }
        .stInfo { background-color: #1e293b !important; color: #94a3b8 !important; }
        .stWarning { background-color: #451a03 !important; color: #fdba74 !important; }
        hr { border-color: #333; }
        
        /* Spinner */
        .stSpinner > div { border-top-color: #6366f1 !important; }
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

# --- FUNKCJE BACKENDOWE (DB, OCR) ---
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
    # Próba LlamaParse (jeśli klucz jest)
    ll_key = st.secrets.get("LLAMA_CLOUD_API_KEY", None)
    if ll_key:
        try:
            parser = LlamaParse(api_key=ll_key, result_type="markdown", premium_mode=True, language="pl")
            docs = parser.load_data(tmp_path)
            if docs: text_content = "\n\n".join([d.text for d in docs])
        except: pass
    
    # Fallback do PDFPlumber
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
# 🧭 TOP MENU (GÓRNA NAWIGACJA)
# ==========================================
st.markdown("<div style='text-align: center; margin-bottom: 5px; color: #6366f1; font-size: 0.8em; letter-spacing: 2px;'>SOLIDRULES ECOSYSTEM v4.5</div>", unsafe_allow_html=True)

selected_app = st.radio(
    "Nawigacja",
    ["🚀 INNOVATE", "💰 ESTIMATOR", "📐 METROLOGY", "🔧 FIELD", "🧠 KNOWLEDGE"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ==========================================
# 🚀 APLIKACJA 1: INNOVATE (KONSTRUKCJA + WATCHDOG + MES)
# ==========================================
if selected_app == "🚀 INNOVATE":
    
    # --- SIDEBAR: KONTEKST + WATCHDOG ---
    with st.sidebar:
        st.header("🚀 Panel Konstruktora")
        
        # 1. WATCHDOG (STRAŻNIK LEGISLACYJNY)
        st.markdown("### 🛡️ Watchdog Status")
        watchdog_status = "OSTRZEŻENIE" 
        
        if watchdog_status == "OK":
            st.success("✅ Normy Aktualne")
        elif watchdog_status == "OSTRZEŻENIE":
            st.warning("⚠️ Wykryto zmiany w prawie!")
            with st.expander("Szczegóły alertu"):
                st.write("**Dyrektywa Maszynowa:** Planowana rewizja art. 12 w Q4 2026.")
                st.write("**Norma PN-EN ISO 12100:** Zalecana weryfikacja oceny ryzyka.")
        
        st.markdown("---")
        
        # 2. UPLOADER
        st.info("Wgrywanie dokumentacji:")
        uploaded_file = st.file_uploader("Rysunek / Norma / DTR (PDF)", type=["pdf"])
        st.caption("Silnik: GPT-4o + Vision + Physics Engine")

    # --- MAIN SCREEN ---
    st.title("SolidRules INNOVATE")
    st.caption("AI-Powered R&D: Rozwiązywanie problemów & Szybka Symulacja")

    # Logika aplikacji Innovate
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
        
        # --- PODGLĄD + INSTANT MES (NOWOŚĆ) ---
        col_view, col_mes = st.columns([1, 1])
        
        with col_view:
            st.markdown("**Podgląd oryginału:**")
            if pdf_imgs:
                st.image(base64.b64decode(pdf_imgs[0]), use_container_width=True)
                
        with col_mes:
            st.markdown("**⚡ Instant MES (AI Prediction):**")
            # Symulacja działania przycisku
            if st.button("Uruchom Szybką Analizę Naprężeń (3s)"):
                with st.spinner("AI przewiduje rozkład naprężeń (Heatmap)..."):
                    time.sleep(2) # Symulacja myślenia
                    # Placeholder heatmapy
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Fem_pole_c.jpg/640px-Fem_pole_c.jpg", 
                             caption="Przewidywane Hotspoty (Czerwone = Ryzyko pęknięcia)",
                             use_container_width=True)
                    
                    st.error("Wykryto spiętrzenie naprężeń w narożniku A! (Współczynnik K > 3.0).")
                    st.markdown("💡 **Sugestia TRIZ:** Zastosuj zaokrąglenie progresywne lub zmień geometrię na eliptyczną.")
            else:
                st.info("Kliknij, aby nałożyć mapę naprężeń bez uruchamiania Ansysa/SolidWorksa.")

    st.markdown("---")
    
    # --- CZAT INŻYNIERSKI (TRIZ / LIBRARIAN) ---
    problem = st.text_area("Opisz problem techniczny lub zadaj pytanie do norm:", height=100, placeholder="Np. Jak zredukować masę tego wspornika zachowując sztywność?")
    
    if st.button("Generuj Rozwiązanie (TRIZ & Safety)", type="primary"):
        history = search_lessons(problem)
        
        # --- INTELIGENTNY SYSTEM PROMPT (BIBLIOTEKARZ vs TRIZ) ---
        system_prompt = """Jesteś Głównym Inżynierem. Masz dwa tryby działania. Musisz SAM zdecydować, którego użyć.

        TRYB 1: BIBLIOTEKARZ (Pytania o dane)
        Kiedy użyć: Pytania typu "Ile wynosi X?", "Jaki skok?", "Co mówi norma?".
        ZASADA: Podaj konkrety z tabeli/tekstu. Nie wymyślaj problemów.

        TRYB 2: EKSPERT TRIZ (Rozwiązywanie problemów)
        Kiedy użyć: Użytkownik zgłasza problem, awarię lub pyta "Jak poprawić?".
        ZASADA (Chain of Thought):
        1. DIAGNOZA.
        2. TRIZ (Sprzeczność + Zasady).
        3. KRYTYK (Ryzyko + Normy).
        
        DODATKOWO: Masz dostęp do bazy 'Lessons Learnt' (Historia Firmy). Jeśli coś tam jest, wspomnij o tym.
        """
        
        user_msg = f"PYTANIE: {problem}\n\nHISTORIA FIRMY:\n{history}"
        if has_file: user_msg += f"\n\nDOKUMENTACJA (OCR):\n{pdf_text[:30000]}"
        
        content = [{"type": "text", "text": user_msg}]
        if has_file and pdf_imgs:
             for img in pdf_imgs[:3]: content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
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
# 💰 APLIKACJA 2: ESTIMATOR (WYCENY)
# ==========================================
elif selected_app == "💰 ESTIMATOR":
    with st.sidebar:
        st.header("💰 Panel Kosztorysanta")
        st.info("Wgraj rysunek złożeniowy, aby wygenerować BOM.")
        st.file_uploader("Wgraj Rysunek Złożeniowy (PDF)", disabled=True)
        st.markdown("---")
        st.metric("Kurs Euro", "4.32 PLN")
        st.metric("Cena Stali (S235)", "4.50 PLN/kg")

    st.title("SolidRules ESTIMATOR")
    st.subheader("Automatyzacja Ofertowania")
    st.markdown("""
    ### ⚙️ Workflow:
    1.  **Vision AI (BOM):** Skanuje tabelę rysunkową i wyciąga listę części.
    2.  **Kalkulator:** Rozpoznaje materiały i liczy wagę netto.
    3.  **Shape Complexity:** Algorytm ocenia złożoność obróbki (Liczba operacji CNC).
    """)
    st.info("Moduł w fazie R&D. Przewidywane wdrożenie: Q3 2026.")
    st.image("https://cdn-icons-png.flaticon.com/512/4011/4011166.png", width=100)

# ==========================================
# 📐 APLIKACJA 3: METROLOGY (JAKOŚĆ)
# ==========================================
elif selected_app == "📐 METROLOGY":
    with st.sidebar:
        st.header("📐 Panel Kontroli Jakości")
        st.file_uploader("1. Wgraj Model 3D (.STL/.STEP)", disabled=True)
        st.file_uploader("2. Wgraj Rysunek 2D (.PDF)", disabled=True)
        st.checkbox("Analiza GD&T", value=True, disabled=True)

    st.title("SolidRules METROLOGY")
    st.subheader("Weryfikacja Zgodności 3D vs 2D")
    st.markdown("""
    ### ⚙️ Workflow:
    1.  **Digital Twin Check:** Porównuje geometrię 3D z wymiarami na PDF.
    2.  **Analiza GD&T:** Silnik CadQuery weryfikuje płaskość i pozycję otworów.
    3.  **Raport:** Generuje "PASS/FAIL" dla każdego wymiaru krytycznego.
    """)
    st.info("Prototyp silnika geometrycznego jest gotowy. Trwa integracja z interfejsem.")

# ==========================================
# 🔧 APLIKACJA 4: FIELD (SERWIS)
# ==========================================
elif selected_app == "🔧 FIELD":
    with st.sidebar:
        st.header("🔧 Panel Mobilny")
        st.info("Zrób zdjęcie telefonem.")
        st.camera_input("Zrób zdjęcie części", disabled=True)
        st.text_input("Szukaj po kodzie błędu", placeholder="np. E-502")

    st.title("SolidRules FIELD")
    st.subheader("Inteligentny Asystent Utrzymania Ruchu")
    st.markdown("""
    ### ⚙️ Workflow:
    1.  **Visual Search:** Rozpoznaje część ze zdjęcia.
    2.  **DTR Lookup:** Otwiera procedurę wymiany w dokumentacji.
    3.  **Audio Diagnostyka:** Analiza widma dźwięku (wykrywanie zużytych łożysk).
    """)
    st.success("Aplikacja projektowana jako PWA (Mobile-First).")

# ==========================================
# 🧠 APLIKACJA 5: KNOWLEDGE (BAZA)
# ==========================================
elif selected_app == "🧠 KNOWLEDGE":
    with st.sidebar:
        st.header("🧠 Zarządzanie Wiedzą")
        with st.expander("📥 Importuj Dane Firmowe"):
            uploaded_db = st.file_uploader("Wgraj plik z historią (.xlsx, .csv)", type=["csv", "xlsx"])
            if uploaded_db:
                try:
                    if uploaded_db.name.endswith('.csv'): df_imp = pd.read_csv(uploaded_db)
                    else: df_imp = pd.read_excel(uploaded_db)
                    st.write("Podgląd:", df_imp.head(3))
                    col_p = st.selectbox("Kolumna PROBLEM", df_imp.columns)
                    col_s = st.selectbox("Kolumna ROZWIĄZANIE", df_imp.columns)
                    if st.button("🔀 Scal z bazą"):
                        df_new = pd.DataFrame({
                            "date": [datetime.now().strftime("%Y-%m-%d")]*len(df_imp),
                            "problem": df_imp[col_p],
                            "solution": df_imp[col_s],
                            "tags": "Imported"
                        })
                        df_new.to_csv(DB_FILE, mode='a', header=False, index=False)
                        st.success(f"Zaimportowano {len(df_imp)} wpisów!")
                except Exception as e: st.error(str(e))

    st.title("SolidRules KNOWLEDGE CORE")
    st.subheader("Centralny Mózg Systemu")
    st.markdown("Tu trafiają wszystkie rozwiązania z modułów Innovate i Field.")
    
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Baza wiedzy jest pusta.")
