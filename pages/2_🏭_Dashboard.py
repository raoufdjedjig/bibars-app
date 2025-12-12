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

st.markdown("""
<style>
    .prod-card {
        background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; border-left: 5px solid #4CAF50;
    }
    .big-percent { font-size: 40px; font-weight: bold; color: #4CAF50; }
</style>
""", unsafe_allow_html=True)

# FILTRES
st.sidebar.title("📅 Filtres")
date_selected = st.sidebar.date_input("Date de Production", value=datetime.now())
date_str = date_selected.strftime("%Y-%m-%d")

st.title(f"🏭 DASHBOARD DU {date_selected.strftime('%d/%m/%Y')}")

placeholder = st.empty()

def ask_ai(txt):
    try:
        return model.generate_content(f"Analyse prod usine: {txt}").text
    except: return "IA Indisponible"

while True:
    try:
        # 1. On récupère les commandes du jour
        cmds_day = supabase.table('commandes').select('id')\
            .gte('created_at', f"{date_str} 00:00:00")\
            .lte('created_at', f"{date_str} 23:59:59")\
            .execute()
        
        ids_du_jour = [c['id'] for c in cmds_day.data]
        
        resp = supabase.table("vue_suivi_commandes").select("*").execute()
        data_brute = resp.data
        df = pd.DataFrame(data_brute)
        
        if df.empty or not ids_du_jour:
            with placeholder.container():
                st.warning(f"Aucune commande trouvée pour le {date_selected.strftime('%d/%m/%Y')}.")
        else:
            df_filtered = df[df['commande_id'].isin(ids_du_jour)]
            
            if df_filtered.empty:
                with placeholder.container():
                    st.warning("Commandes trouvées mais pas de données synchro.")
            else:
                with placeholder.container():
                    # KPI GLOBAUX
                    total_kg = df_filtered['total_kg_produit'].sum()
                    k1, k2, k3 = st.columns(3)
                    k1.metric("📦 Colis Faits", int(df_filtered['total_cartons_scannes'].sum()))
                    k2.metric("⚖️ Tonnage", f"{total_kg} kg")
                    k3.metric("🏭 Commandes", len(df_filtered))
                    
                    if st.button("🧠 Analyse IA", key="btn_ai"):
                        txt = f"Date {date_str}. Total {total_kg}kg."
                        st.info(ask_ai(txt))
                        
                    st.divider()

                    # CARTES CLIENTS
                    for _, row in df_filtered.iterrows():
                        obj = float(row['objectif_kg'])
                        curr = float(row['total_kg_produit'])
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

                            # --- TABLEAU DÉTAILLÉ (NOUVEAU) ---
                            with st.expander("Voir Détail (Fait vs Reste à faire)"):
                                cmd_id = row['commande_id']
                                
                                # A. On récupère ce qu'il FAUT faire (Ligne Commandes)
                                lignes = supabase.table('ligne_commandes').select('produit_id, quantite_cible_cartons').eq('commande_id', cmd_id).execute()
                                
                                # B. On récupère ce qui est FAIT (Scans)
                                scans = supabase.table('scans').select('produit_id, poids_enregistre').eq('commande_id', cmd_id).execute()
                                
                                # C. On récupère les infos produits (Noms + Poids fixe)
                                prods = supabase.table('produits').select('id, designation, poids_fixe_carton').execute()
                                
                                if lignes.data and prods.data:
                                    # Création DataFrames
                                    df_cible = pd.DataFrame(lignes.data) # Ce qu'on doit faire
                                    df_prods = pd.DataFrame(prods.data)  # Le catalogue
                                    
                                    if scans.data:
                                        df_scans = pd.DataFrame(scans.data) # Ce qu'on a fait
                                        # On groupe les scans par produit pour avoir le total fait
                                        df_fait = df_scans.groupby('produit_id').size().reset_index(name='nb_fait')
                                    else:
                                        df_fait = pd.DataFrame(columns=['produit_id', 'nb_fait'])
                                    
                                    # FUSION DES DONNÉES (Le Merge intelligent)
                                    # 1. On joint Cible + Produits pour avoir les noms
                                    merge1 = df_cible.merge(df_prods, left_on='produit_id', right_on='id')
                                    
                                    # 2. On joint avec le Fait (Left join pour garder même ce qui n'est pas commencé)
                                    final = merge1.merge(df_fait, left_on='produit_id', right_on='produit_id', how='left')
                                    
                                    # 3. Nettoyage (remplacer les vides par 0)
                                    final['nb_fait'] = final['nb_fait'].fillna(0).astype(int)
                                    
                                    # 4. Calculs KG
                                    final['Poids Fait (kg)'] = final['nb_fait'] * final['poids_fixe_carton']
                                    final['Objectif (kg)'] = final['quantite_cible_cartons'] * final['poids_fixe_carton']
                                    
                                    # 5. Calcul Reste à faire
                                    final['Reste (Cartons)'] = final['quantite_cible_cartons'] - final['nb_fait']
                                    # On évite les nombres négatifs si on a trop produit
                                    final['Reste (Cartons)'] = final['Reste (Cartons)'].apply(lambda x: x if x > 0 else 0)
                                    
                                    # Affichage propre
                                    display_df = final[['designation', 'Poids Fait (kg)', 'Objectif (kg)', 'Reste (Cartons)']]
                                    display_df.columns = ['Article', 'Fait (kg)', 'Cible (kg)', 'Reste à faire (Colis)']
                                    
                                    st.dataframe(
                                        display_df, 
                                        use_container_width=True, 
                                        hide_index=True,
                                        column_config={
                                            "Reste à faire (Colis)": st.column_config.NumberColumn(
                                                "Reste (Colis)",
                                                help="Combien de cartons il manque",
                                                format="%d 📦"
                                            )
                                        }
                                    )
                                else:
                                    st.info("Détail non disponible.")
    except Exception as e:
        st.error(f"Erreur : {e}")
    time.sleep(5)

