import streamlit as st
from openai import OpenAI

# --- KONFIGURACJA ---
# Wklej tutaj swój klucz od OpenAI (zaczyna się od sk-...)
# --- KONFIGURACJA ---
# Teraz klucz pobieramy z bezpiecznych sekretów chmury, a nie z pliku!
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("Brak klucza API! Ustaw go w Streamlit Cloud Secrets.")
    st.stop()
# Konfiguracja strony
st.set_page_config(
    page_title="SolidRules: Asystent Inżyniera (TRIZ)",
    page_icon="🔧",
    layout="wide"
)

# Tytuł aplikacji
st.title("🔧 SolidRules: Asystent Inżyniera (TRIZ)")
st.markdown("---")

# Opis aplikacji
st.markdown("""
### Witaj w asystencie TRIZ!
Wpisz swój problem inżynierski poniżej, a otrzymasz kreatywne rozwiązania oparte o **40 Zasad Wynalazczych TRIZ**.
""")

# Pole tekstowe do wprowadzenia problemu
problem = st.text_area(
    "Opisz swój problem inżynierski:",
    height=150,
    placeholder="Np. Jak zmniejszyć zużycie energii w procesie produkcyjnym? Jak zwiększyć wytrzymałość materiału przy zachowaniu jego lekkości?"
)

# Przycisk do generowania rozwiązań
generate_button = st.button("🚀 Generuj Rozwiązania", type="primary", use_container_width=True)

# Funkcja generująca rozwiązania TRIZ przy użyciu OpenAI
def generate_triz_solutions(problem_text):
    if not problem_text or len(problem_text.strip()) < 10:
        return None
    
    if not OPENAI_API_KEY or "TU_WKLEJ" in OPENAI_API_KEY:
        return "ERROR: Klucz API nie został ustawiony."
    
    try:
        # Konfiguracja Klienta OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # System Prompt - Instrukcja dla Inżyniera
        system_prompt = """Jesteś Głównym Technologiem w zakładzie przemysłu ciężkiego. 
        Twoim celem jest rozwiązywanie problemów produkcyjnych przy użyciu metodyki TRIZ.

        ZASADY:
        1. Bądź PRAGMATYCZNY. Unikaj rozwiązań sci-fi.
        2. Skup się na procesie technologicznym (spawanie, gięcie, montaż, obróbka).
        3. Odpowiedź ma być konkretna: Konkretna Zasada TRIZ + Jak to zastosować w warsztacie.
        4. Formatuj odpowiedź używając Markdown (pogrubienia, listy)."""
        
        # Zapytanie do modelu
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Najlepszy stosunek ceny do jakości
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Problem inżynierski: {problem_text}. Zaproponuj 3 rozwiązania TRIZ."}
            ],
            temperature=0.7 # Kreatywność (0 = robot, 1 = artysta)
        )
        
        # Zwróć tekst odpowiedzi
        return response.choices[0].message.content
        
    except Exception as e:
        return f"BŁĄD: Nie udało się wygenerować odpowiedzi. Szczegóły: {str(e)}"

# Główna logika aplikacji
if generate_button:
    if not problem or len(problem.strip()) < 10:
        st.warning("⚠️ Proszę wpisać problem inżynierski (minimum 10 znaków).")
    else:
        with st.spinner("🔍 Analizuję problem (Silnik: OpenAI GPT-4o-mini)..."):
            response = generate_triz_solutions(problem)
        
        if response:
            st.markdown("---")
            st.subheader("💡 Zaproponowane rozwiązania:")
            st.markdown("")
            
            if response.startswith("ERROR:") or response.startswith("BŁĄD"):
                st.error(response)
            else:
                st.markdown(response)
            
            st.markdown("")
            st.caption("💡 *Powered by OpenAI GPT-4o-mini*")

# Stopka
st.markdown("---")
st.caption("🔧 SolidRules MVP")