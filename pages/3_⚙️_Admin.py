import streamlit as st
import pandas as pd
import math
import time
from datetime import datetime
from fpdf import FPDF
from supabase import create_client
# ... après les imports ...

st.set_page_config(page_title="Bibars Login", page_icon="🔒", layout="centered")

# --- 1. CONNEXION SUPABASE ---
try:
    # REMETS TES CLES ICI
    SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Erreur de configuration Supabase : {e}")
    st.stop()

# --- 2. INITIALISATION SESSION ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None

# --- 3. DESIGN PAGE ---
st.title("🔒 Connexion Bibars")

# --- 4. SI DÉJÀ CONNECTÉ ---
if st.session_state.user:
    st.success(f"✅ Bonjour {st.session_state.user.email} !")
    st.info("Utilisez le menu à gauche pour naviguer.")
    
    if st.session_state.role == "admin":
        st.write("Droit : 👑 ADMINISTRATEUR")
    else:
        st.write("Droit : 👷 OPÉRATEUR")

    if st.button("Se déconnecter"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()

# --- 5. SI PAS CONNECTÉ (FORMULAIRE) ---
else:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
    
    if submit:
        try:
            # Vérification via Supabase Auth
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            if response.user:
                st.session_state.user = response.user
                
                # DÉFINITION DES RÔLES
                if "scan" in email:
                    st.session_state.role = "operateur"
                else:
                    st.session_state.role = "admin"
                
                st.success("Connexion réussie !")
                st.rerun()
                
        except Exception as e:
            st.error("Email ou mot de passe incorrect.")




