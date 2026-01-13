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
        
        /* Stylizacja 1D: Confidence Scores */
        .score-green { color: #10b981; font-weight: bold; }
        .score-yellow { color: #f59e0b; font-weight: bold; }
        .score-red { color: #ef4444; font-weight: bold; }
        
        .review-card {
            background-color: #111;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }
        
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
        .stError { background-color: #450a0a !important; color: #fecaca !important; }
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
def render_confidence(score):
    if score >= 90:
        return f'<span class="score-green">● High ({score}%)</span>'
    elif score >= 70:
        return f'<span class="score-yellow">● Medium ({score}%)</span>'
    else:
        return f'<span class="score-red">● Low ({score}%)</span>'

# ==========================================
# 🎛️ WYBÓR STRATEGII
# ==========================================
with st.sidebar:
    st.markdown("### 🏗️ Strategia Produktu")
    variant = st.selectbox(
        "Wybierz Koncepcję:",
        [
            "WARIANT 1D: FLOW (Controlled Autonomy)",
            "WARIANT 1C: AUTONOMY (Turbo Pivot)",
            "WARIANT 1B: EngOps AI (Proces)",
            "WARIANT 1A: Rodzina Aplikacji (Narzędzia)"
        ],
        index=0
    )
    st.markdown("---")
    
    if "1D" in variant:
        st.markdown("**📊 Risk Monitor:**")
        st.metric("Oczekujące Projekty", "3")
        st.metric("Wymaga Twojej uwagi", "1", delta="Low Confidence", delta_color="inverse")

# ==============================================================================
# WARIANT 1D: SOLIDRULES FLOW (Controlled Autonomy)
# ==============================================================================
if variant == "WARIANT 1D: FLOW (Controlled Autonomy)":
    
    st.markdown("# 🏗️ SolidRules FLOW")
    st.caption("AI pracuje (80%), Ty decydujesz (20%) | Human-in-the-loop Feature.")
    
    # 1. INTAKE (EMAIL TO WORKSPACE)
    st.markdown("### 📥 Projekty Robocze (Drafts)")
    
    col_list, col_work = st.columns([1, 2])
    
    with col_list:
        st.markdown("**Ostatnie Zgłoszenia (Email/Upload):**")
        with st.container(border=True):
            if st.button("📄 TechCorp: Wałek Fi50 (Email)", use_container_width=True):
                st.session_state['flow_task'] = 'techcorp'
            st.caption("Status: 🟢 AI pewne (95%)")
            
            st.markdown("---")
            
            if st.button("📄 AgroMech: Rama Spawana (Email)", use_container_width=True):
                st.session_state['flow_task'] = 'agromech'
            st.caption("Status: 🔴 AI niepewne (45%) - Wymaga Korekty")
            
    # 2. WORKBENCH (HUMAN CONTROL PANEL)
    with col_work:
        task = st.session_state.get('flow_task', None)
        
        if task == 'techcorp':
            st.info("✅ Ten projekt wygląda dobrze. AI ma wysoką pewność.")
            st.markdown("#### Podgląd Wyceny Automatycznej")
            df = pd.DataFrame({
                "Część": ["Wałek Fi50 L200", "Podkładka"],
                "Materiał": ["S355", "Mosiądz"],
                "Cena/szt": ["45.00 PLN", "2.50 PLN"],
                "Pewność AI": ["98%", "99%"]
            })
            st.dataframe(df, use_container_width=True)
            if st.button("Zatwierdź i Wyślij Ofertę", type="primary"):
                st.success("Wysłano!")
        
        elif task == 'agromech':
            st.warning("⚠️ AI zgłasza wyjątki. Sprawdź czerwone pola.")
            
            st.markdown("#### 🔧 Korekta Parametrów")
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1: 
                    st.markdown("**1. Materiał** (Wykryto z rysunku)")
                    st.markdown("AI odczytało: `Stal Nierdzewna 304`")
                with c2:
                    st.markdown(render_confidence(45), unsafe_allow_html=True)
                with c3:
                    # Human Override
                    new_mat = st.selectbox("Korekta człowieka:", ["Zatwierdź (304)", "Zmień na 316L", "Zmień na S235"], index=1)
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1: 
                    st.markdown("**2. Operacje**")
                    st.markdown("AI sugeruje: `Laser + Gięcie`")
                with c2:
                    st.markdown(render_confidence(92), unsafe_allow_html=True)
                with c3:
                    st.write("✅ OK")

            st.markdown("---")
            col_dec1, col_dec2 = st.columns(2)
            with col_dec1:
                st.markdown("**Estymacja:** 12 500 PLN")
            with col_dec2:
                if st.button("Zatwierdź korekty i Generuj PDF"):
                    st.success("Zapisano! System nauczył się, że dla AgroMech używamy 316L.")

    st.markdown("---")
    with st.expander("🧠 Knowledge Loop (Co się dzieje pod spodem?)"):
        st.write("Twoja korekta (zmiana materiału na 316L) została zapisana.")
        st.write("Następnym razem AI dla klienta 'AgroMech' zasugeruje 316L z pewnością 90%.")


# ==============================================================================
# POZOSTAŁE WARIANTY (DLA PORÓWNANIA)
# ==============================================================================
elif variant == "WARIANT 1C: AUTONOMY (Turbo Pivot)":
    st.markdown("# 🤖 SolidRules AUTONOMY")
    st.info("Tu AI robi wszystko samo. Wysokie ryzyko, wysoki zysk. (Dla odważnych)")
    st.button("Włącz Autopilota", disabled=True)

elif variant == "WARIANT 1B: EngOps AI (Proces)":
    st.markdown("# 🏗️ Engineering Ops AI")
    st.info("Procesowe podejście: Upload -> Quote -> Order.")

elif variant == "WARIANT 1A: Rodzina Aplikacji (Narzędzia)":
    st.markdown("# 💠 Rodzina Aplikacji")
    st.info("Zestaw narzędzi (Toolbox) dla inżynierów.")
