import streamlit as st
import tempfile
import os
import nest_asyncio
from openai import OpenAI
from llama_parse import LlamaParse

# Wymagane dla działania LlamaParse w środowisku Streamlit
nest_asyncio.apply()

# --- KONFIGURACJA KLUCZY ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    LLAMA_CLOUD_API_KEY = st.secrets["LLAMA_CLOUD_API_KEY"]
except:
    st.error("Brak kluczy API! Ustaw OPENAI_API_KEY oraz LLAMA_CLOUD_API_KEY w Streamlit Secrets.")
    st.stop()

st.set_page_config(
    page_title="SolidRules AI",
    page_icon="🛡️",
    layout="wide"
)

# --- SŁOWNIK TŁUMACZEŃ ---
translations = {
    "PL": {
        "title": "SolidRules: Asystent Inżyniera + Analiza PDF",
        "sidebar_title": "🛡️ SolidRules v0.3 (RAG)",
        "instruction_header": "**Instrukcja:**",
        "instr_1": "1. (Opcja) Wgraj plik PDF (Norma/DTR).",
        "instr_2": "2. Opisz problem.",
        "instr_3": "3. Kliknij Generuj.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Twój problem / Pytanie do dokumentacji:",
        "placeholder": "Np. Jaka jest tolerancja dla wałka fi 50 wg wgranej tabeli? albo: Jak to naprawić używając TRIZ?",
        "button": "🚀 Analizuj i Generuj",
        "warning_short": "⚠️ Opisz problem dokładniej.",
        "spinner_pdf": "📂 Skanuję dokumentację (LlamaParse)... to może chwilę potrwać...",
        "spinner_ai": "🧠 Analizuję dane i szukam rozwiązania...",
        "report_header": "### 💡 Raport Inżynierski",
        "disclaimer": "⚠️ **Nota prawna:** AI może popełniać błędy. Zweryfikuj dane z oryginałem dokumentu.",
        "upload_label": "📂 Wgraj dokumentację (PDF, max 10MB)",
        "file_success": "✅ Plik wczytany poprawnie!",
        "system_prompt_base": """Jesteś Głównym Technologiem. 
        ZASADY:
        1. Jeśli użytkownik wgrał plik PDF, twoim PRIORYTETEM jest odpowiedź na podstawie tego pliku.
        2. Cytuj konkretne wartości z tabel (jeśli są).
        3. Jeśli pytania są ogólne, używaj metodyki TRIZ.
        4. Bądź konkretny i techniczny.
        5. Odpowiadaj w języku POLSKIM."""
    },
    "EN": {
        "title": "SolidRules: Engineering Assistant + PDF Analysis",
        "sidebar_title": "🛡️ SolidRules v0.3 (RAG)",
        "instruction_header": "**Instructions:**",
        "instr_1": "1. (Optional) Upload PDF (Standard/Manual).",
        "instr_2": "2. Describe the problem.",
        "instr_3": "3. Click Generate.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Your problem / Question about the document:",
        "placeholder": "E.g. What is the tolerance for 50mm shaft according to the table? or: How to fix this using TRIZ?",
        "button": "🚀 Analyze & Generate",
        "warning_short": "⚠️ Please describe the problem.",
        "spinner_pdf": "📂 Scanning document (LlamaParse)... please wait...",
        "spinner_ai": "🧠 Analyzing data and generating solution...",
        "report_header": "### 💡 Engineering Report",
        "disclaimer": "⚠️ **Disclaimer:** AI can make mistakes. Verify data with the original document.",
        "upload_label": "📂 Upload documentation (PDF, max 10MB)",
        "file_success": "✅ File loaded successfully!",
        "system_prompt_base": """You are a Chief Technology Officer.
        RULES:
        1. If the user uploaded a PDF, your PRIORITY is to answer based on that file.
        2. Cite specific values from tables (if present).
        3. If questions are general, use TRIZ methodology.
        4. Be concrete and technical.
        5. Answer in ENGLISH."""
    }
}

# --- FUNKCJA PARSUJĄCA PDF (LlamaParse - Wersja Wzmocniona) ---
@st.cache_data(show_spinner=False)
def parse_pdf_with_llama(file_bytes, file_name):
    try:
        # Tworzymy plik tymczasowy
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        # Inicjalizacja parsera z wymuszonym trybem GPT-4o (lepszy OCR)
        parser = LlamaParse(
            api_key=LLAMA_CLOUD_API_KEY,
            result_type="markdown",
            premium_mode=True,  # Wymusza lepszy OCR (darmowe w limicie 1000 stron)
            language="pl",      # Podpowiedź dla OCR, że to polski tekst
            verbose=True
        )

        # Parsowanie
        documents = parser.load_data(tmp_path)
        
        # Sprzątanie
        os.remove(tmp_path)
        
        # Weryfikacja czy coś wróciło
        if not documents:
            return "Error: LlamaParse zwróciła pustą listę. Sprawdź czy plik nie jest uszkodzony lub czy klucz API jest poprawny."
            
        full_text = "\n\n".join([doc.text for doc in documents])
        
        if len(full_text) < 10:
            return "Error: Odczytano mniej niż 10 znaków. Prawdopodobnie skan jest nieczytelny."
            
        return full_text
    
    except Exception as e:
        return f"Error parsing PDF: {str(e)}"

# --- PASEK BOCZNY ---
with st.sidebar:
    lang = st.radio("Language / Język:", ["PL", "EN"], horizontal=True)
    t = translations[lang]
    
    st.header(t["sidebar_title"])
    st.markdown("---")
    st.markdown(t["instruction_header"])
    st.markdown(t["instr_1"])
    st.markdown(t["instr_2"])
    st.markdown(t["instr_3"])
    st.markdown("---")
    st.info("Engine: GPT-4o-mini + LlamaParse")
    st.markdown("---")
    st.caption(t["footer"])

# --- GŁÓWNA STRONA ---
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("# 🛡️") 
with col2:
    st.title(t["title"])

st.markdown("---")

# 1. SEKCYJA WGRYWANIA PLIKU
uploaded_file = st.file_uploader(t["upload_label"], type=["pdf"])
pdf_content = ""

# ... (wcześniejszy kod funkcji parse) ...

if uploaded_file is not None:
    with st.spinner(t["spinner_pdf"]):
        bytes_data = uploaded_file.getvalue()
        parsed_text = parse_pdf_with_llama(bytes_data, uploaded_file.name)
        
        if "Error" in parsed_text:
            st.error(parsed_text)
        else:
            pdf_content = parsed_text
            st.success(t["file_success"])
            
            # --- NOWOŚĆ: DEBUGGER ---
            with st.expander("🕵️ DEBUG: Zobacz co widzi AI (Kliknij tutaj)"):
                st.info(f"Pobrano znaków: {len(pdf_content)}")
                if len(pdf_content) < 100:
                    st.error("⚠️ UWAGA: Tekst jest podejrzanie krótki! LlamaParse mogła nie zadziałać.")
                st.markdown("**Początek dokumentu:**")
                st.text(pdf_content[:2000]) # Pokaż pierwsze 2000 znaków
            # ------------------------

# 2. POLE TEKSTOWE
st.markdown("---")
problem = st.text_area(t["label_problem"], height=100, placeholder=t["placeholder"])
generate_button = st.button(t["button"], type="primary", use_container_width=True)

# 3. LOGIKA AI
if generate_button:
    if not problem or len(problem.strip()) < 3:
        st.warning(t["warning_short"])
    else:
        with st.spinner(t["spinner_ai"]):
            try:
                client = OpenAI(api_key=OPENAI_API_KEY)
                
                # Budujemy kontekst
                system_instruction = t["system_prompt_base"]
                
                # Jeśli jest PDF, doklejamy go do wiadomości systemowej
                if pdf_content:
                    system_instruction += f"\n\n--- ZAWARTOŚĆ WGRANEGO DOKUMENTU PDF ---\n{pdf_content}\n--- KONIEC DOKUMENTU ---\n\nOdpowiadaj WYŁĄCZNIE na podstawie powyższego dokumentu, jeśli zawiera odpowiedź."

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": problem}
                    ],
                    temperature=0.5 # Mniejsza temperatura = bardziej precyzyjne czytanie tabel
                )
                
                answer = response.choices[0].message.content
                
                st.markdown(t["report_header"])
                st.markdown(answer)
                st.warning(t["disclaimer"])
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
