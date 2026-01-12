import streamlit as st
import tempfile
import os
import nest_asyncio
import pdfplumber
import fitz  # PyMuPDF
import base64
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

st.set_page_config(page_title="SolidRules AI: Expert System", page_icon="🛡️", layout="wide")

# --- TŁUMACZENIA (SUPER-PROMPT "CRITIC & TRIZ") ---
translations = {
    "PL": {
        "title": "SolidRules: Vision + TRIZ + Safety Check",
        "sidebar_title": "🛡️ SolidRules v3.5 (Expert)",
        "instruction_header": "**Instrukcja:**",
        "instr_1": "1. Wgraj dokumentację (PDF z Rysunkiem/Normą).",
        "instr_2": "2. Opisz problem inżynierski.",
        "instr_3": "3. Kliknij Generuj.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Opisz problem lub sprzeczność techniczną:",
        "placeholder": "Np. Muszę zwiększyć ciśnienie robocze, ale nie mogę zmienić geometrii zbiornika...",
        "button": "🚀 Analizuj i Weryfikuj (TRIZ)",
        "upload_label": "📂 Wgraj dokumentację / Rysunki (PDF)",
        "report_header": "### 💡 Raport Ekspercki (TRIZ & Safety)",
        "disclaimer": "⚠️ **Nota prawna:** System wspomagania decyzji. Wymagana weryfikacja przez uprawnionego inżyniera.",
        "status_ok": "✅ Dane wczytane: Tekst ({engine}) + Obrazy ({img_count} str.).",
        
        # --- MÓZG SYTEMU: PROMPT INSPIROWANY "CLAUDE SKILLS" ---
        "system_prompt": """Jesteś Głównym Konstruktorem, Ekspertem TRIZ i Audytorem Bezpieczeństwa (zgodnie z dyrektywami UE, np. PED).
        
        DANE WEJŚCIOWE:
        1. OBRAZY: Rysunki techniczne, wykresy (Vision AI).
        2. TEKST: Normy, DTR, ograniczenia prawne.
        
        TWOJE ZADANIE: 
        Rozwiązać problem inżynierski, a następnie przeprowadzić BEZWZGLĘDNĄ KRYTYKĘ własnych rozwiązań w oparciu o dokumentację.
        
        PROCEDURA MYŚLENIA (Chain of Thought):
        
        KROK 1: DIAGNOZA SOKRATEJSKA (Vision + Text)
        - Spójrz na obrazy. Zidentyfikuj kluczowe elementy (np. spoiny, kształt dna, osie wykresu).
        - Zidentyfikuj braki w danych. Jeśli czegoś nie wiesz, przyjmij bezpieczne założenie (Worst Case Scenario) i zaznacz to.
        
        KROK 2: GENEROWANIE ROZWIĄZAŃ (TRIZ)
        - Zdefiniuj Sprzeczność Techniczną (Co chcesz poprawić vs Co się pogarsza).
        - Wybierz 3 konkretne Zasady TRIZ.
        - Opisz jak je wdrożyć fizycznie w tym konkretnym urządzeniu.
        
        KROK 3: FAZA KRYTYKA (Safety Check & Compliance) - KLUCZOWE!
        - Wciel się w rolę Inspektora UDT/TDT.
        - Przeskanuj wgrany tekst PDF. Czy proponowane zmiany są legalne?
        - Czy zmiana parametrów (np. ciśnienia) przesuwa punkt pracy na wykresie w niebezpieczną strefę (np. Kategoria III -> IV)?
        - Wymień ryzyka.
        
        FORMAT ODPOWIEDZI (Markdown):
        
        ## 1. 👁️ Diagnoza Wizualna i Założenia
        (Co widzę na rysunku/wykresie + Jakie przyjąłem założenia bezpieczeństwa)
        
        ## 2. ⚙️ Sprzeczność Techniczna (TRIZ)
        * **Konflikt:** ...
        
        ## 3. 💡 Proponowane Koncepcje
        (3 rozwiązania. Dla każdego: Zasada TRIZ + Opis Techniczny)
        
        ## 4. 🛡️ RAPORT RYZYKA (CRITICAL REVIEW)
        * **Analiza Zgodności (PDF):** (Cytuj normę/wykres. Czy rozwiązanie jest dopuszczalne?)
        * **Zidentyfikowane Zagrożenia:** (Co może pójść nie tak?)
        * **Rekomendacja:** (Wdrożyć / Odrzucić / Wymagane badania NDT)
        
        Bądź konkretny, innowacyjny, ale przede wszystkim ODPOWIEDZIALNY. Odpowiadaj po POLSKU."""
    },
    "EN": {
        "title": "SolidRules: Vision + TRIZ + Safety Check",
        "sidebar_title": "🛡️ SolidRules v3.5 (Expert)",
        "instruction_header": "**Instructions:**",
        "instr_1": "1. Upload Docs (PDF with Drawings/Standards).",
        "instr_2": "2. Describe engineering problem.",
        "instr_3": "3. Click Generate.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Describe problem or contradiction:",
        "placeholder": "E.g. I need to increase pressure but cannot change geometry...",
        "button": "🚀 Analyze & Verify (TRIZ)",
        "upload_label": "📂 Upload Docs / Drawings (PDF)",
        "report_header": "### 💡 Expert Report (TRIZ & Safety)",
        "disclaimer": "⚠️ **Disclaimer:** AI Decision Support. Requires certified engineer verification.",
        "status_ok": "✅ Data loaded: Text ({engine}) + Images ({img_count} pages).",
        "system_prompt": """You are a Chief Design Engineer, TRIZ Expert, and Safety Auditor.
        
        INPUT DATA:
        1. IMAGES: Technical drawings, charts (Vision AI).
        2. TEXT: Standards, manuals, legal constraints.
        
        TASK: 
        Solve the problem using TRIZ, then perform a RUTHLESS CRITIQUE of your own solutions based on the documentation.
        
        THOUGHT PROCESS (Chain of Thought):
        
        STEP 1: SOCRATIC DIAGNOSIS (Vision + Text)
        - Analyze images. Identify hotspots.
        - Identify missing data. Assume Worst Case Scenario if data is missing.
        
        STEP 2: TRIZ SOLUTIONS
        - Define Technical Contradiction.
        - Select 3 TRIZ Principles.
        - Describe physical implementation.
        
        STEP 3: CRITIC PHASE (Safety Check & Compliance)
        - Act as a Safety Inspector.
        - Scan PDF text. Are changes legal?
        - Does the operating point shift to a dangerous zone on the graph?
        
        RESPONSE FORMAT:
        ## 1. Visual Diagnosis & Assumptions
        ## 2. Technical Contradiction
        ## 3. Concepts (TRIZ)
        ## 4. 🛡️ RISK REPORT (CRITICAL REVIEW)
        * **Compliance Analysis:** (Cite PDF/Graph)
        * **Risks:**
        * **Recommendation:**
        
        Answer in ENGLISH."""
    }
}

# --- FUNKCJE BACKENDOWE (BEZ ZMIAN) ---
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
    st.info("Modules: Vision AI + TRIZ + Compliance Check")
    st.caption(t["footer"])

st.title(t["title"])

uploaded_file = st.file_uploader(t["upload_label"], type=["pdf"])
pdf_text_context = ""
pdf_images_list = []

if uploaded_file is not None:
    with st.spinner("⚙️ Analiza inżynierska (OCR + Vision)..."):
        file_bytes = uploaded_file.getvalue()
        pdf_text_context, engine_name = parse_hybrid(file_bytes)
        pdf_images_list = pdf_to_images_base64(file_bytes)
        if pdf_text_context and pdf_images_list:
            st.success(t["status_ok"].format(engine=engine_name, img_count=len(pdf_images_list)))
            with st.expander("Podgląd dokumentacji"):
                if pdf_images_list: st.image(base64.b64decode(pdf_images_list[0]), width=300)

problem = st.text_area(t["label_problem"], height=100, placeholder=t["placeholder"])
generate_button = st.button(t["button"], type="primary", use_container_width=True)

if generate_button and problem and pdf_images_list:
    with st.spinner("🧠 Uruchamiam: Vision AI -> TRIZ -> Inspektor Bezpieczeństwa..."):
        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = [{"role": "system", "content": t["system_prompt"]}]
        
        # Kontekst użytkownika
        user_content = [{"type": "text", "text": f"PROBLEM UŻYTKOWNIKA: {problem}\n\nKONTEKST Z DOKUMENTACJI (OCR):\n{pdf_text_context[:40000]}"}]
        
        # Dodajemy max 3 obrazy (Vision)
        for i, img in enumerate(pdf_images_list[:3]):
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
            
        messages.append({"role": "user", "content": user_content})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.6 # Balans między kreatywnością a rygorem
        )
        st.markdown(t["report_header"])
        st.markdown(response.choices[0].message.content)
        st.warning(t["disclaimer"])
elif generate_button:
    st.warning("⚠️ Proszę wgrać plik PDF przed generowaniem rozwiązania.")
