import streamlit as st
from openai import OpenAI

# --- KONFIGURACJA ---
# Pobieranie klucza z sekretów chmury
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("Brak klucza API! Ustaw go w Streamlit Cloud Secrets.")
    st.stop()

# Konfiguracja strony
st.set_page_config(
    page_title="SolidRules AI",
    page_icon="🛡️",
    layout="wide"
)

# --- PASEK BOCZNY (SIDEBAR) ---
with st.sidebar:
    st.header("🛡️ SolidRules v0.1")
    st.markdown("---")
    st.markdown("**Instrukcja:**")
    st.markdown("1. Opisz problem techniczny.")
    st.markdown("2. Określ ograniczenia (np. brak oleju).")
    st.markdown("3. Kliknij Generuj.")
    st.markdown("---")
    
    # Opcja dla Ciebie: Wybór "Trybu" (na przyszłość)
    mode = st.radio("Tryb pracy:", ["Kreatywny (TRIZ)", "Zgodność z Normą (Wkrótce)"])
    
    st.info("System używa modelu GPT-4o-mini.")
    st.markdown("---")
    st.caption("© 2026 SolidRules Engineering")

# --- GŁÓWNA STRONA ---
col1, col2 = st.columns([1, 5])
with col1:
    # Tu możesz wstawić emoji lub link do logo, jeśli masz URL
    st.markdown("# 🛡️") 
with col2:
    st.title("SolidRules: Inżynierski Asystent TRIZ")

st.markdown("---")

# Pole tekstowe
problem = st.text_area(
    "Opisz problem inżynierski lub sprzeczność technologiczną:",
    height=150,
    placeholder="Np. Muszę zwiększyć sztywność blachy, ale nie mogę zwiększyć jej masy. Spawanie ciągłe powoduje deformacje."
)

generate_button = st.button("🚀 Generuj Rozwiązania", type="primary", use_container_width=True)

# Funkcja (ta sama co wcześniej)
def generate_triz_solutions(problem_text):
    if not problem_text or len(problem_text.strip()) < 5:
        return None
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        system_prompt = """Jesteś Głównym Technologiem w zakładzie przemysłu ciężkiego (Heavy Industry). 
        Twoim celem jest rozwiązywanie problemów produkcyjnych przy użyciu metodyki TRIZ.

        ZASADY:
        1. Bądź PRAGMATYCZNY. Unikaj rozwiązań sci-fi.
        2. Skup się na procesie technologicznym (spawanie, obróbka, montaż, materiałoznawstwo).
        3. STRUKTURA ODPOWIEDZI:
           - Podaj 3 konkretne koncepcje.
           - Dla każdej podaj: Numer Zasady TRIZ + Opis Techniczny + Ryzyka.
        4. Używaj języka technicznego, zrozumiałego dla inżyniera."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Problem: {problem_text}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"BŁĄD: {str(e)}"

# Logika wyświetlania
if generate_button:
    if not problem or len(problem.strip()) < 5:
        st.warning("⚠️ Opisz problem dokładniej.")
    else:
        with st.spinner("⚙️ Analizuję parametry i dobieram zasady TRIZ..."):
            response = generate_triz_solutions(problem)
        
        if response:
            st.markdown("### 💡 Raport Rozwiązań")
            st.markdown(response)
            
            # Disclaimer prawny (Ważne w B2B!)
            st.warning("⚠️ **Nota prawna:** To narzędzie wspomagające (AI). Każde rozwiązanie musi zostać zweryfikowane obliczeniowo przez uprawnionego inżyniera przed wdrożeniem.")
