import streamlit as st

st.set_page_config(
    page_title="Bibars Production",
    page_icon="🐔",
    layout="centered"
)

st.title("🐔 Bibars Polska - Production")

st.markdown("""
### Bienvenue sur l'application de gestion d'usine.

Utilisez le menu à gauche pour naviguer :

* **🔫 Scanner** : Pour les opérateurs sur la ligne (Tablettes).
* **🏭 Dashboard** : Pour suivre l'avancement en temps réel (TV/Bureau).
* **⚙️ Admin** : Pour créer des clients et lancer des commandes.

---
*V 1.0 - Connecté à Supabase*
""")

# Petit test de connexion pour rassurer
try:
    from supabase import create_client
    
    # ---------------------------------------------------------
    # COLLE TA CLÉ JUSTE EN DESSOUS ENTRE LES GUILLEMETS
    # ---------------------------------------------------------
    SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co" 
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"
    
    # Création de la connexion
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Si on arrive ici sans erreur, c'est gagné
    st.success("✅ Connexion Base de Données : OK")

except Exception as e:
    # C'est ce bloc qui manquait !
    st.error(f"❌ Erreur de connexion : {e}")
