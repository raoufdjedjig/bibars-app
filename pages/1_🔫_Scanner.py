import streamlit as st
import time
import streamlit.components.v1 as components
from supabase import create_client

# --- CONFIGURATION (Mets tes clés ici) ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="SCANNER", page_icon="🔫", layout="centered")

# --- CSS SPÉCIAL TABLETTE ---
# On grossit les boutons pour les doigts
st.markdown("""
    <style>
    .stTextInput > div > div > input { font-size: 30px; text-align: center; background-color: #f0f2f6; }
    
    /* Gros boutons de sélection client */
    div[data-testid="stButton"] > button {
        width: 100%;
        height: 80px; /* Hauteur confortable pour le doigt */
        font-size: 20px;
        font-weight: bold;
        border-radius: 10px;
        border: 2px solid #ddd;
    }
    
    /* Messages */
    .big-success { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .big-error { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .big-warning { background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("🔫 STATION DE SCAN")

# Initialisation de la mémoire (Quel client est choisi ?)
if 'commande_choisie' not in st.session_state:
    st.session_state.commande_choisie = None

# ==============================================================================
# ÉTAPE 1 : CHOIX DU CLIENT (MODE GRILLE)
# ==============================================================================
if st.session_state.commande_choisie is None:
    st.info("👆 APPUYEZ SUR UN CLIENT POUR COMMENCER")
    
    try:
        # On récupère les commandes actives
        response = supabase.table('vue_suivi_commandes').select("*").eq('statut', 'EN_COURS').execute()
        commandes = response.data
    except:
        commandes = []
        
    if not commandes:
        st.warning("⚠️ Aucune commande active. Demandez au chef de lancer une prod.")
        if st.button("🔄 Rafraîchir"): st.rerun()
    else:
        # ON CRÉE UNE GRILLE DE BOUTONS (2 colonnes)
        cols = st.columns(2)
        
        for index, cmd in enumerate(commandes):
            # On alterne entre colonne 1 et colonne 2
            col = cols[index % 2]
            
            with col:
                # Le label du bouton
                label_btn = f"{cmd['nom_client']}\n({cmd['reference_interne']})"
                
                # Si on clique dessus
                if st.button(label_btn, key=f"btn_{cmd['commande_id']}"):
                    st.session_state.commande_choisie = cmd
                    st.rerun() # On recharge la page pour passer à l'étape 2

# ==============================================================================
# ÉTAPE 2 : SCANNER (MODE OPÉRATEUR)
# ==============================================================================
else:
    # On récupère les infos stockées
    cmd = st.session_state.commande_choisie
    
    # --- BARRE DU HAUT ---
    c_back, c_title = st.columns([1, 4])
    with c_back:
        # Bouton pour revenir au menu
        if st.button("🔙 CHANGER", type="secondary"):
            st.session_state.commande_choisie = None
            st.rerun()
            
    with c_title:
        st.success(f"📦 CLIENT : **{cmd['nom_client']}**")

    # --- FORMULAIRE DE SCAN ---
    with st.form("scan_form", clear_on_submit=True):
        # Focus automatique sur cette case
        code_scanne = st.text_input("SCANNEZ ICI 👇", key="scan_input")
        # Bouton invisible qui s'active avec "Entrée"
        submitted = st.form_submit_button("VALIDER")

    # --- TRAITEMENT DU SCAN ---
    if submitted and code_scanne:
        # 1. Vérif Produit existe
        prod_resp = supabase.table('produits').select("*").eq('dun14_carton', code_scanne).execute()
        
        if not prod_resp.data:
            st.markdown(f'<div class="big-error">⛔ INCONNU !<br>{code_scanne}</div>', unsafe_allow_html=True)
        else:
            produit = prod_resp.data[0]
            
            # 2. Vérif Produit commandé (POKA YOKE)
            verif = supabase.table('ligne_commandes').select('*')\
                .eq('commande_id', cmd['commande_id'])\
                .eq('produit_id', produit['id']).execute()
                
            if not verif.data:
                st.markdown(f'<div class="big-error">⛔ PAS COMMANDÉ !<br>{produit["designation"]}</div>', unsafe_allow_html=True)
            else:
                # 3. Enregistrement
                new_scan = {
                    "commande_id": cmd['commande_id'],
                    "produit_id": produit['id'],
                    "poids_enregistre": produit['poids_fixe_carton']
                }
                try:
                    supabase.table("scans").insert(new_scan).execute()
                    st.markdown(f'''
                        <div class="big-success">
                            ✅ OK ! +{produit['poids_fixe_carton']} kg<br>
                            {produit['designation']}
                        </div>
                    ''', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # --- SUPPRESSION DU DERNIER ---
    st.markdown("---")
    last = supabase.table('scans').select("*").eq('commande_id', cmd['commande_id']).order('scanned_at', desc=True).limit(1).execute()
    
    if last.data:
        l = last.data[0]
        c1, c2 = st.columns([2, 1])
        with c1:
            st.info(f"Dernier : {l['poids_enregistre']} kg (à {l['scanned_at'].split('T')[1][:5]})")
        with c2:
            if st.button("🗑️ SUPPRIMER", type="primary"):
                supabase.table('scans').delete().eq('id', l['id']).execute()
                st.warning("Dernier scan annulé !")
                time.sleep(1)
                st.rerun()

    # --- FOCUS AUTO (JavaScript) ---
    components.html("""<script>var input = window.parent.document.querySelector("input[type=text]"); input.focus();</script>""", height=0)
