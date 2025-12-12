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
    
# --- TES CLÉS ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"

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
            # 1. Connexion Supabase Auth (Vérifie le mot de passe)
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            if response.user:
                st.session_state.user = response.user
                
                # 2. RÉCUPÉRATION DU RÔLE (NOUVEAU)
                # On demande à la table : "Quel est le rôle de cet email ?"
                role_resp = supabase.table('user_roles').select('role').eq('email', email).execute()
                
                if role_resp.data:
                    # On a trouvé le rôle dans la base
                    st.session_state.role = role_resp.data[0]['role']
                else:
                    # Cas de sécurité : Si l'utilisateur n'est pas dans la liste des rôles, on le met opérateur par défaut ou on bloque
                    st.warning("Compte valide mais aucun rôle défini. Contactez l'admin.")
                    st.session_state.role = "operateur" # ou None pour bloquer
                
                st.success(f"Connexion réussie (Rôle : {st.session_state.role}) !")
                time.sleep(0.5)
                st.rerun()
                
        except Exception as e:
            st.error("Identifiants incorrects ou erreur système.")
            
# On lance la fonction
login_page()            
