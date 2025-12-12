import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
from supabase import create_client

# --- TES CLÉS ICI ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="ADMINISTRATION", page_icon="⚙️", layout="wide")

# Initialisation panier
if 'panier_production' not in st.session_state:
    st.session_state.panier_production = []

# --- FONCTION PDF ---
def create_pdf(date_prevue, panier):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"ORDRE DE PRODUCTION - {date_prevue}", ln=True, align='C')
    pdf.ln(10)
    for item in panier:
        client = item['client_nom']
        ref = item['ref_commande']
        produits = item['produits']
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, f"CLIENT : {client} (Ref: {ref})", ln=True, fill=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 8, "Article", 1)
        pdf.cell(30, 8, "Objectif KG", 1)
        pdf.cell(30, 8, "Cartons", 1)
        pdf.ln()
        pdf.set_font("Arial", '', 10)
        for _, row in produits.iterrows():
            pdf.cell(100, 8, row['designation'][:45], 1)
            pdf.cell(30, 8, str(row['Objectif KG']), 1)
            pdf.cell(30, 8, str(row['nb_cartons']), 1)
            pdf.ln()
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

st.title("⚙️ GESTION & PLANIFICATION")

# Organisation en 3 Onglets
tab1, tab2, tab3 = st.tabs(["👥 GESTION CLIENTS", "📅 PLANIFICATION (KG)", "📜 HISTORIQUE & MODIF"])

# ==============================================================================
# ONGLET 1 : GESTION CLIENTS (AJOUT & SUPPRESSION)
# ==============================================================================
with tab1:
    col_add, col_list = st.columns([1, 2])
    
    with col_add:
        st.subheader("Nouveau Client")
        with st.form("add_cli"):
            nom_cli = st.text_input("Nom").upper()
            if st.form_submit_button("Ajouter"):
                if nom_cli:
                    supabase.table('clients').insert({"nom": nom_cli}).execute()
                    st.success("Ajouté !")
                    st.rerun()

    with col_list:
        st.subheader("Liste des Clients")
        clients_data = supabase.table('clients').select("*").order('nom').execute().data
        
        if clients_data:
            # On affiche sous forme de petit tableau avec bouton supprimer
            for c in clients_data:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{c['nom']}**")
                if c2.button("🗑️", key=f"del_cli_{c['id']}"):
                    # Suppression (Attention aux contraintes de clé étrangère si commandes existent)
                    try:
                        supabase.table('clients').delete().eq('id', c['id']).execute()
                        st.warning(f"Client {c['nom']} supprimé.")
                        st.rerun()
                    except:
                        st.error("Impossible de supprimer ce client (il a déjà des commandes).")
        else:
            st.info("Aucun client.")

# ==============================================================================
# ONGLET 2 : PLANIFICATION (SAISIE EN KG)
# ==============================================================================
with tab2:
    st.sidebar.header("Configuration Planning")
    date_prod = st.sidebar.date_input("Date de Production", value=datetime.now())
    date_str = date_prod.strftime("%d/%m/%y")
    
    col_gauche, col_droite = st.columns([1.2, 1])
    
    # --- A GAUCHE : LE FORMULAIRE ---
    with col_gauche:
        st.subheader(f"1. Préparer une commande ({date_str})")
        
        # Chargement
        clients_resp = supabase.table('clients').select("*").order('nom').execute()
        liste_clients = {c['nom']: c['id'] for c in clients_resp.data} if clients_resp.data else {}
        
        prods_resp = supabase.table('produits').select("*").order('designation').execute()
        
        if liste_clients and prods_resp.data:
            choix_client = st.selectbox("Client", list(liste_clients.keys()))
            ref_auto = f"CMD-{choix_client}-{date_str}"
            
            # Préparation Tableau Saisie
            df_prods = pd.DataFrame(prods_resp.data)
            # DEMANDE 5 : Saisie en KG
            if "Objectif KG" not in df_prods.columns:
                df_prods['Objectif KG'] = 0.0

            df_editor = df_prods[['id', 'designation', 'poids_fixe_carton', 'Objectif KG']]

            st.caption("👇 Saisissez les quantités en KILOGRAMMES")
            edited_df = st.data_editor(
                df_editor,
                key=f"edit_{choix_client}",
                column_config={
                    "id": None,
                    "designation": "Article",
                    "poids_fixe_carton": st.column_config.NumberColumn("Poids/Colis", disabled=True),
                    "Objectif KG": st.column_config.NumberColumn("Objectif (KG)", min_value=0, step=10)
                },
                hide_index=True,
                use_container_width=True,
                height=350
            )
            
            if st.button("➕ AJOUTER AU PANIER"):
                # Filtrer les lignes > 0
                selection = edited_df[edited_df['Objectif KG'] > 0].copy()
                
                if selection.empty:
                    st.warning("Mettez des KG quelque part !")
                else:
                    # CALCUL AUTOMATIQUE DES CARTONS (Maths)
                    # Nb Cartons = Objectif KG / Poids du carton (Arrondi au dessus)
                    selection['nb_cartons'] = selection.apply(
                        lambda x: math.ceil(x['Objectif KG'] / x['poids_fixe_carton']), axis=1
                    )
                    
                    # On recalcule le poids total théorique exact
                    poids_total_calc = (selection['nb_cartons'] * selection['poids_fixe_carton']).sum()

                    item = {
                        "client_nom": choix_client,
                        "client_id": liste_clients[choix_client],
                        "ref_commande": ref_auto,
                        "date_prod": date_prod.strftime("%Y-%m-%d"),
                        "produits": selection,
                        "poids_total": poids_total_calc
                    }
                    st.session_state.panier_production.append(item)
                    st.success("Commande ajoutée au panier (à droite) !")
    
    # --- A DROITE : LE PANIER MODIFIABLE ---
    with col_droite:
        st.subheader("2. Panier & Validation")
        
        if not st.session_state.panier_production:
            st.info("Panier vide.")
        else:
            total_global = 0
            indices_to_remove = []

            # DEMANDE 2 : Possibilité de modifier/supprimer dans le panier
            for i, item in enumerate(st.session_state.panier_production):
                total_global += item['poids_total']
                
                with st.expander(f"{item['client_nom']} - Total: {item['poids_total']} kg", expanded=True):
                    # On montre le tableau
                    st.dataframe(
                        item['produits'][['designation', 'Objectif KG', 'nb_cartons']], 
                        hide_index=True, 
                        use_container_width=True
                    )
                    
                    c_del, c_info = st.columns([1, 3])
                    c_info.caption("Pour modifier les quantités, supprimez et refaites la saisie.")
                    if c_del.button("🗑️ Retirer", key=f"rm_{i}"):
                        indices_to_remove.append(i)

            # Gestion suppression
            if indices_to_remove:
                for index in sorted(indices_to_remove, reverse=True):
                    del st.session_state.panier_production[index]
                st.rerun()

            st.divider()
            st.metric("TOTAL JOURNÉE", f"{total_global} kg")

            # BOUTONS FINAUX
            c_pdf, c_send = st.columns(2)
            
            pdf_data = create_pdf(date_str, st.session_state.panier_production)
            c_pdf.download_button("📄 TÉLÉCHARGER PDF", pdf_data, f"Prod_{date_str.replace('/','-')}.pdf", "application/pdf")
            
            if c_send.button("🚀 ENVOYER EN PRODUCTION", type="primary"):
                try:
                    barre = st.progress(0)
                    for idx, item in enumerate(st.session_state.panier_production):
                        # 1. Création Commande
                        new_cmd = {
                            "client_id": item['client_id'],
                            "reference_interne": item['ref_commande'],
                            "statut": "EN_COURS",
                            "objectif_kg": float(item['poids_total']),
                            "created_at": f"{item['date_prod']} 08:00:00" # On force la date choisie
                        }
                        res = supabase.table('commandes').insert(new_cmd).execute()
                        cmd_id = res.data[0]['id']
                        
                        # 2. Création Lignes
                        lignes = []
                        for _, row in item['produits'].iterrows():
                            lignes.append({
                                "commande_id": cmd_id,
                                "produit_id": row['id'],
                                "quantite_cible_cartons": int(row['nb_cartons'])
                            })
                        supabase.table('ligne_commandes').insert(lignes).execute()
                        barre.progress((idx+1)/len(st.session_state.panier_production))
                    
                    st.success("✅ Planning envoyé aux tablettes !")
                    st.session_state.panier_production = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur envoi : {e}")

# ==============================================================================
# ONGLET 3 : HISTORIQUE & MODIFICATIONS (DEMANDE 3)
# ==============================================================================
with tab3:
    st.header("Gestion des Commandes existantes")
    
    # Filtre de recherche
    filtre_date = st.date_input("Filtrer par date de création", value=datetime.now(), key="hist_date")
    
    # Requête Supabase pour récupérer les commandes de cette date (ou toutes)
    # Astuce : On récupère les 50 dernières commandes pour simplifier
    try:
        # On fait une jointure manuelle simple
        cmds = supabase.table('commandes').select("*").order('created_at', desc=True).limit(20).execute().data
        clients = supabase.table('clients').select("*").execute().data
        map_cli = {c['id']: c['nom'] for c in clients}
        
        if not cmds:
            st.info("Aucun historique.")
        else:
            # Affichage sous forme de tableau éditable
            for cmd in cmds:
                # Filtrage visuel par date si besoin (optionnel)
                cmd_date = cmd['created_at'].split('T')[0]
                if str(filtre_date) == cmd_date:
                    
                    nom_cli = map_cli.get(cmd['client_id'], 'Inconnu')
                    
                    with st.expander(f"{cmd_date} | {nom_cli} | {cmd['reference_interne']} ({cmd['statut']})"):
                        
                        c1, c2, c3 = st.columns(3)
                        
                        # MODIFICATION STATUT
                        new_statut = c1.selectbox("Statut", ["EN_COURS", "PAUSE", "TERMINE"], index=["EN_COURS", "PAUSE", "TERMINE"].index(cmd['statut']), key=f"st_{cmd['id']}")
                        
                        # MODIFICATION OBJECTIF
                        new_obj = c2.number_input("Objectif KG", value=float(cmd['objectif_kg']), key=f"obj_{cmd['id']}")
                        
                        # BOUTON MISE A JOUR
                        if c3.button("💾 Mettre à jour", key=f"upd_{cmd['id']}"):
                            supabase.table('commandes').update({
                                "statut": new_statut,
                                "objectif_kg": new_obj
                            }).eq('id', cmd['id']).execute()
                            st.success("Mis à jour !")
                            st.rerun()
                            
                        st.divider()
                        
                        # SUPPRESSION
                        if st.button("🗑️ SUPPRIMER CETTE COMMANDE DÉFINITIVEMENT", key=f"del_cmd_{cmd['id']}", type="primary"):
                            # Attention : il faut supprimer les scans et lignes d'abord (cascade)
                            # Supabase gère souvent ça si configuré, sinon on force :
                            supabase.table('scans').delete().eq('commande_id', cmd['id']).execute()
                            supabase.table('ligne_commandes').delete().eq('commande_id', cmd['id']).execute()
                            supabase.table('commandes').delete().eq('id', cmd['id']).execute()
                            st.error("Commande supprimée.")
                            st.rerun()

    except Exception as e:
        st.error(f"Erreur lecture historique : {e}")
