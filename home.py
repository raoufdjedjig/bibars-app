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
    # REMETS TES CLES ICI UNE DERNIERE FOIS
    SUPABASE_URL = "TON_URL_SUPABASE_ICI" 
    SUPABASE_KEY = "TA_CLE_PUBLIQUE_ANON_ICI"
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    st.success("✅ Connexion Base de Données : OK")
except:
    st.error("❌ Erreur de connexion (Vérifiez les clés dans Home.py)")