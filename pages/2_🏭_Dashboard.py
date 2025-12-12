import streamlit as st
import pandas as pd
import time
import google.generativeai as genai
from supabase import create_client

# --- TES CLÉS (A REMPLIR) ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"
GOOGLE_API_KEY = "AIzaSyCxjeTMmF1IZHGtjkhCdaNclhpRzTEiAh0"


# Configuration
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="Smart Factory", page_icon="🏭", layout="wide")

# --- CSS POUR LE DESIGN "CARTE" ---
st.markdown("""
<style>
    /* Style global */
    .block-container { padding-top: 1rem; }
    
    /* Style des cartes */
    .prod-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        border-left: 5px solid #4CAF50; /* Bordure verte à gauche */
    }
    .metric-box {
        text-align: center;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
    }
    .big-percent {
        font-size: 40px;
        font-weight: bold;
        color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏭 MONITORING PRODUCTION")
st.caption("Suivi temps réel • Usine Bibars Polska")

placeholder = st.empty()

# Fonction d'analyse IA
def ask_ai_analysis(txt_context):
    prompt = f"Analyse ces données de production (usine poulet) et donne 3 points clés (Succès ou Alerte) : {txt_context}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Erreur IA"

while True:
    try:
        # 1. Données globales
        resp_cmd = supabase.table("vue_suivi_commandes").select("*").eq('statut', 'EN_COURS').execute()
        commandes = resp_cmd.data

        with placeholder.container():
            # --- KPI GLOBAUX (Haut de page) ---
            # On récupère les totaux
            all_scans = supabase.table('scans').select("poids_enregistre").execute()
            df_all = pd.DataFrame(all_scans.data)
            total_kg = df_all['poids_enregistre'].sum() if not df_all.empty else 0
            
            # Affichage en 3 colonnes colorées
            k1, k2, k3 = st.columns(3)
            k1.metric("📦 TOTAL CARTONS", len(df_all) if not df_all.empty else 0, delta="Aujourd'hui")
            k2.metric("⚖️ TONNAGE JOUR", f"{total_kg} kg", delta="Production")
            k3.metric("🏭 LIGNES ACTIVES", len(commandes), delta="En cours")
            
            # --- BOUTON IA ---
            if st.button("🧠 DEMANDER ANALYSE AI", key="unique_key_ia"):
                resume = f"Total: {total_kg}kg. " + "".join([f"{c['nom_client']}: {c['total_kg_produit']}/{c['objectif_kg']}kg. " for c in commandes])
                st.info(ask_ai_analysis(resume))

            st.markdown("---")

            if not commandes:
                st.info("😴 Aucune production en cours. L'usine est calme.")
            
            else:
                # --- AFFICHAGE "CARTE" PAR CLIENT ---
                for cmd in commandes:
                    # Calculs
                    obj = float(cmd['objectif_kg'])
                    curr = float(cmd['total_kg_produit'])
                    prog = min(curr / obj, 1.0)
                    prog_percent = int(prog * 100)
                    
                    # Début de la Carte
                    with st.container():
                        st.markdown(f"""
                        <div class="prod-card">
                            <h3>🛒 CLIENT : {cmd['nom_client']} <span style="font-size:16px;color:gray">({cmd['reference_interne']})</span></h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns([2, 1])
                        
                        with c1:
                            # Barre de progression et chiffres
                            st.progress(prog)
                            c1a, c1b = st.columns(2)
                            c1a.metric("Réalisé", f"{curr} kg")
                            c1b.metric("Objectif", f"{obj} kg")
                        
                        with c2:
                            # Gros Pourcentage
                            st.markdown(f"<div style='text-align:center'><span class='big-percent'>{prog_percent}%</span><br>Avancement</div>", unsafe_allow_html=True)

                        # --- TABLEAU DE DÉTAIL (LE PLUS BEAU) ---
                        with st.expander(f"Voir le détail des articles ({cmd['nom_client']})", expanded=True):
                            
                            # Récupération détail
                            scans_resp = supabase.table('scans').select('produit_id, poids_enregistre').eq('commande_id', cmd['commande_id']).execute()
                            
                            if scans_resp.data:
                                prods_resp = supabase.table('produits').select('id, designation').execute()
                                df_scans = pd.DataFrame(scans_resp.data)
                                df_prods = pd.DataFrame(prods_resp.data)
                                
                                merged = df_scans.merge(df_prods, left_on='produit_id', right_on='id')
                                
                                # On prépare le tableau final
                                recap = merged.groupby('designation').agg(
                                    Cartons=('poids_enregistre', 'count'),
                                    Poids=('poids_enregistre', 'sum')
                                ).reset_index()
                                
                                # Ajout d'une colonne "Barre visuelle" (Astuce Pandas)
                                # On imagine que chaque article a un mini objectif pour la beauté (ex: max de la série)
                                max_val = recap['Poids'].max()
                                recap['Visuel'] = recap['Poids'] # On duplique pour l'affichage
                                
                                # AFFICHAGE AVEC BARRES INTÉGRÉES
                                st.dataframe(
                                    recap,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "designation": "Article",
                                        "Cartons": st.column_config.NumberColumn("📦 Colis"),
                                        "Poids": st.column_config.NumberColumn("⚖️ Poids (kg)", format="%.1f kg"),
                                        "Visuel": st.column_config.ProgressColumn(
                                            "Volume",
                                            help="Volume relatif",
                                            format="%.0f",
                                            min_value=0,
                                            max_value=float(max_val),
                                        ),
                                    }
                                )
                            else:
                                st.caption("⏳ En attente du premier scan...")
                        
                        st.write("") # Espace vide

            st.caption(f"Dernière synchro : {time.strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"Erreur : {e}")
    
    time.sleep(5)

