import streamlit as st
import pdfplumber
from openai import OpenAI

# --- KONFIGURACJA ---
# Teraz potrzebujemy TYLKO klucza OpenAI. LlamaCloud omijamy.
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("Brak klucza OpenAI! Ustaw go w Streamlit Cloud Secrets.")
    st.stop()

st.set_page_config(
    page_title="SolidRules AI",
    page_icon="🛡️",
    layout="wide"
)

# --- TŁUMACZENIA ---
translations = {
    "PL": {
        "title": "SolidRules: Asystent Inżyniera (Silnik: PDFPlumber)",
        "sidebar_title": "🛡️ SolidRules v0.4 (Local)",
        "instruction_header": "**Instrukcja:**",
        "instr_1": "1. Wgraj plik PDF (Norma/DTR).",
        "instr_2": "2. Opisz problem.",
        "instr_3": "3. Kliknij Generuj.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Twój problem / Pytanie do dokumentacji:",
        "placeholder": "Np. Jaka jest kategoria zbiornika dla PS=45bar i V=150L?",
        "button": "🚀 Analizuj i Generuj",
        "warning_short": "⚠️ Opisz problem dokładniej.",
        "spinner_pdf": "📂 Skanuję plik lokalnie (PDFPlumber)...",
        "spinner_ai": "🧠 Analizuję dane i szukam rozwiązania...",
        "report_header": "### 💡 Raport Inżynierski",
        "disclaimer": "⚠️ **Nota prawna:** Zweryfikuj dane z oryginałem. AI może popełniać błędy.",
        "upload_label": "📂 Wgraj dokumentację (PDF)",
        "file_success": "✅ Plik wczytany (Stron: {pages})",
        "system_prompt_base": """Jesteś Głównym Technologiem. 
        ZASADY:
        1. Odpowiadaj GŁÓWNIE na podstawie wgranego tekstu PDF.
        2. Jeśli w tekście są tabele, postaraj się odczytać z nich wartości.
        3. Jeśli nie masz pewności, napisz to wprost.
        4. Bądź konkretny i techniczny.
        5. Odpowiadaj w języku POLSKIM."""
    },
    "EN": {
        "title": "SolidRules: Engineering Assistant (Engine: PDFPlumber)",
        "sidebar_title": "🛡️ SolidRules v0.4 (Local)",
        "instruction_header": "**Instructions:**",
        "instr_1": "1. Upload PDF.",
        "instr_2": "2. Describe problem.",
        "instr_3": "3. Click Generate.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Your problem / Question:",
        "placeholder": "E.g. What is the category for PS=45bar and V=150L?",
        "button": "🚀 Analyze & Generate",
        "warning_short": "⚠️ Please describe the problem.",
        "spinner_pdf": "📂 Scanning file locally...",
        "spinner_ai": "🧠 Analyzing data...",
        "report_header": "### 💡 Engineering Report",
        "disclaimer": "⚠️ **Disclaimer:** Verify data with original document.",
        "upload_label": "📂 Upload documentation (PDF)",
        "file_success": "✅ File loaded (Pages: {pages})",
        "system_prompt_base": """You are a Chief Technology Officer.
        RULES:
        1. Answer MAINLY based on the uploaded PDF text.
        2. Try to extract values from tables if present.
        3. Be concrete and technical.
        4. Answer in ENGLISH."""
    }
}

# --- FUNKCJA PARSUJĄCA (PDFPlumber - Lokalna) ---
@st.cache_data(show_spinner=False)
def parse_pdf_local(file_bytes):
    try:
        # PDFPlumber potrafi czytać bajty bezpośrednio, ale dla bezpieczeństwa zapiszemy plik
        import tempfile
        import os
        
        text_content = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name
            
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                # Extract text (good for paragraphs)
                text = page.extract_text() or ""
                # Extract tables (experimental, adds raw table data)
                tables = page.extract_tables()
                
                text_content += f"\n--- Page {page.page_number} ---\n{text}\n"
                
                if tables:
                    text_content += "\n[TABELA ZNALEZIONA NA STRONIE]:\n"
                    for table in tables:
                        for row in table:
                            # Czyścimy None i łączymy wiersze
                            clean_row = [str(cell) if cell is not None else "" for cell in row]
                            text_content += " | ".join(clean_row) + "\n"
        
        os.remove(tmp_path)
        return text_content
        
    except Exception as e:
        return f"Error: {str(e)}"

# --- PASEK BOCZNY ---
with st.sidebar:
    lang = st.radio("Language / Język:", ["PL", "EN"], horizontal=True)
    t = translations[lang]
    st.header(t["sidebar_title"])
    st.markdown("---")
    st.info("Engine: GPT-4o-mini + PDFPlumber")
    st.markdown("---")
    st.caption(t["footer"])

# --- GŁÓWNA STRONA ---
st.title(t["title"])
st.markdown("---")

# 1. WGRYWANIE
uploaded_file = st.file_uploader(t["upload_label"], type=["pdf"])
pdf_text = ""

if uploaded_file is not None:
    with st.spinner(t["spinner_pdf"]):
        bytes_data = uploaded_file.getvalue()
        extracted_text = parse_pdf_local(bytes_data)
        
        if "Error" in extracted_text:
            st.error(extracted_text)
        else:
            pdf_text = extracted_text
            # Liczymy strony "na piechotę" po znacznikach
            page_count = extracted_text.count("--- Page")
            st.success(t["file_success"].format(pages=page_count))
            
            with st.expander("🕵️ DEBUG: Zobacz co widzi AI"):
                st.text(pdf_text[:2000])

# 2. PYTANIE
problem = st.text_area(t["label_problem"], height=100, placeholder=t["placeholder"])
generate_button = st.button(t["button"], type="primary", use_container_width=True)

# 3. GENEROWANIE
if generate_button:
    if not problem:
        st.warning(t["warning_short"])
    else:
        with st.spinner(t["spinner_ai"]):
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            # Skracamy tekst jeśli jest gigantyczny (limit tokenów)
            # GPT-4o-mini ma duże okno (128k), ale bezpieczniej nie przesadzać
            final_context = pdf_text[:100000] 
            
            prompt = t["system_prompt_base"]
            if final_context:
                prompt += f"\n\n--- DOKUMENTACJA (PDF) ---\n{final_context}\n--- KONIEC ---\n"

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": problem}
                ],
                temperature=0.3 # Niski, żeby był precyzyjny
            )
            
            st.markdown(t["report_header"])
            st.markdown(response.choices[0].message.content)
            st.warning(t["disclaimer"])
