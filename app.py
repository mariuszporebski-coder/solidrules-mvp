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
import json
import random
from datetime import datetime
from openai import OpenAI
from llama_parse import LlamaParse

# --- NAPRAWA ASYNCIO ---
nest_asyncio.apply()

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SolidRules Ecosystem", page_icon="💠", layout="wide")

# --- CSS (PRO DESIGN) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        header {visibility: hidden;}
        .stApp { background-color: #050505; }
        
        section[data-testid="stSidebar"] { background-color: #0c0c0c; border-right: 1px solid #1e1e1e; }
        
        /* Stylizacja Kart Agentów (Wariant 1C) */
        .agent-card {
            background-color: #111;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
        }
        .agent-active { border-color: #10b981; box-shadow: 0 0 10px rgba(16, 185, 129, 0.2); }
        .agent-warning { border-color: #f59e0b; }
        
        /* UI Elements */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {
            background-color: #111111 !important; color: #e2e8f0 !important;
            border: 1px solid #333 !important; border-radius: 8px !important;
        }
        div.stButton > button {
            background-color: #1e1e2e; color: white; border: 1px solid #333;
            border-radius: 8px; transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #6366f1; border-color: #6366f1;
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(to right, #4f46e5, #6366f1); border: none;
        }
        
        h1, h2, h3 { color: #f8fafc !important; }
        p, li, label, .stMarkdown, .stCaption { color: #94a3b8 !important; }
        .stSuccess { background-color: #064e3b !important; color: #a7f3d0 !important; }
        .stInfo { background-color: #172554 !important; color: #bfdbfe !important; }
        .stWarning { background-color: #451a03 !important; color: #fdba74 !important; }
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
    st.markdown("### 🔒 SolidRules Access")
    st.text_input("Access Code:", type="password", on_change=password_entered, key="password")
    return False

if not check_password(): st.stop()

# --- FUNKCJE MOCKUP ---
def mock_agent_thinking(text):
    with st.status(text, expanded=True) as status:
        time.sleep(1)
        st.write("🔍 Skanowanie załączników...")
        time.sleep(0.5)
        st.write("🧠 Ekstrakcja danych (Vision AI)...")
        time.sleep(0.5)
        st.write("💰 Sprawdzanie cen stali (API Albeco)...")
        time.sleep(0.5)
        status.update(label="Gotowe!", state="complete", expanded=False)

# ==========================================
# 🎛️ WYBÓR STRATEGII
# ==========================================
with st.sidebar:
    st.markdown("### 🏗️ Strategia Produktu")
    variant = st.selectbox(
        "Wybierz Koncepcję:",
        [
            "WARIANT 1C: AUTONOMY (Turbo Pivot)",
            "WARIANT 1B: EngOps AI (Proces)",
            "WARIANT 1A: Rodzina Aplikacji (Narzędzia)"
        ],
        index=0
    )
    st.markdown("---")
    
    if variant == "WARIANT 1C: AUTONOMY (Turbo Pivot)":
        st.markdown("**Status Agentów:**")
        st.success("🟢 Email Watcher: Active")
        st.success("🟢 Supply Radar: Active")
        st.warning("🟠 Design Critic: Learning")

# ==============================================================================
# WARIANT 1C: SOLIDRULES AUTONOMY (Agentic AI)
# ==============================================================================
if variant == "WARIANT 1C: AUTONOMY (Turbo Pivot)":
    
    st.markdown("# 🤖 SolidRules AUTONOMY")
    st.caption("Human-in-the-loop Engineering | AI wykonuje pracę, Ty zatwierdzasz.")
    
    # PULPIT STEROWNICZY (INBOX)
    st.markdown("### 📥 Skrzynka Odbiorcza Agentów (Action Required)")
    
    col_inbox, col_preview = st.columns([1, 1.5])
    
    with col_inbox:
        # Lista Zadań (To wygląda jak klient poczty, ale dla AI)
        with st.container(border=True):
            st.markdown("**Nowe Zgłoszenia (3)**")
            
            # Zadanie 1
            if st.button("🔴 PILNE: Oferta dla TechCorp (50 szt. Wałek)", key="task1", use_container_width=True):
                st.session_state['active_task'] = 1
            
            # Zadanie 2
            if st.button("🟠 WERYFIKACJA: Rysunek błędny (Brak tolerancji)", key="task2", use_container_width=True):
                st.session_state['active_task'] = 2
                
            # Zadanie 3
            if st.button("🟢 GOTOWE: Faktura od Dostawcy Stali", key="task3", use_container_width=True):
                st.session_state['active_task'] = 3

    with col_preview:
        active_task = st.session_state.get('active_task', 1)
        
        # SCENARIUSZ 1: AI ZROBIŁO WYCENĘ SAMO
        if active_task == 1:
            st.markdown("#### 🤖 Agent: Sales_Bot_v4")
            st.info("Odebrałem maila od `jan.kowalski@techcorp.pl`. Przeanalizowałem PDF. Sprawdziłem magazyn. Przygotowałem draft oferty.")
            
            with st.expander("📄 Podgląd PDF od klienta", expanded=False):
                st.write("[Rysunek_Walek_Fi50.pdf]")
            
            st.markdown("**--- DRAFT ODPOWIEDZI ---**")
            email_draft = st.text_area("Treść maila do wysłania:", 
                                       value="Dzień dobry Panie Janie,\nDziękujemy za zapytanie. Wyceniliśmy detal 'Wałek Fi50' wg rysunku 2024-B.\n\nCena: 45,00 PLN netto/szt.\nTermin: 7 dni roboczych (Materiał dostępny od ręki).\n\nPozdrawiam,\nSolidRules AI",
                                       height=150)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Marża", "32%", "Bezpieczna")
            with c2: st.metric("Ryzyko", "Niskie")
            with c3: 
                if st.button("✅ Wyślij Ofertę", type="primary"):
                    st.toast("Oferta wysłana do klienta!")
                    st.balloons()
            
        # SCENARIUSZ 2: AI ZNALAZŁO BŁĄD I PYTA CZŁOWIEKA
        elif active_task == 2:
            st.markdown("#### 🤖 Agent: Quality_Guardian")
            st.error("STOP! Znalazłem problem krytyczny w dokumentacji od `BuildPol`.")
            
            st.markdown("""
            **Zdiagnozowany problem:**
            Na rysunku `Rama_Spawana.pdf` w widoku B brakuje tolerancji dla otworu pasowanego pod łożysko.
            Norma ISO 2768-mK nie precyzuje tego wymiaru.
            """)
            
            st.markdown("**Sugerowana Akcja:**")
            action = st.radio("Co mam zrobić?", ["Odesłać maila z prośbą o poprawkę", "Przyjąć H7 (Ryzykowne)", "Przekazać do Technologa"])
            
            if st.button("Wykonaj Akcję"):
                st.success(f"Agent wykonuje: {action}")

        elif active_task == 3:
            st.success("Faktura zarchiwizowana. Ceny stali zaktualizowane w systemie Estimator.")

    st.markdown("---")
    
    # WIZUALIZACJA PROCESU W TLE
    st.markdown("### 🧠 Co dzieje się w tle? (Live Log)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**📨 Email Watcher**")
        st.code("11:42: Otrzymano PDF.\n11:42: OCR Start.\n11:43: Klasyfikacja: ZAPYTANIE.", language="bash")
    with c2:
        st.markdown("**🕸️ Supply Radar**")
        st.code("11:40: Ping Albeco API...\n11:40: Stal 1.4301 +2% (vs wczoraj).\n11:41: Aktualizacja cennika.", language="bash")
    with c3:
        st.markdown("**🛡️ Norm Watchdog**")
        st.code("11:00: Skan ISO.org...\n11:00: Brak zmian krytycznych.\n11:05: System bezpieczny.", language="bash")


# ==============================================================================
# WARIANT 1B: ENGINEERING OPS AI (Poprzedni)
# ==============================================================================
elif variant == "WARIANT 1B: EngOps AI (Proces)":
    st.markdown("# 🏗️ Engineering Ops AI")
    st.caption("Procesowe podejście do danych.")
    tab1, tab2, tab3 = st.tabs(["DRAWING → DATA", "QUOTE → ORDER", "KNOWLEDGE CORE"])
    
    with tab1:
        st.info("Tutaj jest ten 'lepszy Excel' do digitalizacji.")
        st.file_uploader("Wgraj PDF")
        st.json({"part": "Shaft", "qty": 10})
        
    with tab2:
        st.info("Kalkulator ofert.")
        st.metric("Cena", "100 PLN")

# ==============================================================================
# WARIANT 1A: RODZINA APLIKACJI (Stary)
# ==============================================================================
elif variant == "WARIANT 1A: Rodzina Aplikacji (Narzędzia)":
    st.markdown("# 💠 Rodzina Aplikacji")
    st.caption("Zestaw narzędzi dla inżynierów.")
    st.radio("Wybierz moduł:", ["Innovate", "Metrology", "Field"], horizontal=True)
    st.info("To jest Twoja pierwotna koncepcja (Toolbox).")
