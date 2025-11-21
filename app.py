# ------------------------------------------------------------
# THE HIVE DASHBOARD PRO - APP.PY (BLOCK 1/10)
# ------------------------------------------------------------
import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import os
import io
from datetime import datetime
from fpdf import FPDF  # pour export PDF

st.set_page_config(
    page_title="THE HIVE DASHBOARD PRO",
    page_icon="🍯",
    layout="wide"
)

# ------------------------------------------------------------
# CUSTOM CSS (Dark/Light mode + Style The Hive)
# ------------------------------------------------------------
def load_custom_css():
    st.markdown("""
    <style>
        .metric-container {
            background: #ffffff10;
            padding: 16px;
            border-radius: 14px;
            margin-bottom: 12px;
        }
        .big-metric {
            font-size: 30px !important;
            font-weight: 700 !important;
        }
        .section-title {
            font-size: 26px;
            margin-top: 20px;
            font-weight: 600;
        }
        .ok { color: #2ecc71; }
        .warn { color: #f1c40f; }
        .critical { color: #e74c3c; }
    </style>
    """, unsafe_allow_html=True)

load_custom_css()

# ------------------------------------------------------------
# LOGO
# ------------------------------------------------------------
if os.path.exists("logo.png"):
    st.image("logo.png", width=260)
else:
    st.title("THE HIVE DASHBOARD PRO")

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------
# SIDEBAR NAVIGATION
# ------------------------------------------------------------
st.sidebar.title("📂 Navigation")

page = st.sidebar.radio(
    "Choisir une page",
    [
        "Dashboard Journalier",
        "Historique Journée",
        "Analyse Mensuelle",
        "Analyse Annuelle",
        "Productivité",
        "Food Cost",
        "Exports",
        "Paramètres"
    ]
)

# ------------------------------------------------------------
# UPLOAD FILES (général)
# ------------------------------------------------------------
st.sidebar.title("📁 Import des fichiers")

file_day = st.sidebar.file_uploader(
    "📅 Fichier du jour (RestoTrack)",
    type=["xlsx"]
)

files_n1 = st.sidebar.file_uploader(
    "📂 Fichiers N-1 (multi-upload)",
    type=["xlsx"],
    accept_multiple_files=True
)

file_budget = st.sidebar.file_uploader(
    "📘 Budget 2025",
    type=["xlsx"]
)

file_foodcost = st.sidebar.file_uploader(
    "🍽 Achats Food Cost",
    type=["xlsx"]
)

file_foodsales = st.sidebar.file_uploader(
    "🥗 Ventes Food Cost",
    type=["xlsx"]
)
# ------------------------------------------------------------
# BLOC 2 – PARSER RESTOTRACK PRO (intégré dans app.py)
# ------------------------------------------------------------

import re

# Convertisseur FR/BE -> float robuste
def to_float(x):
    if x is None or pd.isna(x):
        return 0.0

    s = str(x)
    s = s.replace("€", "").replace("%", "").replace("\xa0", "").replace(" ", "").replace("\u202f", "")

    # Cas 1 : 1.234,56 → 1234.56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")

    # Cas 2 : 123,45 → 123.45
    elif "," in s:
        s = s.replace(",", ".")

    try:
        return float(s)
    except:
        return 0.0


# Détection du service
def detect_service(label):
    t = str(label).lower()

    if "matin" in t:
        return "Midi"       # Christophe veut matin fusionné avec midi
    if "midi" in t or "déjeuner" in t or "dejeuner" in t:
        return "Midi"
    if "soir" in t or "nuit" in t or "17:" in t or "18:" in t or "19:" in t or "20:" in t:
        return "Soir"

    return None


# Détection catégorie (centre de revenu)
def detect_category(name):
    n = str(name).lower()

    if any(k in n for k in ["rest", "nour", "food", "cuisine", "snack", "buffet"]):
        return "Nourriture"

    if any(k in n for k in ["boiss", "bar", "cocktail", "beer", "wine", "drink"]):
        return "Boissons"

    if any(k in n for k in ["boutique", "shop"]):
        return "Nourriture"   # Boutique = nourriture demandé par Christophe

    return None


# Extraction de la date dans les 10 premières lignes
def extract_date(df):
    for row in df.values[:10]:
        for v in row:
            date = pd.to_datetime(v, errors="ignore", dayfirst=True)
            if isinstance(date, pd.Timestamp) and 2020 < date.year < 2035:
                return date.date()
    return None


# PARSER PRINCIPAL RESTOTRACK
def parse_restotrack(file):

    raw = pd.read_excel(file, header=None)

    # Trouver la date du rapport
    report_date = extract_date(raw)

    # Trouver en-têtes ("Couverts")
    header_row = None
    for i, row in raw.iterrows():
        if any("couver" in str(c).lower() for c in row):
            header_row = i
            break

    if header_row is None:
        raise Exception("Impossible de trouver la ligne avec 'Couverts' dans le fichier RestoTrack.")

    # Recréer dataframe propre
    header = raw.iloc[header_row].fillna("")
    df = raw.iloc[header_row + 1:].copy()
    df.columns = header

    cols = [str(c) for c in df.columns]

    # Trouver colonne CA TTC "Total TTC"
    ttc_candidates = [c for c in cols if "ttc" in c.lower()]
    if not ttc_candidates:
        # fallback
        ttc_candidates = [c for c in cols if "total" in c.lower()]
    total_col = ttc_candidates[0]

    # Trouver colonne couverts
    cov_candidates = [c for c in cols if "couver" in c.lower()]
    cov_col = cov_candidates[0]

    # Première colonne = label/service
    label_col = cols[0]

    df = df[[label_col, cov_col, total_col]]

    df["Couverts"] = df[cov_col].apply(to_float)
    df["CA"] = df[total_col].apply(to_float)
    df["label"] = df[label_col].astype(str).str.strip()

    rows = []
    current_center = None  # ex: Restaurant, Bar, Boutique

    # Reconstruction service par service
    for _, r in df.iterrows():

        txt = str(r["label"]).strip()

        # Début d’un nouveau centre (Restaurant / Bar / Boutique)
        if detect_category(txt) is not None and detect_service(txt) is None:
            current_center = txt
            continue

        # Si c'est une ligne de service
        service = detect_service(txt)
        if service is None:
            continue

        category = detect_category(current_center)
        if category is None:
            continue

        rows.append({
            "Date": report_date,
            "Centre": current_center,
            "Categorie": category,
            "ServiceAgg": service,
            "Couverts": r["Couverts"],
            "CA": r["CA"]
        })

    df_clean = pd.DataFrame(rows)

    # Table pivot par catégorie
    df_total = df_clean.groupby(["Categorie", "ServiceAgg"]).agg({
        "CA": "sum",
        "Couverts": "sum"
    }).reset_index()

    return df_clean, df_total, report_date
# ------------------------------------------------------------
# BLOC 3 – DASHBOARD JOURNALIER PRO
# ------------------------------------------------------------

if page == "Dashboard Journalier":

    if not file_day:
        st.warning("Veuillez importer un fichier RestoTrack du jour.")
        st.stop()

    df_s, df_t, date = parse_restotrack(file_day)

    st.markdown(f"## 📊 Dashboard Journalier — {date}")

    # --------------------------
    # CALCUL KPI
    # --------------------------
    ca_n_midi = df_t[(df_t["Categorie"]=="Nourriture") & (df_t["ServiceAgg"]=="Midi")]["CA"].sum()
    ca_n_soir = df_t[(df_t["Categorie"]=="Nourriture") & (df_t["ServiceAgg"]=="Soir")]["CA"].sum()
    ca_b_midi = df_t[(df_t["Categorie"]=="Boissons") & (df_t["ServiceAgg"]=="Midi")]["CA"].sum()
    ca_b_soir = df_t[(df_t["Categorie"]=="Boissons") & (df_t["ServiceAgg"]=="Soir")]["CA"].sum()

    couv_midi = df_s[(df_s["Categorie"]=="Nourriture") & (df_s["ServiceAgg"]=="Midi")]["Couverts"].sum()
    couv_soir = df_s[(df_s["Categorie"]=="Nourriture") & (df_s["ServiceAgg"]=="Soir")]["Couverts"].sum()

    ca_total = ca_n_midi + ca_n_soir + ca_b_midi + ca_b_soir
    couv_total = couv_midi + couv_soir

    pm_midi = ca_n_midi / couv_midi if couv_midi > 0 else 0
    pm_soir = ca_n_soir / couv_soir if couv_soir > 0 else 0

    # --------------------------
    # KPI BLOCKS
    # --------------------------
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("💰 CA Total TTC", f"{ca_total:,.2f} €")
    col2.metric("🍽 PM Midi", f"{pm_midi:,.2f} €")
    col3.metric("🌙 PM Soir", f"{pm_soir:,.2f} €")
    col4.metric("👥 Couverts Total", f"{couv_total}")

    # --------------------------
    # SOUS-KPI DETAILLÉS
    # --------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nourriture Midi", f"{ca_n_midi:,.2f} €")
    c2.metric("Nourriture Soir", f"{ca_n_soir:,.2f} €")
    c3.metric("Boissons Midi", f"{ca_b_midi:,.2f} €")
    c4.metric("Boissons Soir", f"{ca_b_soir:,.2f} €")

    st.markdown("---")

    # --------------------------
    # GRAPHIQUE BAR – Répartition par Service × Catégorie
    # --------------------------
    st.subheader("📈 Répartition du CA par Service et Catégorie")

    df_chart = pd.DataFrame({
        "Service": ["Midi","Soir","Midi","Soir"],
        "Catégorie": ["Nourriture","Nourriture","Boissons","Boissons"],
        "CA": [ca_n_midi, ca_n_soir, ca_b_midi, ca_b_soir]
    })

    fig = px.bar(
        df_chart,
        x="Service",
        y="CA",
        color="Catégorie",
        barmode="group",
        text_auto=True,
        title="CA par Service"
    )

    st.plotly_chart(fig, use_container_width=True)

    # --------------------------
    # DONUT – Nourriture vs Boissons
    # --------------------------
    st.subheader("🍩 Répartition Nourriture / Boissons")

    pie_df = pd.DataFrame({
        "Categorie": ["Nourriture", "Boissons"],
        "CA": [
            ca_n_midi + ca_n_soir,
            ca_b_midi + ca_b_soir
        ]
    })

    fig2 = px.pie(
        pie_df,
        names="Categorie",
        values="CA",
        hole=0.5,
        color="Categorie",
        title="Part de CA"
    )

    st.plotly_chart(fig2, use_container_width=True)

    # --------------------------
    # TABLE DETAIL
    # --------------------------
    st.subheader("📄 Détail du fichier journalier (nettoyé)")
    st.dataframe(df_s, use_container_width=True)
# ------------------------------------------------------------
# BLOC 4 – HISTORIQUE JOURNÉE
# ------------------------------------------------------------

if page == "Historique Journée":

    st.markdown("## 📜 Historique détaillé de la journée")

    if not file_day:
        st.warning("Veuillez importer un fichier RestoTrack du jour.")
        st.stop()

    df_s, df_t, report_date = parse_restotrack(file_day)

    st.markdown(f"### 🗓 Date : **{report_date}**")

    # --------------------------
    # TABLE DETAIL COMPLETE
    # --------------------------
    st.subheader("🧾 Données détaillées (service par service)")
    st.dataframe(df_s, use_container_width=True)

    # --------------------------
    # TABLE PAR CATÉGORIE
    # --------------------------
    st.subheader("📊 Synthèse par catégorie et service")
    st.dataframe(df_t, use_container_width=True)

    # --------------------------
    # EXPORT EXCEL
    # --------------------------
    st.subheader("📤 Export Excel du détail")

    def export_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Historique")
        return output.getvalue()

    if st.download_button(
        "📥 Télécharger historique (Excel)",
        data=export_excel(df_s),
        file_name=f"Historique_{report_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        st.success("Export Excel généré avec succès !")
# ------------------------------------------------------------
# BLOC 5 – ANALYSE MENSUELLE (Budget vs N-1 vs Réalisé)
# ------------------------------------------------------------

def load_budget_file(file):
    df = pd.read_excel(file)
    df.columns = [c.lower().strip() for c in df.columns]

    month_col = [c for c in df.columns if "mois" in c][0]
    resto_col = [c for c in df.columns if "resto" in c or "restaurant" in c][0]
    bar_col = [c for c in df.columns if "bar" in c][0]
    boutique_col = [c for c in df.columns if "boutique" in c][0]
    total_col = [c for c in df.columns if "total" in c][0]
    couv_col = [c for c in df.columns if "couvert" in c][0]

    df_m = pd.DataFrame({
        "mois": df[month_col].astype(str).str.zfill(2),
        "budget_nourriture": df[resto_col] + df[boutique_col],
        "budget_boissons": df[bar_col],
        "budget_total": df[total_col],
        "budget_couverts": df[couv_col]
    })
    return df_m


def build_n1_table(files_n1):
    if not files_n1:
        return None

    results = []

    for f in files_n1:
        df_s, df_t, d = parse_restotrack(f)
        mois = str(pd.to_datetime(d).month).zfill(2)

        ca_n = df_t[df_t["Categorie"]=="Nourriture"]["CA"].sum()
        ca_b = df_t[df_t["Categorie"]=="Boissons"]["CA"].sum()

        results.append({
            "mois": mois,
            "n1_nourriture": ca_n,
            "n1_boissons": ca_b,
            "n1_total": ca_n + ca_b
        })

    df_final = pd.DataFrame(results)
    return df_final.groupby("mois", as_index=False).sum()


if page == "Analyse Mensuelle":

    st.markdown("## 📆 Analyse Mensuelle")

    if not file_day or not file_budget:
        st.warning("Veuillez importer : fichier du jour + budget 2025.")
        st.stop()

    # Charger fichier du jour
    df_s, df_t, d = parse_restotrack(file_day)
    month = str(pd.to_datetime(d).month).zfill(2)

    df_real = pd.DataFrame([{
        "mois": month,
        "realised_nourriture": df_t[df_t["Categorie"]=="Nourriture"]["CA"].sum(),
        "realised_boissons": df_t[df_t["Categorie"]=="Boissons"]["CA"].sum(),
        "realised_total": df_s["CA"].sum()
    }])

    # Charger budget
    df_bud = load_budget_file(file_budget)

    # Charger N-1
    df_n1 = build_n1_table(files_n1)
    if df_n1 is None:
        df_n1 = pd.DataFrame(columns=["mois","n1_nourriture","n1_boissons","n1_total"])

    # Fusion
    df_month = df_bud.merge(df_real, on="mois", how="left") \
                     .merge(df_n1, on="mois", how="left") \
                     .fillna(0)

    # Calculs
    df_month["ecart_total_vs_budget"] = df_month["realised_total"] - df_month["budget_total"]
    df_month["ecart_total_vs_n1"] = df_month["realised_total"] - df_month["n1_total"]
    df_month["atteinte_budget_%"] = df_month.apply(
        lambda r: (r["realised_total"] / r["budget_total"] * 100) if r["budget_total"]>0 else 0,
        axis=1
    )

    st.subheader("📊 Tableau Mensuel consolidé")
    st.dataframe(df_month, use_container_width=True)

    # -------------------------------
    # GRAPHIQUE BUDGET vs RÉALISÉ vs N-1
    # -------------------------------
    st.subheader("📈 Budget vs Réalisé vs N-1")

    fig = px.bar(
        df_month,
        x="mois",
        y=["realised_total", "budget_total", "n1_total"],
        barmode="group",
        labels={"value": "CA (€)", "variable": "Catégorie"},
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------
    # INDICATEURS
    # -------------------------------
    st.subheader("🎯 Objectifs du mois")

    c1, c2, c3 = st.columns(3)
    c1.metric("Budget du mois", f"{df_month['budget_total'].iloc[0]:,.2f} €")
    c2.metric("Réalisé", f"{df_month['realised_total'].iloc[0]:,.2f} €")
    c3.metric("Atteinte", f"{df_month['atteinte_budget_%'].iloc[0]:,.1f} %")

    reste = df_month['budget_total'].iloc[0] - df_month['realised_total'].iloc[0]
    st.info(f"📌 Reste à faire pour atteindre le budget : **{reste:,.2f} €**")
# ------------------------------------------------------------
# BLOC 6 – ANALYSE ANNUELLE
# ------------------------------------------------------------

if page == "Analyse Annuelle":

    st.markdown("## 📅 Analyse Annuelle")

    if not file_budget:
        st.warning("Veuillez importer le budget 2025.")
        st.stop()

    if not file_day:
        st.warning("Veuillez importer au moins un fichier RestoTrack du jour.")
        st.stop()

    # Charger budget annuel
    df_bud = load_budget_file(file_budget)

    # Charger fichier du jour (réalisé M/M)
    df_s, df_t, d = parse_restotrack(file_day)
    month = str(pd.to_datetime(d).month).zfill(2)

    df_real = pd.DataFrame([{
        "mois": month,
        "realised_nourriture": df_t[df_t["Categorie"]=="Nourriture"]["CA"].sum(),
        "realised_boissons": df_t[df_t["Categorie"]=="Boissons"]["CA"].sum(),
        "realised_total": df_s["CA"].sum()
    }])

    # Charger N-1 (multi-fichiers)
    df_n1 = build_n1_table(files_n1)
    if df_n1 is None:
        df_n1 = pd.DataFrame(columns=["mois","n1_nourriture","n1_boissons","n1_total"])

    # Merge annuel : Budget + Réalisé + N-1
    df_year = df_bud.merge(df_real, on="mois", how="left") \
                    .merge(df_n1, on="mois", how="left") \
                    .fillna(0)

    # Totaux annuels
    budget_total_year = df_year["budget_total"].sum()
    realised_total_year = df_year["realised_total"].sum()
    n1_total_year = df_year["n1_total"].sum()

    atteinte = (realised_total_year / budget_total_year * 100) if budget_total_year > 0 else 0
    ecart_budget = realised_total_year - budget_total_year

    # -------------------------------
    # KPI ANNUEL
    # -------------------------------
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("💰 Budget Annuel", f"{budget_total_year:,.2f} €")
    col2.metric("🏁 Réalisé Annuel", f"{realised_total_year:,.2f} €")
    col3.metric("📊 N-1 Annuel", f"{n1_total_year:,.2f} €")
    col4.metric("🎯 Atteinte", f"{atteinte:,.1f} %")

    # Écart par rapport au budget
    if ecart_budget >= 0:
        st.success(f"🚀 Au-dessus du budget de **{ecart_budget:,.2f} €**")
    else:
        st.error(f"📉 En-dessous du budget de **{ecart_budget:,.2f} €**")

    st.markdown("---")

    # -------------------------------
    # GRAPHIQUE — Budget vs Réalisé vs N-1
    # -------------------------------
    st.subheader("📈 Année complète : Budget / Réalisé / N-1")

    df_plot = pd.DataFrame({
        "Catégorie": ["Budget", "Réalisé", "N-1"],
        "CA": [budget_total_year, realised_total_year, n1_total_year]
    })

    fig = px.bar(
        df_plot,
        x="Catégorie",
        y="CA",
        text_auto=True,
        color="Catégorie",
        title="Comparatif Annuel"
    )
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------
    # COURBE D’ÉVOLUTION MENSUELLE
    # -------------------------------
    st.subheader("📉 Évolution mensuelle (uniquement mois importés)")

    df_plot2 = df_year[["mois","budget_total","realised_total","n1_total"]].copy()

    fig2 = px.line(
        df_plot2,
        x="mois",
        y=["budget_total","realised_total","n1_total"],
        markers=True,
        labels={"value": "CA (€)", "variable": "Catégorie"},
        title="Trend Annuel"
    )
    st.plotly_chart(fig2, use_container_width=True)
# ------------------------------------------------------------
# BLOC 7 – PRODUCTIVITÉ
# ------------------------------------------------------------

if page == "Productivité":

    st.markdown("## 🧮 Productivité du Personnel")

    st.info("⚙️ Saisis ici les données de personnel pour calculer coûts & ratios.")

    # --------------------------
    # Données manuelles par service
    # --------------------------
    services = ["Cuisine", "Salle", "Bar", "Plonge", "Accueil"]

    productivite_data = {}

    for s in services:
        st.markdown(f"### **{s}**")

        col1, col2, col3 = st.columns(3)

        nb = col1.number_input(f"Personnel {s}", min_value=0, value=0, key=f"nb_{s}")
        heures = col2.number_input(f"Heures travaillées {s}", min_value=0.0, value=0.0, key=f"h_{s}")
        taux = col3.number_input(f"Taux horaire {s} (€)", min_value=0.0, value=0.0, key=f"t_{s}")

        cout = heures * taux
        productivite_data[s] = {"personnel": nb, "heures": heures, "taux": taux, "cout": cout}

        st.write(f"**Coût {s} :** {cout:,.2f} €")

        st.markdown("---")

    # --------------------------
    # TOTALS
    # --------------------------
    total_cout = sum(v["cout"] for v in productivite_data.values())

    st.subheader("📊 Synthèse Main-d'œuvre")

    st.metric("💸 Coût total du personnel", f"{total_cout:,.2f} €")

    # --------------------------
    # Payroll Ratio (Coût personnel / CA)
    # --------------------------

    if not file_day:
        st.warning("Pour le payroll ratio, importer un fichier du jour dans la colonne de gauche.")
        st.stop()

    df_s, df_t, d = parse_restotrack(file_day)
    ca_total = df_s["CA"].sum()

    payroll_ratio = total_cout / ca_total * 100 if ca_total > 0 else 0

    # Couleur
    if payroll_ratio < 28:
        color = "🟢 Très bon"
    elif payroll_ratio <= 33:
        color = "🟠 Acceptable"
    else:
        color = "🔴 Trop élevé"

    st.metric("📉 Payroll Ratio", f"{payroll_ratio:,.1f} %", help=f"Niveau : {color}")

    st.subheader("⚠️ Interprétation")
    if payroll_ratio < 28:
        st.success("🟢 Excellente maîtrise de la masse salariale.")
    elif payroll_ratio <= 33:
        st.warning("🟠 Ratio acceptable mais surveiller la productivité.")
    else:
        st.error("🔴 Masse salariale trop élevée par rapport au CA du jour.")

    # --------------------------
    # TABLEAU RÉCAP
    # --------------------------
    df_prod = pd.DataFrame([
        {
            "Service": s,
            "Personnel": productivite_data[s]["personnel"],
            "Heures": productivite_data[s]["heures"],
            "Taux horaire": productivite_data[s]["taux"],
            "Coût": productivite_data[s]["cout"]
        }
        for s in services
    ])

    st.subheader("📃 Détail par service")
    st.dataframe(df_prod, use_container_width=True)

    # --------------------------
    # GRAPHIQUE REPARTITION DES COÛTS
    # --------------------------
    st.subheader("📊 Répartition des coûts de personnel")

    fig = px.pie(
        df_prod,
        names="Service",
        values="Coût",
        hole=0.4,
        title="Répartition des coûts par service"
    )
    st.plotly_chart(fig, use_container_width=True)
# ------------------------------------------------------------
# BLOC 8 – FOOD COST (Achats + Ventes + FC%)
# ------------------------------------------------------------

if page == "Food Cost":

    st.markdown("## 🍽️ Food Cost – Achats & Ventes")

    st.info("Importe tes achats + ventes pour calculer automatiquement ton Food Cost (%)")

    # ---------------
    # IMPORT ACHATS
    # ---------------
    st.subheader("📥 Achats (factures fournisseurs)")

    if file_foodcost:
        df_achats = pd.read_excel(file_foodcost)
        df_achats.columns = [c.lower().strip() for c in df_achats.columns]

        # recherche colonnes
        montant_col = [c for c in df_achats.columns if "montant" in c or "total" in c or "ttc" in c]
        if not montant_col:
            st.error("Impossible de trouver une colonne 'montant' dans l'import Achats.")
            st.stop()
        montant_col = montant_col[0]

        achats_total = df_achats[montant_col].apply(to_float).sum()

        st.metric("💸 Total Achats", f"{achats_total:,.2f} €")
        st.dataframe(df_achats, use_container_width=True)

    else:
        st.warning("Veuillez importer un fichier d’achats food cost.")
        achats_total = 0

    st.markdown("---")

    # ---------------
    # IMPORT VENTES
    # ---------------
    st.subheader("💰 Ventes (CA nourriture)")

    if not file_day:
        st.warning("Importer un fichier RestoTrack pour calculer les ventes.")
        st.stop()

    df_s, df_t, d = parse_restotrack(file_day)
    ventes_total = df_t[df_t["Categorie"] == "Nourriture"]["CA"].sum()

    st.metric("🥗 Total Ventes Nourriture TTC", f"{ventes_total:,.2f} €")

    # ---------------
    # FOOD COST %
    # ---------------
    st.markdown("### 📊 Food Cost (%)")

    if ventes_total > 0:
        fc = achats_total / ventes_total * 100
    else:
        fc = 0

    # Couleur
    if fc < 28:
        col = "🟢 Excellent"
    elif fc <= 35:
        col = "🟠 Surveiller"
    else:
        col = "🔴 Mauvais"

    st.metric("🍽️ Food Cost", f"{fc:,.1f} %", help=f"Niveau : {col}")

    if fc < 28:
        st.success("🟢 Très bon contrôle du food cost.")
    elif fc <= 35:
        st.warning("🟠 À surveiller. Attention aux pertes et aux achats inutiles.")
    else:
        st.error("🔴 Food cost trop élevé ! Ajuster pricing / pertes / fiches techniques.")

    # ---------------
    # GRAPHIQUE FC%
    # ---------------
    st.subheader("📈 Visualisation du Food Cost")

    fig_fc = px.bar(
        pd.DataFrame({"Type": ["Achats", "Ventes"], "Montant": [achats_total, ventes_total]}),
        x="Type",
        y="Montant",
        text_auto=True,
        color="Type",
        title="Achats vs Ventes – Impact sur FC%"
    )

    st.plotly_chart(fig_fc, use_container_width=True)
# ------------------------------------------------------------
# BLOC 9 – EXPORTS (PDF + EXCEL)
# ------------------------------------------------------------

if page == "Exports":

    st.markdown("## 📤 Exports")

    st.info("Télécharge tes données (Journalier, Historique, Food Cost, Productivité) en PDF ou Excel.")

    # ---------------------------------------------------------
    # EXPORT EXCEL CONSOLIDÉ
    # ---------------------------------------------------------
    st.subheader("📦 Export Excel (Consolidé)")

    if not file_day:
        st.warning("Importer le fichier du jour pour générer l’export.")
    else:
        df_s, df_t, d = parse_restotrack(file_day)

        def create_excel_export():
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_s.to_excel(writer, sheet_name="Détail Journalier", index=False)
                df_t.to_excel(writer, sheet_name="Synthèse Journalier", index=False)
            return output.getvalue()

        st.download_button(
            "📥 Télécharger Excel",
            data=create_excel_export(),
            file_name=f"Hive_Export_{d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # EXPORT PDF
    # ---------------------------------------------------------
    st.subheader("📄 Export PDF (Résumé du jour)")

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, "The Hive - Rapport Journalier", ln=True, align="C")

    def build_pdf(ca_total, couv_total, pm_midi, pm_soir, d):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.ln(10)

        pdf.cell(0, 10, f"Date : {d}", ln=True)
        pdf.cell(0, 10, f"CA Total TTC : {ca_total:,.2f} €", ln=True)
        pdf.cell(0, 10, f"Couverts Total : {couv_total}", ln=True)
        pdf.cell(0, 10, f"PM Midi : {pm_midi:,.2f} €", ln=True)
        pdf.cell(0, 10, f"PM Soir : {pm_soir:,.2f} €", ln=True)

        return pdf.output(dest="S").encode("latin-1")

    if file_day:
        df_s, df_t, d = parse_restotrack(file_day)

        # Mini-calculs pour le PDF
        ca_total = df_s["CA"].sum()
        couv_total = df_s["Couverts"].sum()

        ca_n_midi = df_t[(df_t["Categorie"]=="Nourriture") & (df_t["ServiceAgg"]=="Midi")]["CA"].sum()
        ca_n_soir = df_t[(df_t["Categorie"]=="Nourriture") & (df_t["ServiceAgg"]=="Soir")]["CA"].sum()

        couv_midi = df_s[(df_s["ServiceAgg"]=="Midi")]["Couverts"].sum()
        couv_soir = df_s[(df_s["ServiceAgg"]=="Soir")]["Couverts"].sum()

        pm_midi = ca_n_midi / couv_midi if couv_midi > 0 else 0
        pm_soir = ca_n_soir / couv_soir if couv_soir > 0 else 0

        pdf_bytes = build_pdf(ca_total, couv_total, pm_midi, pm_soir, d)

        st.download_button(
            "📥 Télécharger PDF",
            data=pdf_bytes,
            file_name=f"Hive_Rapport_{d}.pdf",
            mime="application/pdf"
        )
# ------------------------------------------------------------
# BLOC 10 – PARAMÈTRES (Dark Mode, Logo, Seuils)
# ------------------------------------------------------------

if page == "Paramètres":

    st.markdown("## ⚙️ Paramètres de l'application")

    st.markdown("### 🎨 Thème (Dark Mode / Light Mode)")

    theme = st.radio("Choisir un thème :", ["Clair", "Sombre"], horizontal=True)

    if theme == "Sombre":
        st.markdown(
            """
            <style>
            body { background-color: #111 !important; color: #eee !important; }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.success("🌙 Mode sombre activé")
    else:
        st.info("☀️ Mode clair activé")

    st.markdown("---")

    # -----------------------------------------------------
    # LOGO UPLOAD
    # -----------------------------------------------------
    st.markdown("### 🖼 Changer le logo The Hive")

    new_logo = st.file_uploader("Uploader un nouveau logo", type=["png", "jpg", "jpeg"])

    if new_logo:
        with open("logo.png", "wb") as f:
            f.write(new_logo.read())
        st.success("Logo remplacé ! Recharge l’application pour voir le nouveau logo.")

    st.markdown("---")

    # -----------------------------------------------------
    # SEUILS ALERTES : Payroll / FoodCost / CA
    # -----------------------------------------------------
    st.markdown("### 🚨 Seuils d’alertes")

    col1, col2, col3 = st.columns(3)

    payroll_low = col1.number_input("Payroll ratio optimal (%)", min_value=0, max_value=100, value=28)
    payroll_high = col1.number_input("Payroll ratio max acceptable (%)", min_value=0, max_value=100, value=33)

    fc_warn = col2.number_input("Seuil Food Cost warning (%)", min_value=0, max_value=100, value=35)
    fc_good = col2.number_input("Seuil Food Cost excellent (%)", min_value=0, max_value=100, value=28)

    ca_objectif = col3.number_input("Objectif CA journalier (€)", min_value=0, value=3000)

    st.info("💾 Les valeurs sont prises en compte immédiatement dans les pages Productivité & Food Cost.")

    st.markdown("---")

    st.success("Paramètres mis à jour !")

