
import streamlit as st
from supabase import create_client
import time

# --- TES CLÉS (À REMPLIR) ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"

def login_page():
    # CAS 1 : UTILISATEUR DÉJÀ CONNECTÉ
    if "user" in st.session_state and st.session_state.user:
        st.title("Profil Utilisateur")
        st.write(f"Connecté en tant que : **{st.session_state.user.email}**")
        
        # Affichage du Rôle
        role = st.session_state.get('role', 'Inconnu')
        if role == 'admin':
            st.info("👑 Droits : ADMINISTRATEUR")
        else:
            st.info("👷 Droits : OPÉRATEUR")

        if st.button("Se déconnecter", type="primary"):
            st.session_state.user = None
            st.session_state.role = None
            st.rerun()
        return

    # CAS 2 : FORMULAIRE DE CONNEXION
    st.title("🔒 Connexion Bibars")
    st.write("Veuillez vous identifier pour accéder à l'usine.")

    # Connexion DB
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erreur de connexion serveur : {e}")
        st.stop()

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter", type="primary")

    if submit:
        try:
            # 1. Vérification Mot de passe (Supabase Auth)
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            if response.user:
                st.session_state.user = response.user
                
                # 2. Récupération du Rôle dans la table 'user_roles'
                try:
                    role_resp = supabase.table('user_roles').select('role').eq('email', email).execute()
                    if role_resp.data:
                        st.session_state.role = role_resp.data[0]['role']
                    else:
                        # Si pas de rôle défini, on met opérateur par défaut ou on bloque
                        st.warning("Aucun rôle défini pour cet email. Accès Opérateur par défaut.")
                        st.session_state.role = "operateur"
                except:
                    # Si la table user_roles n'existe pas encore ou erreur
                    st.session_state.role = "operateur"

                st.success(f"Bienvenue ! ({st.session_state.role})")
                time.sleep(0.5)
                st.rerun() # Recharge la page pour mettre à jour le menu Home.py
                
        except Exception:
            st.error("Email ou mot de passe incorrect.")

if __name__ == "__main__":
    login_page()

