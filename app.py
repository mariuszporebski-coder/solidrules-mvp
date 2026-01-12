import streamlit as st
import tempfile
import os
import nest_asyncio
import pdfplumber
import fitz  # To jest PyMuPDF - nasze "oczy"
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

st.set_page_config(page_title="SolidRules AI Vision", page_icon="👁️", layout="wide")

# --- TŁUMACZENIA ---
translations = {
    "PL": {
        "title": "SolidRules: Asystent Inżyniera (Vision AI)",
        "sidebar_title": "👁️ SolidRules v2.0 (Vision)",
        "instruction_header": "**Instrukcja:**",
        "instr_1": "1. Wgraj plik PDF (Tekst, Tabele LUB Wykresy).",
        "instr_2": "2. Opisz problem.",
        "instr_3": "3. Kliknij Generuj.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Twój problem / Pytanie do dokumentacji:",
        "placeholder": "Np. Patrząc na Wykres 1, jaka jest kategoria dla PS=50bar i V=100L?",
        "button": "🚀 Analizuj (Tekst + Obraz)",
        "upload_label": "📂 Wgraj dokumentację (PDF - max kilka stron dla testu)",
        "report_header": "### 💡 Raport Inżynierski (Multimodalny)",
        "disclaimer": "⚠️ **Nota prawna:** Zweryfikuj dane z oryginałem.",
        "status_ok": "✅ Dokument przetworzony! Widzę tekst ({engine}) oraz {img_count} stron jako obrazy.",
        "system_prompt": """J"system_prompt": """Jesteś Głównym Technologiem.
        
        DANE WEJŚCIOWE: Otrzymałeś tekst z dokumentu ORAZ zrzuty ekranu stron (obrazy).
        
        TWOJE ZADANIE: Łączyć te dane.
        
        ZASADA KRYTYCZNA DLA WYKRESÓW/TABEL:
        1. MASZ DOSTĘP do obrazów. Nie mów, że ich nie masz.
        2. Jeśli pytanie dotyczy wykresu, TWOIM OBOWIĄZKIEM jest spojrzeć na załączone obrazy.
        3. Ignoruj uproszczone regułki tekstowe, jeśli wykres pokazuje co innego.
        4. Działaj krok po kroku: Najpierw zidentyfikuj osie na obrazku, potem znajdź wartości, na końcu określ wynik.
        
        Odpowiadaj rzeczowo, inżyniersko, po POLSKU.""""""
    },
    "EN": {
        "title": "SolidRules: Engineering Assistant (Vision AI)",
        "sidebar_title": "👁️ SolidRules v2.0 (Vision)",
        "instruction_header": "**Instructions:**",
        "instr_1": "1. Upload PDF (Text, Tables OR Graphs).",
        "instr_2": "2. Describe problem.",
        "instr_3": "3. Click Generate.",
        "footer": "© 2026 SolidRules Engineering",
        "label_problem": "Your problem / Question:",
        "placeholder": "E.g. Looking at Graph 1, what is the category for PS=50bar and V=100L?",
        "button": "🚀 Analyze (Text + Vision)",
        "upload_label": "📂 Upload documentation (PDF - keep it short for testing)",
        "report_header": "### 💡 Engineering Report (Multimodal)",
        "disclaimer": "⚠️ **Disclaimer:** Verify data with original document.",
        "status_ok": "✅ Document processed! I see text ({engine}) and {img_count} pages as images.",
        "system_prompt": """You are a Chief Technology Officer. You have access to two data sources:
        1. TEXT: Extracted from the document (might be inaccurate for graphs).
        2. IMAGES: Original screenshots of each page.

        RULES:
        1. If the question relates to a GRAPH, SCHEMATIC, or complex TABLE, prioritize ANALYZING THE IMAGES. Look at lines, axes, and legends.
        2. Use text as support.
        3. Be engineering-focused.
        4. Answer in ENGLISH."""
    }
}

# --- NOWOŚĆ: FUNKCJA ZAMIENIAJĄCA PDF NA OBRAZY (BASE64) ---
def pdf_to_images_base64(file_bytes):
    images_base64 = []
    try:
        # Otwieramy PDF z bajtów w pamięci
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Renderujemy stronę do obrazka (pixmap) - zoom=2 dla lepszej jakości
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            # Kodujemy do base64 (tak wymaga OpenAI)
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            images_base64.append(img_b64)
    except Exception as e:
        st.error(f"Błąd przetwarzania obrazów: {e}")
    return images_base64

# --- HYBRYDOWY PARSER TEKSTU (To już znamy) ---
def parse_hybrid(file_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name
    
    text_content = ""
    engine_used = "PDFPlumber (Backup)"

    # Próba 1: LlamaParse
    if LLAMA_CLOUD_API_KEY:
        try:
            parser = LlamaParse(api_key=LLAMA_CLOUD_API_KEY, result_type="markdown", premium_mode=True, language="pl")
            documents = parser.load_data(tmp_path)
            if documents:
                text_content = "\n\n".join([doc.text for doc in documents])
                engine_used = "LlamaParse (PRO)"
        except: pass

    # Próba 2: PDFPlumber (jeśli Llama zawiodła)
    if not text_content or len(text_content) < 50:
        try:
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text_content += (page.extract_text() or "") + "\n"
            engine_used = "PDFPlumber (Backup)"
        except: pass
        
    os.remove(tmp_path)
    return text_content, engine_used

# --- UI ---
with st.sidebar:
    lang = st.radio("Language / Język:", ["PL", "EN"], horizontal=True)
    t = translations[lang]
    st.header(t["sidebar_title"])
    st.markdown("---")
    st.info("Engine: GPT-4o (Vision + Text)")
    st.caption(t["footer"])

st.title(t["title"])

# 1. WGRYWANIE I PRZETWARZANIE (TEKST + OBRAZ)
uploaded_file = st.file_uploader(t["upload_label"], type=["pdf"])
pdf_text_context = ""
pdf_images_list = []
engine_name = ""

if uploaded_file is not None:
    with st.spinner("👁️‍🗨️ Mielę dokument: Czytam tekst ORAZ robię zdjęcia stron..."):
        file_bytes = uploaded_file.getvalue()
        
        # A) Wyciągamy tekst
        pdf_text_context, engine_name = parse_hybrid(file_bytes)
        
        # B) Robimy zdjęcia stron
        pdf_images_list = pdf_to_images_base64(file_bytes)
        
        if pdf_text_context and pdf_images_list:
            st.success(t["status_ok"].format(engine=engine_name, img_count=len(pdf_images_list)))
            with st.expander("🕵️ DEBUG: Zobacz co widzi AI (Tekst + Miniatury)"):
                st.write(f"Silnik tekstu: {engine_name}")
                st.write(f"Liczba stron (obrazów): {len(pdf_images_list)}")
                # Pokazujemy pierwszą stronę jako przykład
                if pdf_images_list:
                     st.image(base64.b64decode(pdf_images_list[0]), caption="Podgląd strony 1 (To widzi GPT-4o)", use_column_width=True)

# 2. GENEROWANIE (VISION API)
problem = st.text_area(t["label_problem"], height=100, placeholder=t["placeholder"])
generate_button = st.button(t["button"], type="primary", use_container_width=True)

if generate_button and problem and pdf_images_list:
    with st.spinner("🧠 Uruchamiam Vision AI... Patrzę na wykresy i czytam tekst..."):
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # --- BUDOWANIE WIADOMOŚCI MULTIMODALNEJ ---
        # 1. Instrukcja systemowa
        messages = [{"role": "system", "content": t["system_prompt"]}]
        
        # 2. Zawartość użytkownika (Tekst + Obrazy)
        user_content = []
        # Dodajemy pytanie użytkownika
        user_content.append({"type": "text", "text": f"PYTANIE UŻYTKOWNIKA: {problem}\n\n"})
        # Dodajemy wyciągnięty tekst (jako kontekst pomocniczy)
        if pdf_text_context:
             user_content.append({"type": "text", "text": f"--- KONTEKST TEKSTOWY (TŁO) ---\n{pdf_text_context[:50000]}\n--- KONIEC TEKSTU ---\n\n"})
        
        # Dodajemy OBRAZY (To jest klucz do Vision!)
        # UWAGA: Dla testu dodajemy max 5 pierwszych stron, żeby nie spalić tokenów.
        for i, img_b64 in enumerate(pdf_images_list[:5]): 
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                    "detail": "high" # Wysoka rozdzielczość do czytania wykresów
                }
            })
            if i == 4: break # Limit 5 stron

        messages.append({"role": "user", "content": user_content})

        # 3. Wysłanie do OpenAI
        response = client.chat.completions.create(
            model="gpt-4o", # Musi być model obsługujący Vision (gpt-4o lub gpt-4o-mini)
            messages=messages,
            max_tokens=1000,
            temperature=0.3
        )
        st.markdown(t["report_header"])
        st.markdown(response.choices[0].message.content)
        st.warning(t["disclaimer"])
elif generate_button and not pdf_images_list:
     st.warning("Najpierw wgraj plik PDF, aby AI miało na co patrzeć.")
