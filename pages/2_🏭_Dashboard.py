import streamlit as st
import pandas as pd
import time
import altair as alt # La librairie de graphiques native de Streamlit
import google.generativeai as genai
from datetime import datetime
from supabase import create_client

# ... après les imports ...

# --- VIGILE SÉCURITÉ ---
if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("⛔ Vous devez vous connecter sur la page d'accueil d'abord.")
    st.stop() # Arrête le chargement de la page ici
# -----------------------

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
        background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; border-left: 5px solid #4CAF50;
    }
    .big-percent { font-size: 40px; font-weight: bold; color: #4CAF50; }
    /* Fond un peu gris pour faire ressortir les graphs */
    .stApp { background-color: #f8f9fa; }
</style>
""", unsafe_allow_html=True)

# FILTRES
st.sidebar.title("📅 Filtres")
date_selected = st.sidebar.date_input("Date de Production", value=datetime.now())
date_str = date_selected.strftime("%Y-%m-%d")

st.title(f"🏭 DASHBOARD ANALYTIQUE - {date_selected.strftime('%d/%m/%Y')}")

placeholder = st.empty()

def ask_ai(txt):
    try:
        return model.generate_content(f"Tu es un expert industriel. Analyse ces données de prod et sois bref (3 points): {txt}").text
    except: return "IA Indisponible"

while True:
    try:
        # 1. On récupère les IDs des commandes du jour
        cmds_day = supabase.table('commandes').select('id')\
            .gte('created_at', f"{date_str} 00:00:00")\
            .lte('created_at', f"{date_str} 23:59:59")\
            .execute()
        
        ids_du_jour = [c['id'] for c in cmds_day.data]
        
        # 2. Données Commandes (Vue globale)
        resp = supabase.table("vue_suivi_commandes").select("*").execute()
        df_vue = pd.DataFrame(resp.data)
        
        if df_vue.empty or not ids_du_jour:
            with placeholder.container():
                st.warning(f"😴 L'usine est calme. Aucune donnée pour le {date_selected.strftime('%d/%m/%Y')}.")
        else:
            df_filtered = df_vue[df_vue['commande_id'].isin(ids_du_jour)]
            
            # 3. Données SCANS (Pour les graphiques détaillés)
            # On récupère TOUS les scans de ces commandes pour faire les graphs
            scans_day = supabase.table('scans').select('poids_enregistre, scanned_at, produit_id')\
                .in_('commande_id', ids_du_jour)\
                .execute()
            
            df_scans = pd.DataFrame(scans_day.data)

            if df_filtered.empty:
                st.warning("Erreur synchro vue.")
            else:
                with placeholder.container():
                    
                    # --- ZONE 1 : KPI GLOBAUX ---
                    total_kg = df_filtered['total_kg_produit'].sum()
                    k1, k2, k3 = st.columns(3)
                    k1.metric("📦 Colis Faits", int(df_filtered['total_cartons_scannes'].sum()))
                    k2.metric("⚖️ Tonnage Jour", f"{total_kg} kg")
                    k3.metric("🏭 Commandes Actives", len(df_filtered))
                    
                    st.markdown("---")

                    # --- ZONE 2 : GRAPHIQUES D'ANALYSE (NOUVEAU) ---
                    st.subheader("📊 Analyse Visuelle")
                    
                    if not df_scans.empty:
                        # Préparation des données pour les graphs
                        
                        # G1: Cadence Horaire (Extraction de l'heure)
                        df_scans['Heure'] = pd.to_datetime(df_scans['scanned_at']).dt.hour
                        hourly_data = df_scans.groupby('Heure')['poids_enregistre'].sum().reset_index()
                        
                        # G2: Comparaison Cible vs Fait par Client
                        # On restructure les données pour Altair
                        df_chart_cli = df_filtered[['nom_client', 'total_kg_produit', 'objectif_kg']].copy()
                        df_chart_cli = df_chart_cli.melt('nom_client', var_name='Type', value_name='Kilos')
                        # Renommer pour faire joli
                        df_chart_cli['Type'] = df_chart_cli['Type'].replace({'total_kg_produit': 'Réalisé', 'objectif_kg': 'Objectif'})

                        # G3: Top Produits (On a besoin des noms produits, on fait une petite requête rapide)
                        prods_info = supabase.table('produits').select('id, designation').execute()
                        df_p_info = pd.DataFrame(prods_info.data)
                        df_scans_merged = df_scans.merge(df_p_info, left_on='produit_id', right_on='id')
                        prod_distrib = df_scans_merged.groupby('designation')['poids_enregistre'].sum().reset_index()

                        # --- AFFICHAGE DES 3 GRAPHIQUES ---
                        col_g1, col_g2 = st.columns(2)
                        
                        with col_g1:
                            st.caption("📈 Cadence de Production (KG par Heure)")
                            chart_line = alt.Chart(hourly_data).mark_area(
                                line={'color':'darkgreen'},
                                color=alt.Gradient(
                                    gradient='linear',
                                    stops=[alt.GradientStop(color='white', offset=0),
                                           alt.GradientStop(color='darkgreen', offset=1)],
                                    x1=1, x2=1, y1=1, y2=0
                                )
                            ).encode(
                                x=alt.X('Heure:O', title='Heure de la journée'),
                                y=alt.Y('poids_enregistre', title='KG Produits'),
                                tooltip=['Heure', 'poids_enregistre']
                            ).properties(height=300)
                            st.altair_chart(chart_line, use_container_width=True)

                        with col_g2:
                            st.caption("🏆 Répartition par Produit")
                            chart_pie = alt.Chart(prod_distrib).mark_arc(innerRadius=50).encode(
                                theta=alt.Theta(field="poids_enregistre", type="quantitative"),
                                color=alt.Color(field="designation", type="nominal", legend=None), # Legend off pour clarté
                                tooltip=['designation', 'poids_enregistre']
                            ).properties(height=300)
                            st.altair_chart(chart_pie, use_container_width=True)

                        st.caption("📊 Comparatif Objectif vs Réalisé")
                        chart_bar = alt.Chart(df_chart_cli).mark_bar().encode(
                            x=alt.X('nom_client', title=None),
                            y=alt.Y('Kilos', title='Poids (KG)'),
                            color=alt.Color('Type', scale=alt.Scale(domain=['Objectif', 'Réalisé'], range=['#e0e0e0', '#4CAF50'])),
                            tooltip=['nom_client', 'Type', 'Kilos']
                        ).properties(height=250)
                        st.altair_chart(chart_bar, use_container_width=True)

                    else:
                        st.info("Pas assez de données pour afficher les graphiques.")

                    st.markdown("---")

                    # --- ZONE 3 : DÉTAIL CARTES (EXISTANT) ---
                    st.subheader("📋 Suivi Détaillé")
                    
                    if st.button("🧠 Analyse IA du Dashboard", key="btn_ai"):
                        txt_context = f"Total {total_kg}kg. Prod/Heure: {hourly_data.to_dict() if not df_scans.empty else 'N/A'}"
                        st.info(ask_ai(txt_context))

                    for _, row in df_filtered.iterrows():
                        # ... (CODE IDENTIQUE A AVANT POUR LES CARTES) ...
                        obj = float(row['objectif_kg'])
                        curr = float(row['total_kg_produit'])
                        prog = min(curr / obj, 1.0) if obj > 0 else 0
                        
                        with st.container():
                            st.markdown(f"""<div class="prod-card"><h3>{row['nom_client']}</h3></div>""", unsafe_allow_html=True)
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.progress(prog)
                                st.write(f"**{curr} kg** / {obj} kg")
                            with c2:
                                st.markdown(f"<div class='big-percent'>{int(prog*100)}%</div>", unsafe_allow_html=True)

                            # DETAIL TABLEAU
                            with st.expander("Voir Détail"):
                                cmd_id = row['commande_id']
                                # REQUETES DETAIL
                                lignes = supabase.table('ligne_commandes').select('produit_id, quantite_cible_cartons').eq('commande_id', cmd_id).execute()
                                scans = supabase.table('scans').select('produit_id, poids_enregistre').eq('commande_id', cmd_id).execute()
                                prods = supabase.table('produits').select('id, designation, poids_fixe_carton').execute()
                                
                                if lignes.data and prods.data:
                                    df_cible = pd.DataFrame(lignes.data)
                                    df_prods = pd.DataFrame(prods.data)
                                    if scans.data:
                                        df_scans = pd.DataFrame(scans.data)
                                        df_fait = df_scans.groupby('produit_id').size().reset_index(name='nb_fait')
                                    else:
                                        df_fait = pd.DataFrame(columns=['produit_id', 'nb_fait'])
                                    
                                    m1 = df_cible.merge(df_prods, left_on='produit_id', right_on='id')
                                    final = m1.merge(df_fait, on='produit_id', how='left')
                                    final['nb_fait'] = final['nb_fait'].fillna(0).astype(int)
                                    final['Poids Fait'] = final['nb_fait'] * final['poids_fixe_carton']
                                    final['Reste'] = (final['quantite_cible_cartons'] - final['nb_fait']).clip(lower=0)
                                    
                                    st.dataframe(
                                        final[['designation', 'Poids Fait', 'Reste']],
                                        use_container_width=True, hide_index=True,
                                        column_config={"Reste": st.column_config.NumberColumn("Reste (Colis)", format="%d 📦")}
                                    )

    except Exception as e:
        st.error(f"Erreur : {e}")
    
    time.sleep(5)

