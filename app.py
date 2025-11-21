import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from parser_restotrack import parse_restotrack  # fichier séparé
import base64

st.set_page_config(
    page_title="The Hive – Dashboard",
    layout="wide",
    page_icon="🍯"
)

# ---------------------------------------------------
# STYLE + LOGO
# ---------------------------------------------------
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

if os.path.exists("logo.png"):
    st.image("logo.png", width=240)
else:
    st.title("THE HIVE DASHBOARD")  # fallback si le logo manque

# ---------------------------------------------------
# SIDEBAR — UPLOAD DES FICHIERS
# ---------------------------------------------------
st.sidebar.title("📂 Import des fichiers")

file_realtime = st.sidebar.file_uploader(
    "Importer fichier du jour (RestoTrack)", type=["xlsx"]
)

files_n1 = st.sidebar.file_uploader(
    "Importer fichiers N-1 (plusieurs fichiers possible)",
    type=["xlsx"],
    accept_multiple_files=True
)

file_budget = st.sidebar.file_uploader(
    "Importer budget annuel 2025",
    type=["xlsx"]
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Historique Journée",
        "Analyse Mensuelle",
        "Analyse Annuelle"
    ]
)

# ---------------------------------------------------
# FONCTION UTILE : Nettoyage nombre FR → float
# ---------------------------------------------------
def to_float(x):
    if x is None or pd.isna(x):
        return 0.0
    s = str(x)
    s = (s.replace("€", "")
           .replace("%", "")
           .replace("\xa0", "")
           .replace(" ", "")
           .replace("\u202f", "")
           .replace(",", "."))
    try:
        return float(s)
    except:
        return 0.0

# ---------------------------------------------------
# FONCTION : Charger budget annuel 2025 TTC
# ---------------------------------------------------
def load_budget(budget_file):
    df = pd.read_excel(budget_file)

    # On normalise les noms de colonnes
    df.columns = [str(c).strip().lower() for c in df.columns]

    # On attend les colonnes suivantes :
    # mois, ca resto ttc, ca bar ttc, boutique gourmande ttc, total ttc, couverts

    month_col = [c for c in df.columns if "mois" in c][0]
    resto_col = [c for c in df.columns if "resto" in c or "restaurant" in c][0]
    bar_col = [c for c in df.columns if "bar" in c][0]
    boutique_col = [c for c in df.columns if "boutique" in c][0]
    total_col = [c for c in df.columns if "total" in c][0]
    couverts_col = [c for c in df.columns if "couvert" in c][0]

    df["mois"] = df[month_col]
    df["ca_nourriture_budget"] = df[resto_col].apply(to_float) + df[boutique_col].apply(to_float)
    df["ca_boissons_budget"] = df[bar_col].apply(to_float)
    df["ca_total_budget"] = df[total_col].apply(to_float)
    df["couverts_budget"] = df[couverts_col].apply(to_float)

    df_budget = df[[
        "mois",
        "ca_nourriture_budget",
        "ca_boissons_budget",
        "ca_total_budget",
        "couverts_budget"
    ]]

    return df_budget
# ---------------------------------------------------
# FUSION DES FICHIERS N-1 (plusieurs fichiers)
# ---------------------------------------------------
def load_n1_files(n1_files):
    if not n1_files:
        return None

    monthly_results = []

    for f in n1_files:
        try:
            df_services, df_total, file_date = parse_restotrack(f)

            # Extraire mois en format "01", "02", etc.
            month = pd.to_datetime(file_date).strftime("%m")

            # Calcul N-1
            ca_midi_nourriture = df_total[
                (df_total["Categorie"] == "Nourriture") &
                (df_total["ServiceAgg"] == "Midi")
            ]["CA"].sum()

            ca_soir_nourriture = df_total[
                (df_total["Categorie"] == "Nourriture") &
                (df_total["ServiceAgg"] == "Soir")
            ]["CA"].sum()

            ca_midi_boissons = df_total[
                (df_total["Categorie"] == "Boissons") &
                (df_total["ServiceAgg"] == "Midi")
            ]["CA"].sum()

            ca_soir_boissons = df_total[
                (df_total["Categorie"] == "Boissons") &
                (df_total["ServiceAgg"] == "Soir")
            ]["CA"].sum()

            total_n1 = (
                ca_midi_nourriture + ca_soir_nourriture +
                ca_midi_boissons + ca_soir_boissons
            )

            monthly_results.append({
                "mois": month,
                "ca_n1": total_n1,
                "n1_nourriture": ca_midi_nourriture + ca_soir_nourriture,
                "n1_boissons": ca_midi_boissons + ca_soir_boissons,
            })

        except Exception as e:
            st.warning(f"Erreur sur fichier N-1 : {f.name} — {e}")

    if not monthly_results:
        return None

    df_n1 = pd.DataFrame(monthly_results)
    df_n1 = df_n1.groupby("mois", as_index=False).sum()

    return df_n1


# ---------------------------------------------------
# EXTRACTION MENSUELLE RÉALISÉ (depuis fichiers journaliers du jour)
# ---------------------------------------------------
def extract_monthly_realised(df_services, report_date):
    month = pd.to_datetime(report_date).strftime("%m")

    ca_midi_n = df_services[
        (df_services["Categorie"] == "Nourriture") &
        (df_services["ServiceAgg"] == "Midi")
    ]["CA"].sum()

    ca_soir_n = df_services[
        (df_services["Categorie"] == "Nourriture") &
        (df_services["ServiceAgg"] == "Soir")
    ]["CA"].sum()

    ca_midi_b = df_services[
        (df_services["Categorie"] == "Boissons") &
        (df_services["ServiceAgg"] == "Midi")
    ]["CA"].sum()

    ca_soir_b = df_services[
        (df_services["Categorie"] == "Boissons") &
        (df_services["ServiceAgg"] == "Soir")
    ]["CA"].sum()

    total = ca_midi_n + ca_soir_n + ca_midi_b + ca_soir_b

    return pd.DataFrame([{
        "mois": month,
        "realise": total,
        "realise_nourriture": ca_midi_n + ca_soir_n,
        "realise_boissons": ca_midi_b + ca_soir_b,
    }])


# ---------------------------------------------------
# EXTRACTION ANNUELLE
# ---------------------------------------------------
def compute_annual(df_budget, df_n1, df_realised):
    annual = {}

    annual["budget_total"] = df_budget["ca_total_budget"].sum()
    annual["budget_nourriture"] = df_budget["ca_nourriture_budget"].sum()
    annual["budget_boissons"] = df_budget["ca_boissons_budget"].sum()

    if df_n1 is not None:
        annual["n1_total"] = df_n1["ca_n1"].sum()
    else:
        annual["n1_total"] = 0

    annual["realise_total"] = df_realised["realise"].sum()

    annual["ecart_vs_budget"] = (
        annual["realise_total"] - annual["budget_total"]
    )

    annual["atteinte"] = (
        annual["realise_total"] / annual["budget_total"] * 100
        if annual["budget_total"] > 0 else 0
    )

    return annual
# ---------------------------------------------------
# DASHBOARD JOURNALIER
# ---------------------------------------------------
if page == "Dashboard":

    if not file_realtime:
        st.warning("Importe le fichier du jour pour afficher le dashboard.")
        st.stop()

    # Parsing du fichier du jour
    df_services, df_total, report_date = parse_restotrack(file_realtime)

    st.title(f"📊 Dashboard Journalier – {report_date}")

    # ----------------------------
    # CALCUL KPI JOURNÉE
    # ----------------------------
    def get(df, cat, serv):
        sub = df[(df["Categorie"] == cat) & (df["ServiceAgg"] == serv)]
        return float(sub["CA"].sum())

    def get_couv(df, cat, serv):
        sub = df[(df["Categorie"] == cat) & (df["ServiceAgg"] == serv)]
        return int(sub["Couverts"].sum())

    # Nourriture
    ca_n_midi = get(df_services, "Nourriture", "Midi")
    ca_n_soir = get(df_services, "Nourriture", "Soir")

    # Boissons
    ca_b_midi = get(df_services, "Boissons", "Midi")
    ca_b_soir = get(df_services, "Boissons", "Soir")

    # Totaux CA TTC
    ca_total = ca_n_midi + ca_n_soir + ca_b_midi + ca_b_soir

    # Couverts
    couv_midi = get_couv(df_services, "Nourriture", "Midi")
    couv_soir = get_couv(df_services, "Nourriture", "Soir")
    couv_total = couv_midi + couv_soir

    # Tickets moyens
    tm_midi = ca_n_midi / couv_midi if couv_midi > 0 else 0
    tm_soir = ca_n_soir / couv_soir if couv_soir > 0 else 0

    # ----------------------------
    # KPIs HAUT DE PAGE
    # ----------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 CA Total TTC", f"{ca_total:,.2f} €")
    c2.metric("👥 Total Couverts", couv_total)
    c3.metric("🍽 PM Midi", f"{tm_midi:,.2f} €")
    c4.metric("🌙 PM Soir", f"{tm_soir:,.2f} €")

    st.subheader("Répartition du CA TTC")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Nourriture Midi", f"{ca_n_midi:,.2f} €")
    c6.metric("Nourriture Soir", f"{ca_n_soir:,.2f} €")
    c7.metric("Bar Midi (Boissons)", f"{ca_b_midi:,.2f} €")
    c8.metric("Bar Soir (Boissons)", f"{ca_b_soir:,.2f} €")

    # ----------------------------
    # GRAPHIQUE : CA PAR SERVICE
    # ----------------------------
    st.subheader("📈 CA par Service – Composition")

    df_graph = pd.DataFrame({
        "Service": ["Midi", "Soir", "Midi", "Soir"],
        "Catégorie": ["Nourriture", "Nourriture", "Boissons", "Boissons"],
        "CA TTC": [ca_n_midi, ca_n_soir, ca_b_midi, ca_b_soir]
    })

    fig = px.bar(
        df_graph,
        x="Service",
        y="CA TTC",
        color="Catégorie",
        barmode="group",
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------
# HISTORIQUE JOURNALIER
# ---------------------------------------------------
if page == "Historique Journée":

    if not file_realtime:
        st.warning("Importe le fichier du jour pour afficher l’historique.")
        st.stop()

    df_services, df_total, report_date = parse_restotrack(file_realtime)

    st.title("📜 Historique – Détails de la journée")

    df_hist = []

    # Midi
    df_hist.append({
        "Date": report_date,
        "Service": "Midi",
        "Couverts": df_services[(df_services["Categorie"]=="Nourriture") &
                                (df_services["ServiceAgg"]=="Midi")]["Couverts"].sum(),
        "CA Nourriture TTC": df_services[(df_services["Categorie"]=="Nourriture") &
                                         (df_services["ServiceAgg"]=="Midi")]["CA"].sum(),
        "CA Boissons TTC": df_services[(df_services["Categorie"]=="Boissons") &
                                       (df_services["ServiceAgg"]=="Midi")]["CA"].sum()
    })

    # Soir
    df_hist.append({
        "Date": report_date,
        "Service": "Soir",
        "Couverts": df_services[(df_services["Categorie"]=="Nourriture") &
                                (df_services["ServiceAgg"]=="Soir")]["Couverts"].sum(),
        "CA Nourriture TTC": df_services[(df_services["Categorie"]=="Nourriture") &
                                         (df_services["ServiceAgg"]=="Soir")]["CA"].sum(),
        "CA Boissons TTC": df_services[(df_services["Categorie"]=="Boissons") &
                                       (df_services["ServiceAgg"]=="Soir")]["CA"].sum()
    })

    st.dataframe(pd.DataFrame(df_hist), use_container_width=True)
# ---------------------------------------------------
# ANALYSE MENSUELLE
# ---------------------------------------------------
if page == "Analyse Mensuelle":

    st.title("📆 Analyse Mensuelle – Budget / N-1 / Réalisé")

    if not file_budget:
        st.warning("⚠️ Merci d’importer le fichier BUDGET 2025.")
        st.stop()

    df_budget = load_budget(file_budget)

    # Charger N-1 (plusieurs fichiers)
    df_n1 = load_n1_files(files_n1)

    if df_n1 is None:
        st.warning("⚠️ Aucun fichier N-1 importé. Impossible d’afficher N-1.")
        df_n1 = pd.DataFrame(columns=["mois", "ca_n1"])

    # Charger réalisé du jour
    if not file_realtime:
        st.warning("Merci d'importer le fichier du jour pour calculer le réalisé.")
        st.stop()

    df_services, df_total, report_date = parse_restotrack(file_realtime)
    df_real_m = extract_monthly_realised(df_services, report_date)

    # Fusion Budget + N-1 + Réalisé
    df_merge = df_budget.merge(df_n1, on="mois", how="left")\
                        .merge(df_real_m, on="mois", how="left")

    # Remplace NaN par 0
    df_merge = df_merge.fillna(0)

    # Calcul des écarts
    df_merge["ecart_vs_budget"] = df_merge["realise"] - df_merge["ca_total_budget"]
    df_merge["ecart_vs_n1"] = df_merge["realise"] - df_merge["ca_n1"]

    df_merge["atteinte_budget_%"] = df_merge.apply(
        lambda r: (r["realise"] / r["ca_total_budget"] * 100) if r["ca_total_budget"] > 0 else 0,
        axis=1
    )

    st.subheader("📊 Tableau Mensuel")

    st.dataframe(
        df_merge[[
            "mois",
            "realise",
            "ca_total_budget",
            "ca_n1",
            "ecart_vs_budget",
            "ecart_vs_n1",
            "atteinte_budget_%"
        ]],
        use_container_width=True
    )

    # -------------------------------------------
    # Graphique Budget / N-1 / Réalisé
    # -------------------------------------------
    st.subheader("📈 Budget vs N-1 vs Réalisé")

    df_plot = df_merge.copy()
    df_plot["Mois"] = df_plot["mois"]

    fig = px.bar(
        df_plot,
        x="Mois",
        y=["realise", "ca_total_budget", "ca_n1"],
        barmode="group",
        labels={"value": "Montant (€)", "variable": "Catégorie"},
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------
    # Objectif du mois
    # -------------------------------------------
    st.subheader("🎯 Objectif du mois")

    obj_mens = float(df_merge.loc[0, "ca_total_budget"])
    real_mens = float(df_merge.loc[0, "realise"])
    reste = obj_mens - real_mens
    atteinte = real_mens / obj_mens * 100 if obj_mens > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Budget du mois", f"{obj_mens:,.2f} €")
    c2.metric("Réalisé", f"{real_mens:,.2f} €")
    c3.metric("Atteinte", f"{atteinte:,.1f} %")

    st.info(f"Reste à faire : **{reste:,.2f} €**")


# ---------------------------------------------------
# ANALYSE ANNUELLE
# ---------------------------------------------------
if page == "Analyse Annuelle":

    st.title("📅 Analyse Annuelle – Budget / N-1 / Réalisé")

    if not file_budget:
        st.warning("⚠️ Merci d’importer le fichier budget.")
        st.stop()

    if not file_realtime:
        st.warning("⚠️ Merci d’importer un fichier du jour.")
        st.stop()

    df_services, df_total, report_date = parse_restotrack(file_realtime)
    df_realised_m = extract_monthly_realised(df_services, report_date)
    df_budget = load_budget(file_budget)
    df_n1 = load_n1_files(files_n1)

    if df_n1 is None:
        df_n1 = pd.DataFrame(columns=["mois", "ca_n1"])

    # Reconstruction annuelle
    annual = compute_annual(df_budget, df_n1, df_realised_m)

    st.subheader("🔢 Résumé Annuel")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget Annuel", f"{annual['budget_total']:,.2f} €")
    c2.metric("Réalisé", f"{annual['realise_total']:,.2f} €")
    c3.metric("N-1", f"{annual['n1_total']:,.2f} €")
    c4.metric("Atteinte", f"{annual['atteinte']:,.1f} %")

    ecart = annual["ecart_vs_budget"]
    st.success(f"Écart vs Budget : **{ecart:,.2f} €**" if ecart >= 0 else
               f"Écart vs Budget : **{ecart:,.2f} €**", icon="📉")
