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
        hr { border-color: #333; }
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
                matches.append(f"- [CASE: {row['date']}] {str(row['solution'])[:200]}...")
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
# 🧭 TOP MENU (GÓRNA NAWIGACJA)
# ==========================================
# Używamy columns, żeby wyśrodkować menu, lub po prostu radio na górze
st.markdown("<div style='text-align: center; margin-bottom: 5px; color: #6366f1; font-size: 0.8em; letter-spacing: 2px;'>SOLIDRULES ECOSYSTEM</div>", unsafe_allow_html=True)

selected_app = st.radio(
    "Nawigacja",
    ["🚀 INNOVATE", "💰 ESTIMATOR", "📐 METROLOGY", "🔧 FIELD", "🧠 KNOWLEDGE"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---") # Oddzielenie menu od treści

# ==========================================
# 🚀 APLIKACJA 1: INNOVATE (KONSTRUKCJA)
# ==========================================
if selected_app == "🚀 INNOVATE":
    
    # --- SIDEBAR DLA INNOVATE ---
    with st.sidebar:
        st.header("🚀 Panel Konstruktora")
        st.info("Tutaj wgrywasz dokumentację, którą chcesz przeanalizować.")
        uploaded_file = st.file_uploader("Wgraj Rysunek / Normę (PDF)", type=["pdf"])
        st.markdown("---")
        st.caption("Silnik: GPT-4o + TRIZ")

    # --- MAIN SCREEN ---
    st.title("SolidRules INNOVATE")
    st.caption("Asystent R&D: Rozwiązywanie problemów, TRIZ i Weryfikacja Norm")

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
        
    problem = st.text_area("Opisz problem techniczny:", height=150, placeholder="Np. Element pęka przy 50 barach. Jak to wzmocnić bez zwiększania masy?")
    
    if st.button("Generuj Rozwiązanie", type="primary"):
        history = search_lessons(problem)
        messages = [{"role": "system", "content": "Jesteś Głównym Inżynierem. Jeśli pytanie jest proste, odpowiedz krótko. Jeśli to problem, użyj TRIZ."}]
        
        user_msg = f"PYTANIE: {problem}\n\nHISTORIA FIRMY:\n{history}"
        if has_file: user_msg += f"\n\nDOKUMENTACJA:\n{pdf_text[:20000]}"
        
        content = [{"type": "text", "text": user_msg}]
        if has_file and pdf_imgs:
             for img in pdf_imgs[:3]: content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
        
        messages.append({"role": "user", "content": content})
        
        try:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            with st.spinner("Analiza..."):
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
    
    # --- SIDEBAR DLA ESTIMATOR ---
    with st.sidebar:
        st.header("💰 Panel Kosztorysanta")
        st.info("Wgraj rysunek złożeniowy, aby wygenerować BOM.")
        st.file_uploader("Wgraj Rysunek Złożeniowy (PDF)", disabled=True)
        st.markdown("---")
        st.metric("Kurs Euro", "4.32 PLN")
        st.metric("Cena Stali (S235)", "4.50 PLN/kg")

    # --- MAIN SCREEN ---
    st.title("SolidRules ESTIMATOR")
    st.subheader("Automatyzacja Ofertowania i Kalkulacji Kosztów")
    
    st.markdown("""
    ### ⚙️ Jak to działa? (Workflow)
    
    1.  **Ekstrakcja BOM (Bill of Materials):**
        * Vision AI skanuje rysunek techniczny.
        * Lokalizuje tabelę rysunkową.
        * Wyciąga listę części, materiały i ilości do ustrukturyzowanej tabeli.
    
    2.  **Kalkulator Materiałowy:**
        * System rozpoznaje gatunki materiałów (np. 1.4301, S355).
        * Oblicza objętość detalu na podstawie wymiarów gabarytowych.
        * Mnoży przez gęstość materiału i aktualną cenę rynkową.
    
    3.  **Szacowanie "Shape Complexity":**
        * Algorytm analizuje geometrię 2D.
        * Dużo wymiarów tolerowanych i rzutów? -> **Wysoka złożoność (Droga obróbka).**
        * Prosty kształt z palnika? -> **Niska złożoność (Tania obróbka).**
        
    4.  **Wynik:**
        * Gotowy plik Excel / PDF z ofertą dla klienta.
    """)
    
    st.info("Moduł w fazie R&D. Przewidywane wdrożenie: Q3 2026.")
    st.image("https://cdn-icons-png.flaticon.com/512/4011/4011166.png", width=100)

# ==========================================
# 📐 APLIKACJA 3: METROLOGY (JAKOŚĆ)
# ==========================================
elif selected_app == "📐 METROLOGY":
    
    # --- SIDEBAR DLA METROLOGY ---
    with st.sidebar:
        st.header("📐 Panel Kontroli Jakości")
        st.file_uploader("1. Wgraj Model 3D (.STL/.STEP)", disabled=True)
        st.file_uploader("2. Wgraj Rysunek 2D (.PDF)", disabled=True)
        st.markdown("---")
        st.checkbox("Analiza GD&T", value=True, disabled=True)
        st.checkbox("Analiza Kolizji", value=False, disabled=True)

    # --- MAIN SCREEN ---
    st.title("SolidRules METROLOGY")
    st.subheader("Weryfikacja Zgodności 3D vs 2D")
    
    st.markdown("""
    ### ⚙️ Jak to działa? (Workflow)
    
    1.  **Cyfrowy Bliźniak (Digital Twin Check):**
        * Wgrywasz model 3D (to co skonstruowano) i rysunek 2D (to co ma być wyprodukowane).
        * System sprawdza spójność: Czy wymiary na rysunku zgadzają się z bryłą 3D?
    
    2.  **Analiza GD&T (Geometric Dimensioning and Tolerancing):**
        * Silnik geometryczny (CadQuery) mierzy płaskość, równoległość i pozycję otworów w modelu 3D.
        * AI odczytuje ramki tolerancji z rysunku PDF.
        * Porównuje wyniki: **PASS / FAIL**.
    
    3.  **Raportowanie:**
        * Automatyczne generowanie raportu pomiarowego (przed wysłaniem na produkcję).
        * Wykrywanie "niemożliwych tolerancji" na etapie projektu.
    """)
    
    st.info("Prototyp silnika geometrycznego jest gotowy. Trwa integracja z interfejsem.")

# ==========================================
# 🔧 APLIKACJA 4: FIELD (SERWIS)
# ==========================================
elif selected_app == "🔧 FIELD":
    
    # --- SIDEBAR DLA FIELD ---
    with st.sidebar:
        st.header("🔧 Panel Mobilny")
        st.info("Zrób zdjęcie telefonem.")
        st.camera_input("Zrób zdjęcie części", disabled=True)
        st.text_input("Szukaj po kodzie błędu", placeholder="np. E-502")

    # --- MAIN SCREEN ---
    st.title("SolidRules FIELD")
    st.subheader("Inteligentny Asystent Utrzymania Ruchu (Mobile)")
    
    st.markdown("""
    ### ⚙️ Jak to działa? (Workflow)
    
    1.  **Rozpoznawanie Wizualne:**
        * Serwisant robi zdjęcie uszkodzonej części lub tabliczki znamionowej.
        * Vision AI identyfikuje komponent (np. "Pompa hydrauliczna Rexroth typ X").
    
    2.  **Błyskawiczny Dostęp do DTR:**
        * System przeszukuje tysiące stron instrukcji (DTR).
        * Wyświetla **tylko** stronę z procedurą wymiany/naprawy dla tego konkretnego modelu.
    
    3.  **Diagnostyka Audio (Smart Sound):**
        * Serwisant nagrywa dźwięk pracującej maszyny.
        * Algorytm FFT (analiza widma) wykrywa anomalie typowe dla zużytych łożysk lub kawitacji pomp.
        
    4.  **Integracja z Magazynem:**
        * "Część zidentyfikowana. Stan magazynowy: 2 sztuki. Półka B-12."
    """)
    
    st.success("Aplikacja projektowana w technologii PWA (Progressive Web App) dla tabletów i smartfonów.")

# ==========================================
# 🧠 APLIKACJA 5: KNOWLEDGE (BAZA)
# ==========================================
elif selected_app == "🧠 KNOWLEDGE":
    
    # --- SIDEBAR DLA KNOWLEDGE ---
    with st.sidebar:
        st.header("🧠 Zarządzanie Wiedzą")
        st.write("Panel Administratora")
        
        with st.expander("📥 Importuj Dane Firmowe"):
            up_db = st.file_uploader("Wgraj Excel/CSV", type=["xlsx", "csv"])
            if up_db:
                st.write("Mapowanie kolumn...")
                st.button("Scal z bazą SolidRules", disabled=True)

    # --- MAIN SCREEN ---
    st.title("SolidRules KNOWLEDGE CORE")
    st.subheader("Centralny Mózg Systemu")
    
    st.markdown("""
    ### ⚙️ Rola w ekosystemie
    
    To nie jest zwykła baza danych. To **Pamięć Zbiorowa** Twojej firmy.
    Każdy problem rozwiązany w *Innovate* lub *Field* trafia tutaj.
    
    1.  **Lessons Learnt (Lekcje):**
        * Automatyczne zapisywanie rozwiązanych problemów.
        * Uczenie się na błędach: "Nie stosuj uszczelek NBR przy 150°C (Awaria z 2024)".
    
    2.  **Semantic Search (Wyszukiwanie Semantyczne):**
        * Możesz wpisać "coś stuka w silniku", a system znajdzie raport o "luzie łożyskowym" (rozumie kontekst, nie tylko słowa).
        
    3.  **API dla Innych Modułów:**
        * *Innovate* pyta bazę: "Czy to rozwiązanie jest bezpieczne?"
        * *Estimator* pyta bazę: "Ile to kosztowało rok temu?"
    """)
    
    st.markdown("### 📊 Aktualny stan wiedzy")
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Baza wiedzy jest pusta.")
