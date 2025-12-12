import streamlit as st
import time
import streamlit.components.v1 as components 
from supabase import create_client

# ... après les imports ...

# --- VIGILE SÉCURITÉ ---
if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("⛔ Vous devez vous connecter sur la page d'accueil d'abord.")
    st.stop() # Arrête le chargement de la page ici
# -----------------------


# --- CONFIGURATION (Mets tes clés ici) ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"


@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="SCANNER", page_icon="🔫", layout="centered")

st.markdown("""
    <style>
    .stTextInput > div > div > input { font-size: 30px; text-align: center; background-color: #f0f2f6; }
    div[data-testid="stButton"] > button { width: 100%; height: 80px; font-size: 20px; font-weight: bold; border-radius: 10px; border: 2px solid #ddd; }
    .big-success { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .big-error { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .palette-card { border: 2px solid #4CAF50; padding: 10px; margin: 5px; text-align: center; border-radius: 10px; background-color: #e8f5e9; }
    </style>
""", unsafe_allow_html=True)

st.title("🔫 STATION DE SCAN")

if 'commande_choisie' not in st.session_state:
    st.session_state.commande_choisie = None
if 'palette_choisie' not in st.session_state:
    st.session_state.palette_choisie = None

# ==============================================================================
# ÉTAPE 1 : CHOIX CLIENT
# ==============================================================================
if st.session_state.commande_choisie is None:
    st.info("1️⃣ CHOISISSEZ LE CLIENT")
    try:
        response = supabase.table('vue_suivi_commandes').select("*").eq('statut', 'EN_COURS').execute()
        commandes = response.data
    except: commandes = []
        
    if not commandes:
        st.warning("⚠️ Aucune commande active.")
        if st.button("🔄"): st.rerun()
    else:
        cols = st.columns(2)
        for index, cmd in enumerate(commandes):
            with cols[index % 2]:
                if st.button(f"{cmd['nom_client']}", key=f"c_{cmd['commande_id']}"):
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

    palettes_resp = supabase.table('palettes').select("*").eq('commande_id', cmd['commande_id']).order('numero').execute()
    palettes = palettes_resp.data
    
    if not palettes:
        st.warning("Aucune palette prévue. Créez-en une manuellement.")
    
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
            new_pal = {"commande_id": cmd['commande_id'], "numero": num, "type_emballage": new_type}
            supabase.table('palettes').insert(new_pal).execute()
            st.rerun()

# ==============================================================================
# ÉTAPE 3 : SCAN (AVEC BLOQUAGE SURPRODUCTION)
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
        # 1. Check Produit existe
        prod_resp = supabase.table('produits').select("*").eq('dun14_carton', code_scanne).execute()
        
        if not prod_resp.data:
            st.markdown(f'<div class="big-error">⛔ INCONNU !</div>', unsafe_allow_html=True)
        else:
            produit = prod_resp.data[0]
            
            # 2. Check Commande (Est-ce que le client veut ça ?)
            # On récupère aussi la QUANTITÉ CIBLE
            verif_cmd = supabase.table('ligne_commandes').select('*')\
                .eq('commande_id', cmd['commande_id'])\
                .eq('produit_id', produit['id']).execute()
            
            if not verif_cmd.data:
                st.markdown(f'<div class="big-error">⛔ PAS COMMANDÉ !</div>', unsafe_allow_html=True)
            
            else:
                # --- NOUVEAU : VÉRIFICATION DE LA QUANTITÉ (STOP SCAN) ---
                objectif_cartons = verif_cmd.data[0]['quantite_cible_cartons']
                
                # On compte combien on en a déjà fait
                deja_fait_resp = supabase.table('scans').select('id')\
                    .eq('commande_id', cmd['commande_id'])\
                    .eq('produit_id', produit['id']).execute()
                
                nb_deja_fait = len(deja_fait_resp.data)
                
                # TEST DE SURPRODUCTION
                if nb_deja_fait >= objectif_cartons:
                    st.markdown(f'''
                        <div class="big-error">
                            ⛔ STOP ! COMMANDE TERMINÉE<br>
                            Vous avez déjà scanné {nb_deja_fait}/{objectif_cartons} cartons.<br>
                            Impossible d'ajouter plus.
                        </div>
                    ''', unsafe_allow_html=True)
                    st.audio("https://upload.wikimedia.org/wikipedia/commons/5/52/Simulated_Error_Sound_Effects_Short_Buzzer_01.ogg", autoplay=True)
                
                else:
                    # 3. Check Palette (Mélange)
                    if produit['type_emballage'] != pal['type_emballage']:
                        st.markdown(f'''
                            <div class="big-error">
                                ⛔ MÉLANGE INTERDIT !<br>
                                Palette : {pal['type_emballage']}<br>
                                Produit : {produit['type_emballage']}
                            </div>
                        ''', unsafe_allow_html=True)
                    
                    else:
                        # 4. Succès -> Enregistrement
                        new_scan = {
                            "commande_id": cmd['commande_id'],
                            "produit_id": produit['id'],
                            "palette_id": pal['id'],
                            "poids_enregistre": produit['poids_fixe_carton']
                        }
                        try:
                            supabase.table("scans").insert(new_scan).execute()
                            # On affiche le progrès (ex: 5/10)
                            st.markdown(f'''
                                <div class="big-success">
                                    ✅ AJOUTÉ (N°{nb_deja_fait + 1}/{objectif_cartons})<br>
                                    {produit['designation']}
                                </div>
                            ''', unsafe_allow_html=True)
                        except Exception as e: st.error(f"Erreur : {e}")

    # Info Palette
    st.caption(f"Contenu actuel de la Palette {pal['numero']} :")
    scans_pal = supabase.table('scans').select("poids_enregistre").eq('palette_id', pal['id']).execute()
    total_pal = sum([s['poids_enregistre'] for s in scans_pal.data]) if scans_pal.data else 0
    st.progress(min(total_pal/500, 1.0))
    st.write(f"**Poids Palette : {total_pal} kg**")

    components.html("""<script>var input = window.parent.document.querySelector("input[type=text]"); input.focus();</script>""", height=0)

