import streamlit as st
from supabase import create_client
import time
# ... imports ...

def login_page():
    # SI DÉJÀ CONNECTÉ -> AFFICHER BOUTON DÉCONNEXION
    if st.session_state.user:
        st.title("Profil Utilisateur")
        st.write(f"Connecté en tant que : **{st.session_state.user.email}**")
        if st.button("Se déconnecter", type="primary"):
            st.session_state.user = None
            st.session_state.role = None
            st.rerun()
        return # On arrête là, pas besoin d'afficher le formulaire

    # SI PAS CONNECTÉ -> AFFICHER LE FORMULAIRE
    st.title("🔒 Connexion Bibars")
    # ... (le reste du code formulaire d'avant) ...
# --- TES CLÉS ---
SUPABASE_URL = "TON_URL_SUPABASE_ICI"
SUPABASE_KEY = "TA_CLE_PUBLIQUE_ANON_ICI"

def login_page():
    st.title("🔒 Connexion Bibars")
    st.write("Veuillez vous identifier pour accéder à l'usine.")

    # Connexion DB
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        st.error("Erreur de connexion serveur.")
        st.stop()

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter", type="primary")

    if submit:
        try:
            # Vérification Supabase
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            if response.user:
                # ON ENREGISTRE L'UTILISATEUR DANS LA SESSION
                st.session_state.user = response.user
                
                # Rôles simples
                if "scan" in email:
                    st.session_state.role = "operateur"
                else:
                    st.session_state.role = "admin"
                
                st.success("Connexion réussie !")
                time.sleep(0.5)
                st.rerun() # Recharge la page pour que le "Cerveau" (Home.py) voie le changement
                
        except Exception:
            st.error("Identifiants incorrects.")

# On lance la fonction
login_page()