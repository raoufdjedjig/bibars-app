import streamlit as st

# --- INITIALISATION SESSION ---
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

# --- DÉFINITION DES PAGES ---
# On "prépare" les pages sans les afficher
page_login = st.Page("login.py", title="Connexion", icon="🔒")
page_scanner = st.Page("pages/1_🔫_Scanner.py", title="Scanner", icon="🔫")
page_dashboard = st.Page("pages/2_🏭_Dashboard.py", title="Dashboard", icon="🏭")
page_admin = st.Page("pages/3_⚙️_Admin.py", title="Admin", icon="⚙️")

# --- LOGIQUE DU ROUTEUR (Le Cerveau) ---

if st.session_state.user is None:
    # CAS 1 : PAS CONNECTÉ
    # On force l'affichage d'une seule page : le Login.
    # Le menu de gauche sera vide ou caché.
    pg = st.navigation([page_login])

else:
    # CAS 2 : CONNECTÉ
    # On affiche le menu selon le rôle ! (C'est encore plus pro)
    
    if st.session_state.role == "admin":
        # L'admin voit TOUT
        pg = st.navigation({
            "Production": [page_scanner],
            "Gestion": [page_dashboard, page_admin],
            "Compte": [page_login] # Pour se déconnecter éventuellement
        })
    else:
        # L'opérateur ne voit QUE le scanner (il ne peut même pas cliquer sur Admin)
        pg = st.navigation({
            "Production": [page_scanner],
            "Compte": [page_login]
        })

# --- LANCEMENT DE LA PAGE CHOISIE ---
pg.run()
