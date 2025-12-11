import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# --- TES CLÉS ICI ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"


@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="ADMINISTRATION", page_icon="⚙️", layout="wide")
st.title("⚙️ PANNEAU D'ADMINISTRATION")

tab1, tab2 = st.tabs(["👥 GÉRER LES CLIENTS", "🚀 LANCER UNE PRODUCTION"])

# --- ONGLET 1 : CLIENTS ---
with tab1:
    st.header("Nouveau Client")
    with st.form("form_client", clear_on_submit=True):
        nom_client = st.text_input("Nom du Client (ex: LIDL)").upper()
        if st.form_submit_button("Créer le Client"):
            if nom_client:
                supabase.table('clients').insert({"nom": nom_client}).execute()
                st.success(f"Client '{nom_client}' ajouté !")

    st.divider()
    st.subheader("Clients existants :")
    try:
        clients = supabase.table('clients').select("*").execute().data
        if clients:
            for c in clients:
                st.text(f"- {c['nom']}")
    except:
        st.error("Erreur de lecture clients")

# --- ONGLET 2 : CRÉER UNE COMMANDE ---
with tab2:
    st.header("Nouvelle Commande")
    
    # 1. Chargement des données (Clients et Produits)
    clients_resp = supabase.table('clients').select("*").execute()
    liste_clients = {c['nom']: c['id'] for c in clients_resp.data} if clients_resp.data else {}
    
    prods_resp = supabase.table('produits').select("id, designation, poids_fixe_carton").order('designation').execute()
    
    if not liste_clients:
        st.warning("Ajoutez des clients d'abord.")
    elif not prods_resp.data:
        st.warning("Ajoutez des produits dans la base d'abord.")
    else:
        # --- FORMULAIRE DE COMMANDE ---
        
        # A. Sélection Client
        col1, col2 = st.columns(2)
        with col1:
            choix_nom = st.selectbox("Choisir le Client", list(liste_clients.keys()))
        
        # B. Génération Automatique de la Référence
        # Format : CMD-NOMCLIENT-JJ/MM/AA
        date_str = datetime.now().strftime("%d/%m/%y")
        ref_auto = f"CMD-{choix_nom}-{date_str}"
        
        with col2:
            st.info(f"📌 Référence générée : **{ref_auto}**")

        st.markdown("---")
        st.subheader("🛒 Sélectionner les produits à produire")

        # C. Tableau éditable pour les quantités
        # On prépare les données pour le tableau
        df_prods = pd.DataFrame(prods_resp.data)
        df_prods['Quantité Cible (Cartons)'] = 0 # Colonne par défaut à 0
        
        # On garde les colonnes utiles pour l'affichage
        df_editor = df_prods[['id', 'designation', 'poids_fixe_carton', 'Quantité Cible (Cartons)']]
        
        # Affichage du "Data Editor" (Tableau Excel-like)
        edited_df = st.data_editor(
            df_editor, 
            column_config={
                "id": None, # On cache l'ID
                "designation": "Article",
                "poids_fixe_carton": st.column_config.NumberColumn("Poids Carton (kg)", disabled=True),
                "Quantité Cible (Cartons)": st.column_config.NumberColumn("Quantité à produire", min_value=0, step=1)
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )

        # Calcul automatique du poids total prévisionnel
        total_poids_prevu = (edited_df['poids_fixe_carton'] * edited_df['Quantité Cible (Cartons)']).sum()
        st.caption(f"Objectif Total estimé : {total_poids_prevu} kg")

        # D. BOUTON DE VALIDATION
        if st.button("🚀 LANCER LA PRODUCTION", type="primary"):
            # 1. On filtre pour ne garder que les produits avec quantité > 0
            lignes_a_inserer = edited_df[edited_df['Quantité Cible (Cartons)'] > 0]
            
            if lignes_a_inserer.empty:
                st.error("⚠️ Veuillez mettre une quantité sur au moins un article.")
            else:
                try:
                    # 2. Création de la Commande principale
                    new_cmd = {
                        "client_id": liste_clients[choix_nom],
                        "reference_interne": ref_auto,
                        "statut": "EN_COURS",
                        "objectif_kg": float(total_poids_prevu)
                    }
                    cmd_result = supabase.table('commandes').insert(new_cmd).execute()
                    
                    if cmd_result.data:
                        new_cmd_id = cmd_result.data[0]['id']
                        
                        # 3. Insertion des lignes de détail (ligne_commandes)
                        lignes_data = []
                        for index, row in lignes_a_inserer.iterrows():
                            lignes_data.append({
                                "commande_id": new_cmd_id,
                                "produit_id": row['id'],
                                "quantite_cible_cartons": int(row['Quantité Cible (Cartons)'])
                            })
                        
                        supabase.table('ligne_commandes').insert(lignes_data).execute()
                        st.success(f"✅ Commande {ref_auto} lancée avec {len(lignes_data)} articles !")
                        
                except Exception as e:
                    st.error(f"Erreur lors de la création : {e}")