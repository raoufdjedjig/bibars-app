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

# CSS Design
st.markdown("""
    <style>
    .stTextInput > div > div > input { font-size: 30px; text-align: center; background-color: #f0f2f6; }
    .big-success { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .big-error { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    .big-warning { background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 10px;}
    
    div[data-testid="stButton"] > button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🔫 STATION DE SCAN")

# --- 1. SÉLECTION DU CLIENT ---
try:
    response = supabase.table('vue_suivi_commandes').select("*").eq('statut', 'EN_COURS').execute()
    liste_commandes = response.data
except:
    liste_commandes = []

if not liste_commandes:
    st.warning("⚠️ Aucune commande active.")
    st.stop()

options_dict = {f"{c['nom_client']} - {c['reference_interne']}": c for c in liste_commandes}
choix = st.selectbox("CLIENT :", list(options_dict.keys()))

commande_active = options_dict[choix]
id_commande = commande_active['commande_id']

# --- 2. GESTION DU SCAN ---
st.markdown("---")
with st.form("scan_form", clear_on_submit=True):
    code_scanne = st.text_input("SCANNEZ ICI 👇", key="scan_input")
    submitted = st.form_submit_button("VALIDER")

if submitted and code_scanne:
    prod_resp = supabase.table('produits').select("*").eq('dun14_carton', code_scanne).execute()
    
    if not prod_resp.data:
        st.markdown(f'<div class="big-error">⛔ CODE INCONNU !<br>{code_scanne}</div>', unsafe_allow_html=True)
    else:
        produit = prod_resp.data[0]
        new_scan = {
            "commande_id": id_commande,
            "produit_id": produit['id'],
            "poids_enregistre": produit['poids_fixe_carton']
        }
        try:
            supabase.table("scans").insert(new_scan).execute()
            st.markdown(f'''
                <div class="big-success">
                    ✅ AJOUTÉ : {produit['designation']} (+{produit['poids_fixe_carton']} kg)
                </div>
            ''', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- 3. ANNULATION ---
st.markdown("---")
last_scan_resp = supabase.table('scans').select("*").eq('commande_id', id_commande).order('scanned_at', desc=True).limit(1).execute()

if last_scan_resp.data:
    last_scan = last_scan_resp.data[0]
    col1, col2 = st.columns([1, 3])
    with col2:
        heure_scan = last_scan['scanned_at'].split('T')[1][:8]
        st.caption(f"Dernier : {last_scan['poids_enregistre']} kg (à {heure_scan})")
    with col1:
        if st.button("🗑️ ANNULER LE DERNIER", type="primary"):
            supabase.table('scans').delete().eq('id', last_scan['id']).execute()
            st.markdown(f'<div class="big-warning">🗑️ SUPPRIMÉ !</div>', unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()

# --- 4. HISTORIQUE ---
st.markdown("---")
st.subheader("Historique récent :")
last_scans_list = supabase.table('scans').select("scanned_at, poids_enregistre").eq('commande_id', id_commande).order('scanned_at', desc=True).limit(5).execute()

if last_scans_list.data:
    for scan in last_scans_list.data:
        heure = scan['scanned_at'].split('T')[1].split('.')[0]
        st.text(f"🕒 {heure} - {scan['poids_enregistre']} kg")

# Focus auto JS (C'est cette ligne qui posait problème avant, ici elle est corrigée)
components.html("""<script>var input = window.parent.document.querySelector("input[type=text]"); input.focus();</script>""", height=0)