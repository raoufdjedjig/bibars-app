import streamlit as st
import pandas as pd
import math
import time
from datetime import datetime
from fpdf import FPDF
from supabase import create_client
# ... autres imports ...


# --- TES CLÉS ---
SUPABASE_URL = "https://ywrdmbqoczqorqeeyzeu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3cmRtYnFvY3pxb3JxZWV5emV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MzYyNzEsImV4cCI6MjA4MTAxMjI3MX0.C7zoaY4iwWTJlqttiYv0M66KLWmpu1_Xn7zl5gWcYKk"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

st.set_page_config(page_title="ADMINISTRATION", page_icon="⚙️", layout="wide")

if 'panier_production' not in st.session_state:
    st.session_state.panier_production = []

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
        pdf.cell(30, 8, "Type", 1)
        pdf.ln()
        pdf.set_font("Arial", '', 10)
        for _, row in produits.iterrows():
            pdf.cell(100, 8, str(row['designation'])[:40], 1)
            pdf.cell(30, 8, str(row['Objectif KG']), 1)
            pdf.cell(30, 8, str(row['type_emballage']), 1)
            pdf.ln()
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

st.title("⚙️ GESTION & PLANIFICATION WMS")

tab1, tab2, tab3, tab4 = st.tabs(["👥 CLIENTS", "📅 PLANIFICATION", "📜 HISTORIQUE", "📦 PRODUITS"])

# ==============================================================================
# TAB 1 : CLIENTS
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
# TAB 2 : PLANIFICATION
# ==============================================================================
with tab2:
    st.sidebar.header("Planning")
    date_prod = st.sidebar.date_input("Date", value=datetime.now())
    date_str = date_prod.strftime("%d/%m/%y")
    
    col_L, col_R = st.columns([1.2, 1])
    
    with col_L:
        st.subheader("1. Saisie")
        clis = supabase.table('clients').select("*").execute().data
        prods = supabase.table('produits').select("*").order('designation').execute().data
        
        if clis and prods:
            d_clis = {c['nom']: c['id'] for c in clis}
            choix_cli = st.selectbox("Client", list(d_clis.keys()))
            ref = f"CMD-{choix_cli}-{date_str}"
            
            df_p = pd.DataFrame(prods)
            if "Objectif KG" not in df_p.columns: df_p['Objectif KG'] = 0.0
            
            ed = st.data_editor(
                df_p[['id', 'designation', 'type_emballage', 'poids_fixe_carton', 'Objectif KG']],
                key=f"ed_{choix_cli}",
                column_config={
                    "id": None, 
                    "poids_fixe_carton": st.column_config.NumberColumn("Kg/Colis", disabled=True),
                    "type_emballage": st.column_config.TextColumn("Type", disabled=True),
                    "Objectif KG": st.column_config.NumberColumn("Obj (KG)", min_value=0)
                },
                hide_index=True, use_container_width=True, height=350
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
        st.subheader("2. Validation & Palettes")
        if st.session_state.panier_production:
            for i, it in enumerate(st.session_state.panier_production):
                with st.expander(f"{it['client_nom']} ({it['poids_total']} kg)"):
                    st.dataframe(it['produits'][['designation', 'type_emballage', 'nb_cartons']], hide_index=True)
                    if st.button("Supprimer", key=f"r_{i}"):
                        del st.session_state.panier_production[i]
                        st.rerun()
            
            if st.button("🚀 VALIDER & GÉNÉRER PALETTES", type="primary"):
                bar = st.progress(0)
                for idx, item in enumerate(st.session_state.panier_production):
                    res = supabase.table('commandes').insert({
                        "client_id": item['client_id'], "reference_interne": item['ref_commande'],
                        "statut": "EN_COURS", "objectif_kg": float(item['poids_total']),
                        "created_at": f"{item['date_prod']} 08:00:00"
                    }).execute()
                    cid = res.data[0]['id']
                    
                    ligs = []
                    for _, r in item['produits'].iterrows():
                        ligs.append({"commande_id": cid, "produit_id": r['id'], "quantite_cible_cartons": int(r['nb_cartons'])})
                    supabase.table('ligne_commandes').insert(ligs).execute()
                    
                    # CALCUL PALETTES
                    grouped = item['produits'].groupby('type_emballage')['Objectif KG'].sum()
                    palette_counter = 1
                    palettes_data = []
                    
                    for type_emb, poids_total in grouped.items():
                        if type_emb == 'SOUS_VIDE': poids_max = 800
                        elif type_emb == 'MAP': poids_max = 600
                        elif type_emb == 'VRAC': poids_max = 600
                        else: poids_max = 600 

                        nb_palettes_estime = math.ceil(poids_total / poids_max)
                        for _ in range(nb_palettes_estime):
                            palettes_data.append({
                                "commande_id": cid, "numero": palette_counter, "type_emballage": type_emb
                            })
                            palette_counter += 1
                    
                    if palettes_data:
                        supabase.table('palettes').insert(palettes_data).execute()

                    bar.progress((idx+1)/len(st.session_state.panier_production))
                
                st.session_state.panier_production = []
                st.success("✅ Commandes envoyées + Palettes calculées !")
                time.sleep(2)
                st.rerun()

# ==============================================================================
# TAB 3 : HISTORIQUE
# ==============================================================================
with tab3:
    st.header("Historique")
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
                            supabase.table('palettes').delete().eq('commande_id', k).execute()
                            supabase.table('ligne_commandes').delete().eq('commande_id', k).execute()
                            supabase.table('commandes').delete().eq('id', k).execute()
                            st.rerun()
    except: pass

# ==============================================================================
# TAB 4 : PRODUITS
# ==============================================================================
with tab4:
    st.header("📦 Base Articles")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Ajout Manuel")
        with st.form("prod_form"):
            des = st.text_input("Désignation").upper()
            code = st.text_input("Code Barre")
            poids = st.number_input("Poids (kg)", step=0.1)
            type_emb = st.selectbox("Type", ["MAP", "SOUS_VIDE", "VRAC", "AUTRE"])
            
            if st.form_submit_button("Sauvegarder"):
                if des and code:
                    try:
                        data = {"designation": des, "dun14_carton": code, "poids_fixe_carton": poids, "type_emballage": type_emb}
                        exist = supabase.table('produits').select("id").eq('dun14_carton', code).execute()
                        if exist.data:
                            supabase.table('produits').update(data).eq('id', exist.data[0]['id']).execute()
                        else:
                            supabase.table('produits').insert(data).execute()
                        st.success("OK")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Erreur: {e}")
                    
    with c2:
        st.subheader("Import Excel")
        up = st.file_uploader("Fichier Excel", type=['xlsx'])
        if up:
            try:
                df = pd.read_excel(up)
                if st.button("🚀 LANCER L'IMPORTATION"):
                    bar = st.progress(0)
                    for idx, r in df.iterrows():
                        try:
                            t = r['Type'] if 'Type' in df.columns else 'MAP'
                            d = {
                                "designation": str(r['Article']).upper().strip(), 
                                "dun14_carton": str(r['Code']).replace('.0','').strip(), 
                                "poids_fixe_carton": float(r['Poids']), 
                                "type_emballage": str(t).upper().strip()
                            }
                            ex = supabase.table('produits').select("id").eq('dun14_carton', d['dun14_carton']).execute()
                            if ex.data: supabase.table('produits').update(d).eq('id', ex.data[0]['id']).execute()
                            else: supabase.table('produits').insert(d).execute()
                        except: pass
                        bar.progress((idx+1)/len(df))
                    st.success("Terminé !")
                    time.sleep(2)
                    st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")
            
    st.divider()
    all_p = supabase.table('produits').select("*").order('designation').execute().data
    if all_p:
        st.dataframe(pd.DataFrame(all_p)[['designation', 'dun14_carton', 'poids_fixe_carton', 'type_emballage']], use_container_width=True)


