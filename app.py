import streamlit as st
import pandas as pd
import plotly.express as px
import os
from parser_restotrack import parse_restotrack

st.set_page_config(page_title="The Hive Dashboard", layout="wide", page_icon="🍯")

# ----------------------------------------------------------
# LOGO
# ----------------------------------------------------------
if os.path.exists("logo.png"):
    st.image("logo.png", width=250)
else:
    st.title("THE HIVE DASHBOARD")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------
st.sidebar.title("📂 Import des fichiers")

file_day = st.sidebar.file_uploader("Fichier du jour (RestoTrack)", type=["xlsx"])
files_n1 = st.sidebar.file_uploader("Importer fichiers N-1", type=["xlsx"], accept_multiple_files=True)
file_budget = st.sidebar.file_uploader("Budget 2025", type=["xlsx"])

page = st.sidebar.radio("Navigation", [
    "Dashboard",
    "Historique",
    "Analyse Mensuelle",
    "Analyse Annuelle"
])

# ----------------------------------------------------------
# LOAD BUDGET
# ----------------------------------------------------------
def load_budget(f):
    df = pd.read_excel(f)
    df.columns = [c.lower().strip() for c in df.columns]
    # colonnes exigees :
    # mois / resto ttc / bar ttc / boutique / total ttc / couverts
    m = [c for c in df.columns if "mois" in c][0]
    resto = [c for c in df.columns if "resto" in c or "restaurant" in c][0]
    bar = [c for c in df.columns if "bar" in c][0]
    boutique = [c for c in df.columns if "boutique" in c][0]
    total = [c for c in df.columns if "total" in c][0]
    couv = [c for c in df.columns if "couvert" in c][0]

    df_budget = pd.DataFrame({
        "mois": df[m].astype(str).str.zfill(2),
        "budget_nourriture": df[resto] + df[boutique],
        "budget_boissons": df[bar],
        "budget_total": df[total],
        "budget_couverts": df[couv]
    })

    return df_budget

# ----------------------------------------------------------
# LOAD N-1
# ----------------------------------------------------------
def load_n1(files):
    if not files:
        return None

    results = []

    for f in files:
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

    df = pd.DataFrame(results)
    return df.groupby("mois", as_index=False).sum()


# ----------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------
if page == "Dashboard":

    if not file_day:
        st.warning("Importe le fichier du jour.")
        st.stop()

    df_s, df_t, date = parse_restotrack(file_day)

    st.title(f"📊 Dashboard — {date}")

    # KPI
    ca_n_midi = df_t[(df_t["Categorie"]=="Nourriture") & (df_t["ServiceAgg"]=="Midi")]["CA"].sum()
    ca_n_soir = df_t[(df_t["Categorie"]=="Nourriture") & (df_t["ServiceAgg"]=="Soir")]["CA"].sum()
    ca_b_midi = df_t[(df_t["Categorie"]=="Boissons") & (df_t["ServiceAgg"]=="Midi")]["CA"].sum()
    ca_b_soir = df_t[(df_t["Categorie"]=="Boissons") & (df_t["ServiceAgg"]=="Soir")]["CA"].sum()

    couv_midi = df_s[(df_s["Categorie"]=="Nourriture")&(df_s["ServiceAgg"]=="Midi")]["Couverts"].sum()
    couv_soir = df_s[(df_s["Categorie"]=="Nourriture")&(df_s["ServiceAgg"]=="Soir")]["Couverts"].sum()

    ca_total = ca_n_midi + ca_n_soir + ca_b_midi + ca_b_soir
    couv_total = couv_midi + couv_soir

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CA Total TTC", f"{ca_total:,.2f} €")
    col2.metric("Nourriture Midi", f"{ca_n_midi:,.2f} €")
    col3.metric("Nourriture Soir", f"{ca_n_soir:,.2f} €")
    col4.metric("Couverts Total", int(couv_total))

    # GRAPHIQUE
    df_plot = pd.DataFrame({
        "Service": ["Midi","Soir","Midi","Soir"],
        "Catégorie": ["Nourriture","Nourriture","Boissons","Boissons"],
        "CA": [ca_n_midi, ca_n_soir, ca_b_midi, ca_b_soir]
    })

    st.subheader("Répartition du CA")
    fig = px.bar(df_plot, x="Service", y="CA", color="Catégorie", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------
# HISTORIQUE
# ----------------------------------------------------------
if page == "Historique":
    if not file_day:
        st.warning("Import fichier du jour.")
        st.stop()

    df_s, df_t, d = parse_restotrack(file_day)
    st.title(f"📜 Historique — {d}")

    st.dataframe(df_s, use_container_width=True)


# ----------------------------------------------------------
# ANALYSE MENSUELLE
# ----------------------------------------------------------
if page == "Analyse Mensuelle":

    if not file_day or not file_budget:
        st.warning("Importer fichier du jour ET budget.")
        st.stop()

    df_s, df_t, d = parse_restotrack(file_day)
    df_real_mois = pd.DataFrame([{
        "mois": str(pd.to_datetime(d).month).zfill(2),
        "realise": df_s["CA"].sum()
    }])

    df_budget = load_budget(file_budget)
    df_n1 = load_n1(files_n1)

    df = df_budget.merge(df_real_mois, on="mois", how="left")
    if df_n1 is not None:
        df = df.merge(df_n1, on="mois", how="left")
    df = df.fillna(0)

    df["ecart_budget"] = df["realise"] - df["budget_total"]

    st.title("📆 Analyse Mensuelle")
    st.dataframe(df, use_container_width=True)

    fig = px.bar(df, x="mois",
        y=["realise","budget_total","n1_total" if "n1_total" in df else "budget_total"],
        barmode="group", text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------
# ANALYSE ANNUELLE
# ----------------------------------------------------------
if page == "Analyse Annuelle":

    if not file_budget:
        st.warning("Importer budget.")
        st.stop()

    df_budget = load_budget(file_budget)
    total_budget = df_budget["budget_total"].sum()

    if not file_day:
        st.warning("Importer fichier du jour.")
        st.stop()

    df_s, df_t, d = parse_restotrack(file_day)
    realise_total = df_s["CA"].sum()

    df_n1 = load_n1(files_n1)
    n1_total = df_n1["n1_total"].sum() if df_n1 is not None else 0

    st.title("📅 Analyse Annuelle")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Budget annuel", f"{total_budget:,.2f} €")
    c2.metric("Réalisé", f"{realise_total:,.2f} €")
    c3.metric("N-1", f"{n1_total:,.2f} €")
    c4.metric("Atteinte", f"{(realise_total/total_budget)*100:,.1f} %")

