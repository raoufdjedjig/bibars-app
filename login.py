
import streamlit as st
from supabase import create_client
import time
import datetime
import extra_streamlit_components as stx

# --- CONFIGURATION ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"


# --- 1. CONFIGURATION PAGE & COOKIE MANAGER ---
# On initialise le manager tout de suite, sans fonction autour
st.title("🔒 Connexion Bibars")

# On change la clé pour éviter le conflit "Duplicate Key"
cookie_manager = stx.CookieManager(key="bibars_mgr_v2")

# On récupère les cookies
cookies = cookie_manager.get_all()
cookie_email = cookies.get("bibars_email")

# --- 2. CONNEXION DB ---
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("Erreur serveur Supabase.")
    st.stop()

# --- 3. LOGIQUE D'AUTO-CONNEXION (COOKIE) ---
if "user" not in st.session_state or st.session_state.user is None:
    if cookie_email:
        try:
            # On vérifie le rôle
            role_resp = supabase.table('user_roles').select('role').eq('email', cookie_email).execute()
            
            if role_resp.data:
                # Restauration Session
                st.session_state.user = type('obj', (object,), {'email': cookie_email})
                st.session_state.role = role_resp.data[0]['role']
                st.success(f"👋 Re-bonjour {cookie_email} !")
                time.sleep(1) # Petite pause pour la stabilité
                st.rerun()
        except:
            pass 

# --- 4. AFFICHAGE (CONNECTÉ OU NON) ---

# CAS A : DÉJÀ CONNECTÉ
if "user" in st.session_state and st.session_state.user:
    st.write(f"Connecté en tant que : **{st.session_state.user.email}**")
    
    role = st.session_state.get('role', 'Inconnu')
    if role == 'admin':
        st.info("👑 Droits : ADMINISTRATEUR")
    else:
        st.info("👷 Droits : OPÉRATEUR")

    if st.button("Se déconnecter", type="primary"):
        cookie_manager.delete("bibars_email")
        st.session_state.user = None
        st.session_state.role = None
        time.sleep(1)
        st.rerun()

# CAS B : FORMULAIRE DE CONNEXION
else:
    st.write("Veuillez vous identifier pour accéder à l'usine.")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter", type="primary")

    if submit:
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            if response.user:
                st.session_state.user = response.user
                
                try:
                    role_resp = supabase.table('user_roles').select('role').eq('email', email).execute()
                    if role_resp.data:
                        st.session_state.role = role_resp.data[0]['role']
                    else:
                        st.session_state.role = "operateur"
                except:
                    st.session_state.role = "operateur"

                # Création du Cookie
                expires = datetime.datetime.now() + datetime.timedelta(days=30)
                cookie_manager.set("bibars_email", email, expires_at=expires)
                
                st.success("Connexion réussie !")
                time.sleep(1)
                st.rerun()
                
        except Exception:
            st.error("Email ou mot de passe incorrect.")


