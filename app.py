import streamlit as st
from openai import OpenAI

# --- KONFIGURACJA ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("Brak klucza API! Ustaw go w Streamlit Cloud Secrets.")
    st.stop()

st.set_page_config(
    page_title="SolidRules AI",
    page_icon="🛡️",
    layout="wide"
)

# --- SŁOWNIK TŁUMACZEŃ ---
# To jest "baza danych" tekstów. Tutaj zmieniasz napisy.
translations = {
    "PL": {
        "title": "SolidRules: Inżynierski Asystent TRIZ",
        "sidebar_title": "🛡️ SolidRules v0.2",
        "instruction_header": "**Instrukcja:**",
        "instr_1": "1. Wybierz język.",
        "instr_2": "2. Opisz problem techniczny.",
        "instr_3": "3. Kliknij Generuj.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Opisz problem inżynierski lub sprzeczność technologiczną:",
        "placeholder": "Np. Muszę zwiększyć sztywność blachy, ale nie mogę zwiększyć jej masy...",
        "button": "🚀 Generuj Rozwiązania",
        "warning_short": "⚠️ Opisz problem dokładniej (min. 5 znaków).",
        "spinner": "⚙️ Analizuję parametry i dobieram zasady TRIZ...",
        "report_header": "### 💡 Raport Rozwiązań",
        "disclaimer": "⚠️ **Nota prawna:** To narzędzie wspomagające (AI). Każde rozwiązanie musi zostać zweryfikowane inżyniersko.",
        "system_prompt": """Jesteś Głównym Technologiem w zakładzie przemysłu ciężkiego.
        ZASADY:
        1. Bądź PRAGMATYCZNY. Unikaj rozwiązań sci-fi.
        2. Skup się na inżynierii mechanicznej i procesowej.
        3. STRUKTURA: Podaj 3 konkretne koncepcje TRIZ. Dla każdej: Zasada + Opis Techniczny + Ryzyka.
        4. Odpowiadaj w języku POLSKIM."""
    },
    "EN": {
        "title": "SolidRules: Engineering TRIZ Assistant",
        "sidebar_title": "🛡️ SolidRules v0.2",
        "instruction_header": "**Instructions:**",
        "instr_1": "1. Select language.",
        "instr_2": "2. Describe the technical problem.",
        "instr_3": "3. Click Generate.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Describe the engineering problem or technical contradiction:",
        "placeholder": "E.g. I need to increase sheet stiffness without adding mass...",
        "button": "🚀 Generate Solutions",
        "warning_short": "⚠️ Please describe the problem in more detail.",
        "spinner": "⚙️ Analyzing parameters and applying TRIZ principles...",
        "report_header": "### 💡 Solution Report",
        "disclaimer": "⚠️ **Disclaimer:** This is an AI assistive tool. Every solution must be verified by a certified engineer.",
        "system_prompt": """You are a Chief Technology Officer in Heavy Industry.
        RULES:
        1. Be PRAGMATIC. Avoid sci-fi solutions.
        2. Focus on mechanical engineering and manufacturing processes.
        3. STRUCTURE: Provide 3 concrete TRIZ concepts. For each: Principle + Technical Description + Risks.
        4. Answer in ENGLISH."""
    }
}

# --- PASEK BOCZNY (SIDEBAR) ---
with st.sidebar:
    # Wybór języka
    lang = st.radio("Language / Język:", ["PL", "EN"], horizontal=True)
    t = translations[lang] # Pobierz odpowiedni zestaw tekstów
    
    st.header(t["sidebar_title"])
    st.markdown("---")
    st.markdown(t["instruction_header"])
    st.markdown(t["instr_1"])
    st.markdown(t["instr_2"])
    st.markdown(t["instr_3"])
    st.markdown("---")
    st.info("Engine: GPT-4o-mini")
    st.markdown("---")
    st.caption(t["footer"])

# --- GŁÓWNA STRONA ---
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("# 🛡️") 
with col2:
    st.title(t["title"])

st.markdown("---")

# Pole tekstowe (zmienia język dynamicznie)
problem = st.text_area(
    t["label_problem"],
    height=150,
    placeholder=t["placeholder"]
)

generate_button = st.button(t["button"], type="primary", use_container_width=True)

# Funkcja generująca
def generate_triz_solutions(problem_text, language_code):
    if not problem_text or len(problem_text.strip()) < 5:
        return None
    
    # Wybór odpowiedniego promptu systemowego (PL lub EN)
    current_prompt = translations[language_code]["system_prompt"]
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": current_prompt},
                {"role": "user", "content": f"Problem: {problem_text}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error: {str(e)}"

# Logika działania
if generate_button:
    if not problem or len(problem.strip()) < 5:
        st.warning(t["warning_short"])
    else:
        with st.spinner(t["spinner"]):
            # Przekazujemy wybrany język do funkcji!
            response = generate_triz_solutions(problem, lang)
        
        if response:
            st.markdown(t["report_header"])
            st.markdown(response)
            st.warning(t["disclaimer"])
