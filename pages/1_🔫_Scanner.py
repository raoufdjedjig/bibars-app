import streamlit as st
import time
import streamlit.components.v1 as components 
from datetime import datetime
from supabase import create_client

# --- VIGILE SÉCURITÉ ---
if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("⛔ Accès refusé. Connectez-vous d'abord.")
    st.stop()

# --- TES CLÉS ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# Note : On enlève st.set_page_config ici car c'est Home.py qui gère ça maintenant
st.title("🔫 STATION DE SCAN")

st.markdown("""
    <style>
    .stTextInput > div > div > input { font-size: 30px; text-align: center; background-color: #f0f2f6; }
    div[data-testid="stButton"] > button { width: 100%; height: 90px; font-size: 18px; font-weight: bold; border-radius: 10px; border: 2px solid #ddd; }
    .big-success { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .big-error { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .palette-card { border: 2px solid #4CAF50; padding: 10px; margin: 5px; text-align: center; border-radius: 10px; background-color: #e8f5e9; }
    </style>
""", unsafe_allow_html=True)

if 'commande_choisie' not in st.session_state:
    st.session_state.commande_choisie = None
if 'palette_choisie' not in st.session_state:
    st.session_state.palette_choisie = None

# ==============================================================================
# ÉTAPE 1 : CHOIX CLIENT (AVEC DATE)
# ==============================================================================
if st.session_state.commande_choisie is None:
    st.info("1️⃣ CHOISISSEZ LA COMMANDE")
    try:
        # On récupère les commandes actives triées par date (la plus récente en haut)
        # On utilise la table 'commandes' directement pour être sûr d'avoir la date, 
        # et on joint les clients manuellement ou via la vue si elle est à jour.
        # Ici on utilise la VUE, assure-toi qu'elle contient 'created_at'.
        # Sinon, on utilise la table 'commandes' et 'clients'.
        
        # Option robuste : Table commandes + Table clients
        cmds = supabase.table('commandes').select('*, clients(nom)').eq('statut', 'EN_COURS').order('created_at', desc=True).execute()
        data_cmds = cmds.data
    except: data_cmds = []
        
    if not data_cmds:
        st.warning("⚠️ Aucune commande active.")
        if st.button("🔄 Actualiser"): st.rerun()
    else:
        cols = st.columns(2)
        for index, cmd in enumerate(data_cmds):
            with cols[index % 2]:
                # Formatage de la date (ex: 2023-12-12T08:00:00 -> 12/12)
                date_obj = datetime.strptime(cmd['created_at'].split('T')[0], "%Y-%m-%d")
                date_fmt = date_obj.strftime("%d/%m")
                
                # Nom du client (Supabase renvoie parfois clients: {nom: ...})
                nom_client = cmd['clients']['nom'] if 'clients' in cmd else "CLIENT"
                
                # Label du bouton avec la DATE
                label = f"{nom_client}\n📅 {date_fmt} (Réf: {cmd['reference_interne']})"
                
                # On ajoute le nom_client aplati pour la suite
                cmd['nom_client'] = nom_client 
                
                if st.button(label, key=f"c_{cmd['id']}"):
                    st.session_state.commande_choisie = cmd
                    st.rerun()

# ==============================================================================
# ÉTAPE 2 : CHOIX PALETTE
# ==============================================================================
elif st.session_state.palette_choisie is None:
    cmd = st.session_state.commande_choisie
    
    c_back, c_tit = st.columns([1, 4])
    with c_back:
        if st.button("🔙", type="secondary"):
            st.session_state.commande_choisie = None
            st.rerun()
    with c_tit:
        st.markdown(f"### 📦 {cmd['nom_client']} > CHOIX PALETTE")

    palettes_resp = supabase.table('palettes').select("*").eq('commande_id', cmd['id']).order('numero').execute()
    palettes = palettes_resp.data
    
    if not palettes:
        st.warning("Aucune palette prévue.")
    
    cols_pal = st.columns(2)
    for idx, pal in enumerate(palettes):
        with cols_pal[idx % 2]:
            label = f"PALETTE {pal['numero']}\n({pal['type_emballage']})"
            if st.button(label, key=f"pal_{pal['id']}"):
                st.session_state.palette_choisie = pal
                st.rerun()
    
    st.divider()
    with st.expander("➕ Créer une nouvelle palette (Hors plan)"):
        new_type = st.selectbox("Type", ["MAP", "SOUS_VIDE", "VRAC"])
        if st.button("Créer Palette"):
            num = len(palettes) + 1
            new_pal = {"commande_id": cmd['id'], "numero": num, "type_emballage": new_type}
            supabase.table('palettes').insert(new_pal).execute()
            st.rerun()

# ==============================================================================
# ÉTAPE 3 : SCAN
# ==============================================================================
else:
    cmd = st.session_state.commande_choisie
    pal = st.session_state.palette_choisie
    
    c_back, c_info = st.columns([1, 4])
    with c_back:
        if st.button("🔙 PALETTE"):
            st.session_state.palette_choisie = None
            st.rerun()
    with c_info:
        st.markdown(f"""
        <div class='palette-card'>
            <b>CLIENT : {cmd['nom_client']}</b><br>
            PALETTE N°{pal['numero']} • <b>{pal['type_emballage']}</b>
        </div>
        """, unsafe_allow_html=True)

    with st.form("scan_form", clear_on_submit=True):
        code_scanne = st.text_input("SCANNEZ 👇", key="scan_input")
        submitted = st.form_submit_button("VALIDER")

    if submitted and code_scanne:
        prod_resp = supabase.table('produits').select("*").eq('dun14_carton', code_scanne).execute()
        
        if not prod_resp.data:
            st.markdown(f'<div class="big-error">⛔ INCONNU !</div>', unsafe_allow_html=True)
        else:
            produit = prod_resp.data[0]
            verif_cmd = supabase.table('ligne_commandes').select('*').eq('commande_id', cmd['id']).eq('produit_id', produit['id']).execute()
            
            if not verif_cmd.data:
                st.markdown(f'<div class="big-error">⛔ PAS COMMANDÉ !</div>', unsafe_allow_html=True)
            else:
                objectif_cartons = verif_cmd.data[0]['quantite_cible_cartons']
                deja_fait_resp = supabase.table('scans').select('id').eq('commande_id', cmd['id']).eq('produit_id', produit['id']).execute()
                nb_deja_fait = len(deja_fait_resp.data)
                
                if nb_deja_fait >= objectif_cartons:
                    st.markdown(f'<div class="big-error">⛔ STOP ! QUOTA ATTEINT ({nb_deja_fait}/{objectif_cartons})</div>', unsafe_allow_html=True)
                elif produit['type_emballage'] != pal['type_emballage']:
                    st.markdown(f'<div class="big-error">⛔ ERREUR PALETTE ({produit["type_emballage"]} vs {pal["type_emballage"]})</div>', unsafe_allow_html=True)
                else:
                    new_scan = {"commande_id": cmd['id'], "produit_id": produit['id'], "palette_id": pal['id'], "poids_enregistre": produit['poids_fixe_carton']}
                    try:
                        supabase.table("scans").insert(new_scan).execute()
                        st.markdown(f'<div class="big-success">✅ OK (N°{nb_deja_fait + 1})<br>{produit["designation"]}</div>', unsafe_allow_html=True)
                    except Exception as e: st.error(f"Erreur : {e}")

    scans_pal = supabase.table('scans').select("poids_enregistre").eq('palette_id', pal['id']).execute()
    total_pal = sum([s['poids_enregistre'] for s in scans_pal.data]) if scans_pal.data else 0
    st.progress(min(total_pal/500, 1.0))
    st.write(f"**Poids Palette : {total_pal} kg**")

    components.html("""<script>var input = window.parent.document.querySelector("input[type=text]"); input.focus();</script>""", height=0)


