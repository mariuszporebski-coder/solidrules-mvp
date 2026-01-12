import streamlit as st
import tempfile
import os
import nest_asyncio
from openai import OpenAI
from llama_parse import LlamaParse

# Wymagane dla asynchroniczności w Streamlit
nest_asyncio.apply()

# --- KONFIGURACJA ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    LLAMA_CLOUD_API_KEY = st.secrets["LLAMA_CLOUD_API_KEY"]
except:
    st.error("Brak kluczy API! Sprawdź Secrets w Streamlit Cloud.")
    st.stop()

st.set_page_config(page_title="SolidRules AI", page_icon="🛡️", layout="wide")

# --- TŁUMACZENIA ---
translations = {
    "PL": {
        "title": "SolidRules: Asystent Inżyniera (Silnik: LlamaParse PRO)",
        "sidebar_title": "🛡️ SolidRules v1.0 (RAG)",
        "instruction_header": "**Instrukcja:**",
        "instr_1": "1. Wgraj plik PDF (Norma/DTR).",
        "instr_2": "2. Opisz problem.",
        "instr_3": "3. Kliknij Generuj.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Twój problem / Pytanie do dokumentacji:",
        "placeholder": "Np. Jaka jest kategoria zbiornika dla PS=50bar i V=100L wg Wykresu 1?",
        "button": "🚀 Analizuj i Generuj",
        "warning_short": "⚠️ Opisz problem dokładniej.",
        "spinner_pdf": "👁️ Skanuję dokumentację (LlamaParse - tryb tabelaryczny)...",
        "spinner_ai": "🧠 Analizuję dane i szukam rozwiązania...",
        "report_header": "### 💡 Raport Inżynierski",
        "disclaimer": "⚠️ **Nota prawna:** Zweryfikuj dane z oryginałem. AI to tylko asystent.",
        "upload_label": "📂 Wgraj dokumentację (PDF)",
        "file_success": "✅ Plik przetworzony przez LlamaParse! (Znaków: {chars})",
        "system_prompt_base": """Jesteś Głównym Technologiem. 
        PRIORYTET:
        1. Analizuj wgrany tekst BARDZO DOKŁADNIE.
        2. Zwracaj uwagę na strukturę tabel i wykresów opisanych w tekście.
        3. Jeśli dane wskazują na wysoką kategorię ryzyka (np. PED), informuj o tym.
        4. Bądź konkretny i techniczny.
        5. Odpowiadaj w języku POLSKIM."""
    },
    "EN": {
        "title": "SolidRules: Engineering Assistant (Engine: LlamaParse PRO)",
        "sidebar_title": "🛡️ SolidRules v1.0 (RAG)",
        "instruction_header": "**Instructions:**",
        "instr_1": "1. Upload PDF.",
        "instr_2": "2. Describe problem.",
        "instr_3": "3. Click Generate.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Your problem / Question:",
        "placeholder": "E.g. What is the category for PS=50bar and V=100L?",
        "button": "🚀 Analyze & Generate",
        "warning_short": "⚠️ Please describe the problem.",
        "spinner_pdf": "👁️ Scanning document (LlamaParse)...",
        "spinner_ai": "🧠 Analyzing data...",
        "report_header": "### 💡 Engineering Report",
        "disclaimer": "⚠️ **Disclaimer:** Verify data with original document.",
        "upload_label": "📂 Upload documentation (PDF)",
        "file_success": "✅ LlamaParse Success! (Chars: {chars})",
        "system_prompt_base": """You are a Chief Technology Officer.
        RULES:
        1. Analyze uploaded text VERY CAREFULLY.
        2. Pay attention to tables and graph descriptions.
        3. Be concrete and technical.
        4. Answer in ENGLISH."""
    }
}

# --- FUNKCJA PARSUJĄCA (LlamaParse) ---
@st.cache_data(show_spinner=False)
def parse_pdf_llama(file_bytes, file_name):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        # Konfiguracja parsera - tryb agresywny dla tabel
        parser = LlamaParse(
            api_key=LLAMA_CLOUD_API_KEY,
            result_type="markdown",
            premium_mode=True,  # Wymusza tryb GPT-4o do OCR
            language="pl",
            verbose=True
        )
        
        documents = parser.load_data(tmp_path)
        os.remove(tmp_path)
        
        if not documents:
            return "Error: Pusta odpowiedź z LlamaCloud."
            
        full_text = "\n\n".join([doc.text for doc in documents])
        return full_text
        
    except Exception as e:
        return f"Error LlamaParse: {str(e)}"

# --- UI ---
with st.sidebar:
    lang = st.radio("Language / Język:", ["PL", "EN"], horizontal=True)
    t = translations[lang]
    st.header(t["sidebar_title"])
    st.markdown("---")
    st.info("Engine: GPT-4o-mini + LlamaParse (Vision)")
    st.caption(t["footer"])

st.title(t["title"])
st.markdown("---")

# 1. WGRYWANIE
uploaded_file = st.file_uploader(t["upload_label"], type=["pdf"])
pdf_text = ""

if uploaded_file is not None:
    with st.spinner(t["spinner_pdf"]):
        bytes_data = uploaded_file.getvalue()
        extracted_text = parse_pdf_llama(bytes_data, uploaded_file.name)
        
        if "Error" in extracted_text:
            st.error(extracted_text)
            st.error("💡 Sugestia: Sprawdź klucz API LlamaCloud w Secrets.")
        else:
            pdf_text = extracted_text
            st.success(t["file_success"].format(chars=len(pdf_text)))
            with st.expander("🕵️ DEBUG: Co widzi LlamaParse?"):
                st.markdown(pdf_text[:5000]) # Podgląd Markdown

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
            
            prompt = t["system_prompt_base"]
            if pdf_text:
                prompt += f"\n\n--- DOKUMENTACJA (Markdown z LlamaParse) ---\n{pdf_text}\n--- KONIEC ---\n"

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": problem}
                ],
                temperature=0.3
            )
            
            st.markdown(t["report_header"])
            st.markdown(response.choices[0].message.content)
            st.warning(t["disclaimer"])
