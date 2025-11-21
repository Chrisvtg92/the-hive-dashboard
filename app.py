import streamlit as st
import pandas as pd
import numpy as np
from parser_restotrack_daily import parse_daily_report
from parser_n1 import parse_n1_month
from budget_loader import load_budget

# ---------------------------
#   CONFIG APP
# ---------------------------
st.set_page_config(
    page_title="The Hive – Dashboard",
    layout="wide",
    page_icon="🍯"
)

# ---------------------------
#   LOGO
# ---------------------------
try:
    st.image("logo.png", width=180)
except:
    st.warning("⚠️ Logo introuvable : assure-toi que 'logo.png' est bien à la racine du repo.")

st.title("📊 Dashboard – Reporting The Hive")


# ---------------------------
#   MENU LATERAL
# ---------------------------
menu = st.sidebar.radio(
    "Navigation",
    [
        "📅 Rapport Journalier",
        "📈 Analyse Mensuelle",
        "📊 Analyse Annuelle",
        "🕒 Historique"
    ]
)


# ============================================================================================
#  📅 — PAGE 1 — RAPPORT JOURNALIER
# ============================================================================================
if menu == "📅 Rapport Journalier":
    st.header("📅 Rapport Journalier – Import RestoTrack")

    uploaded_file = st.file_uploader(
        "Importer un fichier **Cumulatif_YYYYMMDD.xlsx**",
        type=["xlsx"]
    )

    if uploaded_file:
        try:
            df_daily, resume = parse_daily_report(uploaded_file)

            st.success("✔️ Fichier traité avec succès !")

            # Résumé KPI
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("CA Total TTC", f"{resume['ca_total']:.2f} €")
            col2.metric("Couverts Total", resume["couverts_total"])
            col3.metric("Panier Moyen Midi", f"{resume['pm_midi']:.2f} €")
            col4.metric("Panier Moyen Soir", f"{resume['pm_soir']:.2f} €")

            # Détails nourriture & boissons
            st.subheader("Répartition CA TTC")
            colA, colB, colC, colD = st.columns(4)
            colA.metric("Nourriture Midi", f"{resume['food_midi']:.2f} €")
            colB.metric("Nourriture Soir", f"{resume['food_soir']:.2f} €")
            colC.metric("Boissons Midi", f"{resume['drink_midi']:.2f} €")
            colD.metric("Boissons Soir", f"{resume['drink_soir']:.2f} €")

            st.divider()

            # Graphique
            st.subheader("📊 CA par Service et Catégorie")
            st.bar_chart(df_daily.set_index("Service")[["Food", "Drinks"]])

        except Exception as e:
            st.error(f"❌ Erreur lors du traitement : {e}")


# ============================================================================================
#  📈 — PAGE 2 — ANALYSE MENSUELLE
# ============================================================================================
if menu == "📈 Analyse Mensuelle":
    st.header("📈 Analyse Mensuelle")

    uploaded_budget = st.file_uploader("Importer le fichier Budget 2025", type=["xlsx"])
    uploaded_n1 = st.file_uploader("Importer le cumulatif N-1 (mois)", type=["xlsx"])
    uploaded_realised = st.file_uploader("Importer les rapports journaliers cumulés", type=["csv"])

    if uploaded_budget and uploaded_realised:
        try:
            df_budget = load_budget(uploaded_budget)
            df_n1 = parse_n1_month(uploaded_n1) if uploaded_n1 else None
            df_real = pd.read_csv(uploaded_realised)

            st.success("✔️ Données chargées")

            st.subheader("Comparatif Budget / Réalisé")
            st.line_chart(df_real.set_index("Mois")[["CA", "Budget"]])

            if df_n1 is not None:
                st.subheader("Comparatif N-1")
                st.line_chart(df_real.set_index("Mois")[["CA", "N1"]])

        except Exception as e:
            st.error(f"Erreur : {e}")


# ============================================================================================
#  📊 — PAGE 3 — ANALYSE ANNUELLE
# ============================================================================================
if menu == "📊 Analyse Annuelle":
    st.header("📊 Analyse Annuelle – Budget / N-1 / Réalisé")

    uploaded_budget = st.file_uploader("Importer Budget 2025", type=["xlsx"])
    uploaded_n1_year = st.file_uploader("Importer cumulatif N-1 COMPLET", type=["xlsx"])
    uploaded_realised = st.file_uploader("Importer le CSV cumulé jour-par-jour", type=["csv"])

    if uploaded_budget and uploaded_realised:
        try:
            df_budget = load_budget(uploaded_budget)
            df_n1 = parse_n1_month(uploaded_n1_year) if uploaded_n1_year else None
            df_real = pd.read_csv(uploaded_realised)

            st.success("✔️ Données chargées")

            st.subheader("Vue Annuelle – CA")
            st.area_chart(df_real.set_index("Mois")[["CA", "Budget", "N1"]])

        except Exception as e:
            st.error(f"Erreur : {e}")


# ============================================================================================
#  🕒 — PAGE 4 — HISTORIQUE
# ============================================================================================
if menu == "🕒 Historique":
    st.header("🕒 Historique des Journées Importées")

    uploaded_history = st.file_uploader("Importer l’historique généré (CSV)", type=["csv"])

    if uploaded_history:
        try:
            df_hist = pd.read_csv(uploaded_history)
            st.dataframe(df_hist, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur : {e}")

