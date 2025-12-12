
import streamlit as st
from supabase import create_client
import time
import datetime
import extra_streamlit_components as stx # La librairie Cookie

# --- CONFIGURATION ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"

# --- GESTIONNAIRE DE COOKIES (CACHE) ---
@st.cache_resource
def get_manager():
    return stx.CookieManager()

def login_page():
    st.title("🔒 Connexion Bibars")
    
    # 1. Initialiser le gestionnaire de cookies
    cookie_manager = get_manager()
    
    # On récupère tous les cookies pour voir si 'bibars_email' existe
    cookies = cookie_manager.get_all()
    cookie_email = cookies.get("bibars_email")

    # Connexion DB
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        st.error("Erreur serveur Supabase.")
        st.stop()

    # --- LOGIQUE D'AUTO-CONNEXION VIA COOKIE ---
    # Si on n'est pas connecté dans la session, mais qu'on a un cookie
    if "user" not in st.session_state or st.session_state.user is None:
        if cookie_email:
            # On vérifie que cet email a bien un rôle dans la base (Sécurité)
            try:
                role_resp = supabase.table('user_roles').select('role').eq('email', cookie_email).execute()
                if role_resp.data:
                    # BINGO ! On restaure la session
                    st.session_state.user = type('obj', (object,), {'email': cookie_email}) # On recrée un faux objet user avec l'email
                    st.session_state.role = role_resp.data[0]['role']
                    st.success(f"👋 Re-bonjour {cookie_email} !")
                    time.sleep(1)
                    st.rerun()
            except:
                pass # Si le cookie est invalide, on ne fait rien, le formulaire s'affichera

    # --- CAS 1 : UTILISATEUR CONNECTÉ (SESSION ACTIVE) ---
    if "user" in st.session_state and st.session_state.user:
        st.write(f"Connecté en tant que : **{st.session_state.user.email}**")
        
        role = st.session_state.get('role', 'Inconnu')
        if role == 'admin':
            st.info("👑 Droits : ADMINISTRATEUR")
        else:
            st.info("👷 Droits : OPÉRATEUR")

        if st.button("Se déconnecter", type="primary"):
            # 1. On supprime le cookie du navigateur
            cookie_manager.delete("bibars_email")
            # 2. On vide la session
            st.session_state.user = None
            st.session_state.role = None
            st.rerun()
        return

    # --- CAS 2 : FORMULAIRE DE CONNEXION (SI PAS DE COOKIE) ---
    st.write("Veuillez vous identifier pour accéder à l'usine.")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter", type="primary")

    if submit:
        try:
            # Vérification Supabase Auth
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            if response.user:
                st.session_state.user = response.user
                
                # Récupération du rôle
                try:
                    role_resp = supabase.table('user_roles').select('role').eq('email', email).execute()
                    if role_resp.data:
                        st.session_state.role = role_resp.data[0]['role']
                    else:
                        st.session_state.role = "operateur"
                except:
                    st.session_state.role = "operateur"

                # === CRÉATION DU COOKIE ICI ===
                # Expire dans 30 jours
                expires = datetime.datetime.now() + datetime.timedelta(days=30)
                cookie_manager.set("bibars_email", email, expires_at=expires)
                
                st.success(f"Connexion réussie !")
                time.sleep(1)
                st.rerun()
                
        except Exception:
            st.error("Email ou mot de passe incorrect.")

if __name__ == "__main__":
    login_page()
