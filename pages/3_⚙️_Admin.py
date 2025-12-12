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

# ON AJOUTE UN 4EME ONGLET ICI 👇
tab1, tab2, tab3, tab4 = st.tabs(["👥 CLIENTS", "📅 PLANIFICATION", "📜 HISTORIQUE", "📦 PRODUITS"])

# ==============================================================================
# ONGLET 1 : GESTION CLIENTS
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
            for c in clients_data:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{c['nom']}**")
                if c2.button("🗑️", key=f"del_cli_{c['id']}"):
                    try:
                        supabase.table('clients').delete().eq('id', c['id']).execute()
                        st.rerun()
                    except:
                        st.error("Impossible : ce client a des commandes.")

# ==============================================================================
# ONGLET 2 : PLANIFICATION
# ==============================================================================
with tab2:
    st.sidebar.header("Configuration Planning")
    date_prod = st.sidebar.date_input("Date de Production", value=datetime.now())
    date_str = date_prod.strftime("%d/%m/%y")
    
    col_gauche, col_droite = st.columns([1.2, 1])
    
    with col_gauche:
        st.subheader(f"1. Préparer une commande ({date_str})")
        clients_resp = supabase.table('clients').select("*").order('nom').execute()
        liste_clients = {c['nom']: c['id'] for c in clients_resp.data} if clients_resp.data else {}
        prods_resp = supabase.table('produits').select("*").order('designation').execute()
        
        if liste_clients and prods_resp.data:
            choix_client = st.selectbox("Client", list(liste_clients.keys()))
            ref_auto = f"CMD-{choix_client}-{date_str}"
            
            df_prods = pd.DataFrame(prods_resp.data)
            if "Objectif KG" not in df_prods.columns: df_prods['Objectif KG'] = 0.0

            df_editor = df_prods[['id', 'designation', 'poids_fixe_carton', 'Objectif KG']]

            edited_df = st.data_editor(
                df_editor,
                key=f"edit_{choix_client}",
                column_config={
                    "id": None,
                    "designation": "Article",
                    "poids_fixe_carton": st.column_config.NumberColumn("Poids/Colis", disabled=True),
                    "Objectif KG": st.column_config.NumberColumn("Objectif (KG)", min_value=0, step=10)
                },
                hide_index=True, use_container_width=True, height=350
            )
            
            if st.button("➕ AJOUTER AU PANIER"):
                selection = edited_df[edited_df['Objectif KG'] > 0].copy()
                if not selection.empty:
                    selection['nb_cartons'] = selection.apply(lambda x: math.ceil(x['Objectif KG'] / x['poids_fixe_carton']), axis=1)
                    poids_total_calc = (selection['nb_cartons'] * selection['poids_fixe_carton']).sum()
                    item = {
                        "client_nom": choix_client, "client_id": liste_clients[choix_client],
                        "ref_commande": ref_auto, "date_prod": date_prod.strftime("%Y-%m-%d"),
                        "produits": selection, "poids_total": poids_total_calc
                    }
                    st.session_state.panier_production.append(item)
                    st.success("Ajouté !")

    with col_droite:
        st.subheader("2. Panier & Validation")
        if st.session_state.panier_production:
            total_global = 0
            indices_to_remove = []
            for i, item in enumerate(st.session_state.panier_production):
                total_global += item['poids_total']
                with st.expander(f"{item['client_nom']} - {item['poids_total']} kg"):
                    st.dataframe(item['produits'][['designation', 'Objectif KG', 'nb_cartons']], hide_index=True)
                    if st.button("🗑️ Retirer", key=f"rm_{i}"): indices_to_remove.append(i)

            if indices_to_remove:
                for index in sorted(indices_to_remove, reverse=True): del st.session_state.panier_production[index]
                st.rerun()

            st.divider()
            st.metric("TOTAL JOURNÉE", f"{total_global} kg")
            c_pdf, c_send = st.columns(2)
            pdf_data = create_pdf(date_str, st.session_state.panier_production)
            c_pdf.download_button("📄 TÉLÉCHARGER PDF", pdf_data, f"Prod.pdf", "application/pdf")
            
            if c_send.button("🚀 ENVOYER EN PRODUCTION", type="primary"):
                try:
                    barre = st.progress(0)
                    for idx, item in enumerate(st.session_state.panier_production):
                        new_cmd = {
                            "client_id": item['client_id'], "reference_interne": item['ref_commande'],
                            "statut": "EN_COURS", "objectif_kg": float(item['poids_total']),
                            "created_at": f"{item['date_prod']} 08:00:00"
                        }
                        res = supabase.table('commandes').insert(new_cmd).execute()
                        cmd_id = res.data[0]['id']
                        lignes = []
                        for _, row in item['produits'].iterrows():
                            lignes.append({
                                "commande_id": cmd_id, "produit_id": row['id'],
                                "quantite_cible_cartons": int(row['nb_cartons'])
                            })
                        supabase.table('ligne_commandes').insert(lignes).execute()
                        barre.progress((idx+1)/len(st.session_state.panier_production))
                    st.success("Envoyé !")
                    st.session_state.panier_production = []
                    st.rerun()
                except Exception as e: st.error(f"Erreur : {e}")

# ==============================================================================
# ONGLET 3 : HISTORIQUE
# ==============================================================================
with tab3:
    st.header("Gestion des Commandes")
    filtre_date = st.date_input("Filtrer par date", value=datetime.now(), key="hist_date")
    try:
        cmds = supabase.table('commandes').select("*").order('created_at', desc=True).limit(20).execute().data
        clients = supabase.table('clients').select("*").execute().data
        map_cli = {c['id']: c['nom'] for c in clients}
        if cmds:
            for cmd in cmds:
                cmd_date = cmd['created_at'].split('T')[0]
                if str(filtre_date) == cmd_date:
                    nom_cli = map_cli.get(cmd['client_id'], 'Inconnu')
                    with st.expander(f"{cmd_date} | {nom_cli} | {cmd['reference_interne']} ({cmd['statut']})"):
                        c1, c2, c3 = st.columns(3)
                        new_stat = c1.selectbox("Statut", ["EN_COURS", "PAUSE", "TERMINE"], index=["EN_COURS", "PAUSE", "TERMINE"].index(cmd['statut']), key=f"s_{cmd['id']}")
                        new_obj = c2.number_input("Objectif", value=float(cmd['objectif_kg']), key=f"o_{cmd['id']}")
                        if c3.button("💾 Maj", key=f"u_{cmd['id']}"):
                            supabase.table('commandes').update({"statut": new_stat, "objectif_kg": new_obj}).eq('id', cmd['id']).execute()
                            st.rerun()
                        if st.button("🗑️ Supprimer", key=f"d_{cmd['id']}", type="primary"):
                            supabase.table('scans').delete().eq('commande_id', cmd['id']).execute()
                            supabase.table('ligne_commandes').delete().eq('commande_id', cmd['id']).execute()
                            supabase.table('commandes').delete().eq('id', cmd['id']).execute()
                            st.rerun()
    except Exception as e: st.error(f"Erreur : {e}")

# ==============================================================================
# ONGLET 4 : GESTION PRODUITS (NOUVEAU)
# ==============================================================================
with tab4:
    st.header("📦 Base de données Articles")
    
    col_new_prod, col_list_prod = st.columns([1, 2])
    
    # --- FORMULAIRE D'AJOUT ---
    with col_new_prod:
        st.subheader("Créer un Article")
        with st.form("new_product_form", clear_on_submit=True):
            designation = st.text_input("Désignation Produit").upper()
            code_barre = st.text_input("Code Barre Carton (DUN14)")
            poids_colis = st.number_input("Poids Fixe par Colis (kg)", min_value=0.1, step=0.1, format="%.1f")
            
            if st.form_submit_button("✅ Ajouter l'article"):
                if designation and code_barre and poids_colis > 0:
                    try:
                        # Vérification doublon code barre
                        exist = supabase.table('produits').select("*").eq('dun14_carton', code_barre).execute()
                        if exist.data:
                            st.error("Ce Code Barre existe déjà !")
                        else:
                            new_prod = {
                                "designation": designation,
                                "dun14_carton": code_barre,
                                "poids_fixe_carton": poids_colis
                            }
                            supabase.table('produits').insert(new_prod).execute()
                            st.success(f"Article '{designation}' ajouté !")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                else:
                    st.warning("Veuillez remplir tous les champs.")

    # --- LISTE DES PRODUITS ---
    with col_list_prod:
        st.subheader("Catalogue Actuel")
        
        # On récupère tous les produits
        all_prods = supabase.table('produits').select("*").order('designation').execute().data
        
        if all_prods:
            # On affiche un tableau propre
            df_prods = pd.DataFrame(all_prods)
            
            # Affichage tableau
            st.dataframe(
                df_prods[['designation', 'dun14_carton', 'poids_fixe_carton']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "designation": "Article",
                    "dun14_carton": "Code Barre",
                    "poids_fixe_carton": st.column_config.NumberColumn("Poids (kg)", format="%.1f kg")
                }
            )
            
            st.caption("Pour supprimer un article, contactez l'admin technique (protection sécurité).")
        else:
            st.info("Aucun produit dans la base.")
