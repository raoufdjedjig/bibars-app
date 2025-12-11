
import streamlit as st
import pandas as pd
import time
import google.generativeai as genai
from supabase import create_client

# --- REMPLACE ICI AVEC TES INFOS SUPABASE ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"
GOOGLE_API_KEY = "AIzaSyCxjeTMmF1IZHGtjkhCdaNclhpRzTEiAh0"


# Configuration de l'IA
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="Smart Factory", page_icon="🏭", layout="wide")
st.title("🏭 SUIVI DE PRODUCTION & IA MANAGER")

placeholder = st.empty()

# Fonction d'analyse IA
def ask_ai_analysis(df_global, df_detail_text):
    prompt = f"""
    Tu es le directeur de production d'une usine de volaille.
    Voici les données temps réel :
    {df_detail_text}
    
    Donne-moi une analyse concise (3 points max) :
    1. Quelle est la performance globale ?
    2. Y a-t-il un client ou un produit qui pose problème (retard) ?
    3. Une action recommandée pour le chef d'équipe maintenant.
    Sois direct et professionnel.
    """
    with st.spinner('🧠 Gemini analyse la production...'):
        response = model.generate_content(prompt)
        return response.text

while True:
    try:
        # 1. Données globales
        resp_cmd = supabase.table("vue_suivi_commandes").select("*").eq('statut', 'EN_COURS').execute()
        commandes = resp_cmd.data

        with placeholder.container():
            # --- ZONE KPI ---
            # On récupère les totaux via une petite requête rapide
            all_scans = supabase.table('scans').select("poids_enregistre").execute()
            df_all = pd.DataFrame(all_scans.data)
            total_kg = df_all['poids_enregistre'].sum() if not df_all.empty else 0
            
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("⚖️ Total Produit (Jour)", f"{total_kg} kg")
            kpi2.metric("🏭 Commandes Actives", len(commandes))
            
            # --- ZONE IA (NOUVEAU) ---
            kpi3.write("") # Espacement
            if kpi3.button("🧠 ANALYSE IA"):
                if not commandes:
                    st.warning("Pas de données à analyser.")
                else:
                    # On prépare un résumé texte pour l'IA
                    resume_txt = f"Total Jour: {total_kg}kg.\n"
                    for c in commandes:
                        resume_txt += f"- Client {c['nom_client']}: {c['total_kg_produit']}/{c['objectif_kg']} kg.\n"
                    
                    analyse = ask_ai_analysis(None, resume_txt)
                    st.success("Rapport généré :")
                    st.info(analyse)

            st.divider()

            if not commandes:
                st.warning("Aucune production en cours.")
            else:
                # --- ZONE DÉTAIL PAR CLIENT ---
                for cmd in commandes:
                    # Barre de progression
                    obj = float(cmd['objectif_kg'])
                    curr = float(cmd['total_kg_produit'])
                    prog = min(curr / obj, 1.0)
                    
                    st.markdown(f"### 📦 {cmd['nom_client']} ({int(prog*100)}%)")
                    st.progress(prog)
                    
                    # Tableau détail
                    scans_resp = supabase.table('scans').select('produit_id, poids_enregistre').eq('commande_id', cmd['commande_id']).execute()
                    
                    if scans_resp.data:
                        prods_resp = supabase.table('produits').select('id, designation').execute()
                        df_scans = pd.DataFrame(scans_resp.data)
                        df_prods = pd.DataFrame(prods_resp.data)
                        
                        merged = df_scans.merge(df_prods, left_on='produit_id', right_on='id')
                        recap = merged.groupby('designation').agg(
                            Cartons=('poids_enregistre', 'count'),
                            Total_KG=('poids_enregistre', 'sum')
                        ).reset_index()
                        
                        st.dataframe(recap, use_container_width=True, hide_index=True)
                    else:
                        st.caption("Démarrage de la production...")
                    
                    st.markdown("---")

            st.caption(f"Live : {time.strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"Erreur : {e}")
    
    time.sleep(5) # Pause un peu plus longue pour laisser le temps à l'IA