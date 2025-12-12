import streamlit as st
import pandas as pd
import time
import google.generativeai as genai
from datetime import datetime
from supabase import create_client

# --- TES CLÉS (A REMPLIR) ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"
GOOGLE_API_KEY = "AIzaSyCxjeTMmF1IZHGtjkhCdaNclhpRzTEiAh0"


genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="Smart Factory", page_icon="🏭", layout="wide")

# CSS Design
st.markdown("""
<style>
    .prod-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 5px solid #4CAF50;
    }
    .big-percent { font-size: 40px; font-weight: bold; color: #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR : FILTRE DATE (DEMANDE 4) ---
st.sidebar.title("📅 Filtres")
date_selected = st.sidebar.date_input("Date de Production", value=datetime.now())
# On transforme la date en string pour la comparaison
date_str = date_selected.strftime("%Y-%m-%d")

st.title(f"🏭 DASHBOARD DU {date_selected.strftime('%d/%m/%Y')}")

placeholder = st.empty()

# Fonction IA
def ask_ai(txt):
    try:
        return model.generate_content(f"Analyse prod usine: {txt}").text
    except: return "IA Indisponible"

while True:
    try:
        # 1. On récupère TOUTES les commandes (Vue Suivi)
        # Mais on va filtrer en Python car la vue SQL est parfois complexe à filtrer par date si elle n'est pas exposée
        # Le mieux : récupérer la vue et filtrer le dataframe
        resp = supabase.table("vue_suivi_commandes").select("*").execute()
        data_brute = resp.data
        
        # 2. Filtrage par date (On a besoin de récupérer la date de création de la commande pour filtrer)
        # Comme la vue 'vue_suivi_commandes' que j'ai donné avant n'avait pas la date, on va faire une astuce:
        # On va re-récupérer les IDs des commandes de la date choisie
        
        # Récup des IDs commandes du jour choisi (created_at commence par la date)
        # Le filtre gte (>=) date 00:00 et lte (<=) date 23:59
        cmds_day = supabase.table('commandes').select('id')\
            .gte('created_at', f"{date_str} 00:00:00")\
            .lte('created_at', f"{date_str} 23:59:59")\
            .execute()
        
        ids_du_jour = [c['id'] for c in cmds_day.data]
        
        # Maintenant on filtre les données de la vue pour ne garder que ces IDs
        df = pd.DataFrame(data_brute)
        
        if df.empty or not ids_du_jour:
            with placeholder.container():
                st.warning(f"Aucune commande trouvée pour le {date_selected.strftime('%d/%m/%Y')}.")
        else:
            # On ne garde que les lignes dont 'commande_id' est dans la liste du jour
            df_filtered = df[df['commande_id'].isin(ids_du_jour)]
            
            if df_filtered.empty:
                with placeholder.container():
                    st.warning("Commandes trouvées mais pas de données dans la vue (bug synchro).")
            else:
                with placeholder.container():
                    # KPI
                    total_kg = df_filtered['total_kg_produit'].sum()
                    total_cartons = df_filtered['total_cartons_scannes'].sum()
                    
                    k1, k2, k3 = st.columns(3)
                    k1.metric("📦 Colis Faits", int(total_cartons))
                    k2.metric("⚖️ Tonnage", f"{total_kg} kg")
                    k3.metric("🏭 Commandes", len(df_filtered))
                    
                    # IA Button
                    if st.button("🧠 Analyse IA", key="btn_ai"):
                        txt = f"Date {date_str}. Total {total_kg}kg. Détail: " + str(df_filtered[['nom_client', 'total_kg_produit']].to_dict())
                        st.info(ask_ai(txt))
                        
                    st.divider()

                    # LISTE DES CARTES
                    for _, row in df_filtered.iterrows():
                        obj = float(row['objectif_kg'])
                        curr = float(row['total_kg_produit'])
                        # Eviter division par zero
                        prog = min(curr / obj, 1.0) if obj > 0 else 0
                        
                        with st.container():
                            st.markdown(f"""
                            <div class="prod-card">
                                <h3>{row['nom_client']} <span style="color:gray;font-size:14px">({row['reference_interne']})</span></h3>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.progress(prog)
                                st.write(f"**{curr} kg** / {obj} kg")
                            with c2:
                                st.markdown(f"<div class='big-percent'>{int(prog*100)}%</div>", unsafe_allow_html=True)

                            # DETAIL
                            with st.expander("Voir Détail"):
                                # On récupère les scans
                                scans = supabase.table('scans').select('produit_id, poids_enregistre')\
                                    .eq('commande_id', row['commande_id']).execute()
                                
                                if scans.data:
                                    # Pour avoir les noms produits, on a besoin de la table produits
                                    # (Optimisation : charger produits une seule fois hors boucle serait mieux, mais ok ici)
                                    prods = supabase.table('produits').select('id, designation').execute()
                                    df_s = pd.DataFrame(scans.data)
                                    df_p = pd.DataFrame(prods.data)
                                    merged = df_s.merge(df_p, left_on='produit_id', right_on='id')
                                    
                                    recap = merged.groupby('designation').agg(
                                        Colis=('poids_enregistre', 'count'),
                                        Poids=('poids_enregistre', 'sum')
                                    ).reset_index()
                                    
                                    st.dataframe(recap, use_container_width=True, hide_index=True)
                                else:
                                    st.caption("Rien scanné.")
                    
                    st.caption(f"Last update: {time.strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"Erreur : {e}")
    
    time.sleep(5)
