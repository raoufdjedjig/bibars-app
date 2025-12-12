import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64
from supabase import create_client

# --- TES CLÉS ICI ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"


@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="PLANNING PROD", page_icon="📅", layout="wide")

# --- FONCTION GÉNÉRATION PDF ---
def create_pdf(date_prevue, panier):
    pdf = FPDF()
    pdf.add_page()
    
    # Titre
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"ORDRE DE PRODUCTION - {date_prevue}", ln=True, align='C')
    pdf.ln(10)
    
    # Pour chaque client dans le panier
    for item in panier:
        client = item['client_nom']
        ref = item['ref_commande']
        produits = item['produits'] # C'est un DataFrame
        
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255) # Bleu clair
        pdf.cell(0, 10, f"CLIENT : {client} (Ref: {ref})", ln=True, fill=True)
        
        # En-tête tableau
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 8, "Désignation", 1)
        pdf.cell(40, 8, "Qté (Colis)", 1)
        pdf.cell(40, 8, "Poids (kg)", 1)
        pdf.ln()
        
        # Lignes produits
        pdf.set_font("Arial", '', 10)
        total_poids_client = 0
        for _, row in produits.iterrows():
            nom = row['designation']
            qty = row['Quantité Cible (Cartons)']
            poids_unit = row['poids_fixe_carton']
            total = qty * poids_unit
            total_poids_client += total
            
            # On tronque le nom si trop long pour le PDF
            pdf.cell(100, 8, nom[:45], 1)
            pdf.cell(40, 8, str(int(qty)), 1)
            pdf.cell(40, 8, f"{total:.1f}", 1)
            pdf.ln()
            
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 8, f"Total Client : {total_poids_client} kg", ln=True, align='R')
        pdf.ln(5)
        
    return pdf.output(dest='S').encode('latin-1')

# --- INITIALISATION MÉMOIRE (PANIER) ---
if 'panier_production' not in st.session_state:
    st.session_state.panier_production = []

st.title("📅 PLANIFICATION DE LA PRODUCTION")

# 1. SÉLECTION DE LA DATE (Commune à tous)
st.sidebar.header("1. Configuration")
date_prod = st.sidebar.date_input("Date de Production", value=datetime.now())
date_str = date_prod.strftime("%d/%m/%y")

# --- COLONNE GAUCHE : AJOUTER DES COMMANDES ---
col_form, col_review = st.columns([1.2, 1])

with col_form:
    st.subheader("📝 Ajouter une commande au planning")
    st.markdown(f"**Date sélectionnée : {date_str}**")
    
    # Chargement clients/produits
    clients_resp = supabase.table('clients').select("*").execute()
    liste_clients = {c['nom']: c['id'] for c in clients_resp.data} if clients_resp.data else {}
    
    prods_resp = supabase.table('produits').select("id, designation, poids_fixe_carton").order('designation').execute()
    
    if not liste_clients or not prods_resp.data:
        st.error("Base de données vide (Clients ou Produits manquants).")
    else:
        # Formulaire d'ajout
        choix_client = st.selectbox("Choisir le Client", list(liste_clients.keys()))
        ref_auto = f"CMD-{choix_client}-{date_str}"
        
        # Tableau saisie
        df_prods = pd.DataFrame(prods_resp.data)
        if "Quantité Cible (Cartons)" not in df_prods.columns:
            df_prods['Quantité Cible (Cartons)'] = 0
            
        df_editor = df_prods[['id', 'designation', 'poids_fixe_carton', 'Quantité Cible (Cartons)']]
        
        # On utilise une clé unique basée sur le client pour reset le tableau quand on change
        edited_df = st.data_editor(
            df_editor, 
            key=f"editor_{choix_client}", 
            column_config={
                "id": None,
                "designation": "Article",
                "poids_fixe_carton": st.column_config.NumberColumn("Poids (kg)", disabled=True),
                "Quantité Cible (Cartons)": st.column_config.NumberColumn("Qté à faire", min_value=0)
            },
            hide_index=True,
            use_container_width=True,
            height=300
        )
        
        # Bouton Ajouter au Panier
        if st.button("➕ AJOUTER CETTE COMMANDE AU PLANNING"):
            lignes_valides = edited_df[edited_df['Quantité Cible (Cartons)'] > 0].copy()
            
            if lignes_valides.empty:
                st.warning("Veuillez saisir au moins une quantité.")
            else:
                # On ajoute dans la mémoire temporaire
                commande_temp = {
                    "client_nom": choix_client,
                    "client_id": liste_clients[choix_client],
                    "ref_commande": ref_auto,
                    "produits": lignes_valides, # On stocke le petit tableau des produits choisis
                    "poids_total": (lignes_valides['poids_fixe_carton'] * lignes_valides['Quantité Cible (Cartons)']).sum()
                }
                st.session_state.panier_production.append(commande_temp)
                st.success(f"Commande {choix_client} ajoutée à la liste (à droite) !")

# --- COLONNE DROITE : RÉCAPITULATIF ET VALIDATION ---
with col_review:
    st.subheader("📋 Récapitulatif de la journée")
    
    if not st.session_state.panier_production:
        st.info("Le planning est vide. Ajoutez des commandes à gauche.")
    else:
        # Affichage du panier
        total_jour_kg = 0
        
        for i, item in enumerate(st.session_state.panier_production):
            total_jour_kg += item['poids_total']
            with st.expander(f"📍 {item['client_nom']} - {item['poids_total']} kg", expanded=False):
                st.dataframe(item['produits'][['designation', 'Quantité Cible (Cartons)']], hide_index=True)
                if st.button(f"🗑️ Supprimer", key=f"del_{i}"):
                    st.session_state.panier_production.pop(i)
                    st.rerun()

        st.divider()
        st.metric("TOTAL JOURNÉE À PRODUIRE", f"{total_jour_kg} kg")
        
        col_pdf, col_send = st.columns(2)
        
        # BOUTON 1 : PDF
        pdf_bytes = create_pdf(date_str, st.session_state.panier_production)
        col_pdf.download_button(
            label="📄 TÉLÉCHARGER LE PDF",
            data=pdf_bytes,
            file_name=f"Planning_Production_{date_str.replace('/','-')}.pdf",
            mime='application/pdf',
            type="secondary"
        )
        
        # BOUTON 2 : ENVOI EN PROD
        if col_send.button("🚀 VALIDER & ENVOYER EN PROD", type="primary"):
            try:
                barre = st.progress(0)
                nb_cmds = len(st.session_state.panier_production)
                
                for idx, item in enumerate(st.session_state.panier_production):
                    # 1. Créer la commande dans Supabase
                    new_cmd = {
                        "client_id": item['client_id'],
                        "reference_interne": item['ref_commande'],
                        "statut": "EN_COURS",
                        "objectif_kg": float(item['poids_total'])
                        # "created_at" sera automatique ou on peut forcer la date_prod
                    }
                    res = supabase.table('commandes').insert(new_cmd).execute()
                    cmd_id = res.data[0]['id']
                    
                    # 2. Créer les lignes
                    lignes_data = []
                    for _, row in item['produits'].iterrows():
                        lignes_data.append({
                            "commande_id": cmd_id,
                            "produit_id": row['id'],
                            "quantite_cible_cartons": int(row['Quantité Cible (Cartons)'])
                        })
                    supabase.table('ligne_commandes').insert(lignes_data).execute()
                    
                    # Update barre progression
                    barre.progress((idx + 1) / nb_cmds)
                
                st.success("✅ TOUTES LES COMMANDES ONT ÉTÉ ENVOYÉES AUX TABLETTES !")
                st.session_state.panier_production = [] # On vide le panier
                time.sleep(2)
                st.rerun()
                
            except Exception as e:
                st.error(f"Erreur lors de l'envoi : {e}")

# --- BOUTON DE VIDAGE D'URGENCE ---
st.sidebar.markdown("---")
if st.sidebar.button("⚠️ Vider tout le panier"):
    st.session_state.panier_production = []
    st.rerun()

