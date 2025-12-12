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
        pdf.cell(30, 8, "Obj (KG)", 1)
        pdf.cell(30, 8, "Colis", 1)
        pdf.ln()
        pdf.set_font("Arial", '', 10)
        for _, row in produits.iterrows():
            pdf.cell(100, 8, str(row['designation'])[:45], 1)
            pdf.cell(30, 8, str(row['Objectif KG']), 1)
            pdf.cell(30, 8, str(row['nb_cartons']), 1)
            pdf.ln()
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

st.title("⚙️ GESTION & PLANIFICATION")

tab1, tab2, tab3, tab4 = st.tabs(["👥 CLIENTS", "📅 PLANIFICATION", "📜 HISTORIQUE", "📦 PRODUITS"])

# ==============================================================================
# ONGLET 1 : CLIENTS
# ==============================================================================
with tab1:
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("add_cli"):
            nom_cli = st.text_input("Nouveau Client").upper()
            if st.form_submit_button("Ajouter"):
                if nom_cli:
                    supabase.table('clients').insert({"nom": nom_cli}).execute()
                    st.rerun()
    with c2:
        clients = supabase.table('clients').select("*").order('nom').execute().data
        if clients:
            for c in clients:
                col_a, col_b = st.columns([4, 1])
                col_a.write(f"**{c['nom']}**")
                if col_b.button("🗑️", key=f"d_c_{c['id']}"):
                    try:
                        supabase.table('clients').delete().eq('id', c['id']).execute()
                        st.rerun()
                    except: st.error("Impossible (Utilisé).")

# ==============================================================================
# ONGLET 2 : PLANIFICATION
# ==============================================================================
with tab2:
    st.sidebar.header("Planning")
    date_prod = st.sidebar.date_input("Date", value=datetime.now())
    date_str = date_prod.strftime("%d/%m/%y")
    
    col_L, col_R = st.columns([1.2, 1])
    
    with col_L:
        st.subheader("1. Saisie Commande")
        clis = supabase.table('clients').select("*").execute().data
        prods = supabase.table('produits').select("*").execute().data
        
        if clis and prods:
            d_clis = {c['nom']: c['id'] for c in clis}
            choix_cli = st.selectbox("Client", list(d_clis.keys()))
            ref = f"CMD-{choix_cli}-{date_str}"
            
            df_p = pd.DataFrame(prods)
            if "Objectif KG" not in df_p.columns: df_p['Objectif KG'] = 0.0
            
            ed = st.data_editor(
                df_p[['id', 'designation', 'poids_fixe_carton', 'Objectif KG']],
                key=f"ed_{choix_cli}",
                column_config={"id": None, "poids_fixe_carton": st.column_config.NumberColumn("Poids/Colis", disabled=True)},
                hide_index=True, use_container_width=True, height=300
            )
            
            if st.button("➕ Ajouter au Panier"):
                sel = ed[ed['Objectif KG'] > 0].copy()
                if not sel.empty:
                    sel['nb_cartons'] = sel.apply(lambda x: math.ceil(x['Objectif KG']/x['poids_fixe_carton']), axis=1)
                    tot = (sel['nb_cartons']*sel['poids_fixe_carton']).sum()
                    st.session_state.panier_production.append({
                        "client_nom": choix_cli, "client_id": d_clis[choix_cli],
                        "ref_commande": ref, "date_prod": date_prod.strftime("%Y-%m-%d"),
                        "produits": sel, "poids_total": tot
                    })
                    st.success("Ajouté !")

    with col_R:
        st.subheader("2. Panier")
        if st.session_state.panier_production:
            total_G = 0
            to_del = []
            for i, it in enumerate(st.session_state.panier_production):
                total_G += it['poids_total']
                with st.expander(f"{it['client_nom']} ({it['poids_total']} kg)"):
                    st.dataframe(it['produits'][['designation', 'nb_cartons']], hide_index=True)
                    if st.button("Supprimer", key=f"r_{i}"): to_del.append(i)
            
            if to_del:
                for x in sorted(to_del, reverse=True): del st.session_state.panier_production[x]
                st.rerun()

            st.metric("TOTAL", f"{total_G} kg")
            c_pdf, c_go = st.columns(2)
            pdf = create_pdf(date_str, st.session_state.panier_production)
            c_pdf.download_button("📄 PDF", pdf, "Prod.pdf", "application/pdf")
            
            if c_go.button("🚀 VALIDER", type="primary"):
                bar = st.progress(0)
                for idx, it in enumerate(st.session_state.panier_production):
                    res = supabase.table('commandes').insert({
                        "client_id": it['client_id'], "reference_interne": it['ref_commande'],
                        "statut": "EN_COURS", "objectif_kg": float(it['poids_total']),
                        "created_at": f"{it['date_prod']} 08:00:00"
                    }).execute()
                    cid = res.data[0]['id']
                    ligs = []
                    for _, r in it['produits'].iterrows():
                        ligs.append({"commande_id": cid, "produit_id": r['id'], "quantite_cible_cartons": int(r['nb_cartons'])})
                    supabase.table('ligne_commandes').insert(ligs).execute()
                    bar.progress((idx+1)/len(st.session_state.panier_production))
                st.session_state.panier_production = []
                st.success("Envoyé !")
                st.rerun()

# ==============================================================================
# ONGLET 3 : HISTORIQUE
# ==============================================================================
with tab3:
    st.header("Historique")
    # ... (Code identique à avant, simplifié pour la place) ...
    # Je garde la logique de modification/suppression
    filtre = st.date_input("Date", value=datetime.now(), key="h_d")
    try:
        raw_cmds = supabase.table('commandes').select("*").order('created_at', desc=True).limit(20).execute().data
        if raw_cmds:
            for c in raw_cmds:
                if str(filtre) == c['created_at'].split('T')[0]:
                    with st.expander(f"{c['reference_interne']} - {c['statut']}"):
                        k = c['id']
                        ns = st.selectbox("Statut", ["EN_COURS","PAUSE","TERMINE"], key=f"s{k}", index=["EN_COURS","PAUSE","TERMINE"].index(c['statut']))
                        if st.button("Update", key=f"u{k}"):
                            supabase.table('commandes').update({"statut": ns}).eq('id', k).execute()
                            st.rerun()
                        if st.button("🗑️ Delete", key=f"d{k}"):
                            supabase.table('scans').delete().eq('commande_id', k).execute()
                            supabase.table('ligne_commandes').delete().eq('commande_id', k).execute()
                            supabase.table('commandes').delete().eq('id', k).execute()
                            st.rerun()
    except: pass

# ==============================================================================
# ONGLET 4 : PRODUITS (IMPORT EXCEL AJOUTÉ)
# ==============================================================================
# ==============================================================================
# ONGLET 4 : PRODUITS (VERSION INTELLIGENTE "ÉCRASE SI EXISTE")
# ==============================================================================
with tab4:
    st.header("📦 Base Articles")
    
    col_man, col_imp = st.columns(2)
    
    # --- 1. AJOUT MANUEL ---
    with col_man:
        st.subheader("1. Ajout Manuel")
        with st.form("manual_prod"):
            des = st.text_input("Désignation").upper()
            code = st.text_input("Code Barre")
            poids = st.number_input("Poids (kg)", min_value=0.1, step=0.1)
            if st.form_submit_button("Ajouter / Mettre à jour"):
                if des and code:
                    try:
                        # Même logique ici : On vérifie si ça existe
                        exist = supabase.table('produits').select("id").eq('dun14_carton', code).execute()
                        
                        data = {"designation": des, "dun14_carton": code, "poids_fixe_carton": poids}
                        
                        if exist.data:
                            # MISE A JOUR
                            pid = exist.data[0]['id']
                            supabase.table('produits').update(data).eq('id', pid).execute()
                            st.success(f"Produit '{des}' mis à jour !")
                        else:
                            # CREATION
                            supabase.table('produits').insert(data).execute()
                            st.success(f"Produit '{des}' créé !")
                        
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Erreur : {e}")

    # --- 2. IMPORT EXCEL MASSIF (LOGIQUE MODIFIÉE) ---
    with col_imp:
        st.subheader("2. Import Excel Massif")
        st.info("Colonnes requises : 'Article', 'Code', 'Poids'")
        st.caption("ℹ️ Si un code barre existe déjà, l'article sera mis à jour (écrasé).")
        
        uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['xlsx'])
        
        if uploaded_file:
            try:
                df_excel = pd.read_excel(uploaded_file)
                required_cols = ['Article', 'Code', 'Poids']
                
                if not set(required_cols).issubset(df_excel.columns):
                    st.error(f"Erreur colonnes ! Il faut : {required_cols}")
                else:
                    st.write("Aperçu :")
                    st.dataframe(df_excel.head(3), hide_index=True)
                    
                    if st.button("🚀 LANCER L'IMPORTATION", type="primary"):
                        progress_bar = st.progress(0)
                        created_count = 0
                        updated_count = 0
                        total_rows = len(df_excel)
                        
                        for index, row in df_excel.iterrows():
                            # Nettoyage des données
                            code_clean = str(row['Code']).replace('.0', '').strip()
                            nom_clean = str(row['Article']).upper().strip()
                            poids_clean = float(row['Poids'])
                            
                            prod_data = {
                                "designation": nom_clean,
                                "dun14_carton": code_clean,
                                "poids_fixe_carton": poids_clean
                            }
                            
                            try:
                                # 1. On vérifie si ce code barre existe déjà
                                check = supabase.table('produits').select("id").eq('dun14_carton', code_clean).execute()
                                
                                if check.data:
                                    # IL EXISTE -> ON ÉCRASE (UPDATE)
                                    id_exist = check.data[0]['id']
                                    supabase.table('produits').update(prod_data).eq('id', id_exist).execute()
                                    updated_count += 1
                                else:
                                    # IL N'EXISTE PAS -> ON CRÉE (INSERT)
                                    supabase.table('produits').insert(prod_data).execute()
                                    created_count += 1
                                    
                            except Exception as e:
                                st.error(f"Erreur ligne {index}: {e}")
                            
                            progress_bar.progress((index + 1) / total_rows)
                            
                        st.success(f"Terminé ! ✅ {created_count} créés, 🔄 {updated_count} mis à jour.")
                        time.sleep(2)
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Erreur fichier : {e}")

    st.divider()
    st.subheader("Liste actuelle")
    all_p = supabase.table('produits').select("*").order('designation').execute().data
    if all_p:
        st.dataframe(pd.DataFrame(all_p)[['designation', 'dun14_carton', 'poids_fixe_carton']], use_container_width=True)
