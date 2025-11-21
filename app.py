import streamlit as st
import pandas as pd
import plotly.express as px

from parser_restotrack_daily import parse_daily_report
from parser_n1 import parse_n1_month
from budget_loader import load_budget

# -----------------------------------------------------------
# CONFIGURATION GLOBALE
# -----------------------------------------------------------
st.set_page_config(
    page_title="Dashboard – Reporting The Hive",
    layout="wide",
)

# -----------------------------------------------------------
# CHARGEMENT DU CSS THEME
# -----------------------------------------------------------
with open("theme.css", "r") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

# -----------------------------------------------------------
# LOGO
# -----------------------------------------------------------
st.image("logo.png", width=180)
st.markdown("## Dashboard – Reporting The Hive")


# -----------------------------------------------------------
# MENU LATÉRAL
# -----------------------------------------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Rapport Journalier – Import RestoTrack", "Analyse Mensuelle – Budget / N-1 / Réalisé", "Analyse Annuelle"]
)


# -----------------------------------------------------------
# PAGE 1 — RAPPORT JOURNALIER
# -----------------------------------------------------------
if menu == "Rapport Journalier – Import RestoTrack":

    st.markdown("### 📅 Rapport Journalier – Import RestoTrack")

    uploaded = st.file_uploader(
        "Importer un fichier **Cumulatif_YYYYMMDD.xlsx**",
        type=["xlsx"],
        accept_multiple_files=False
    )

    if uploaded:
        try:
            data = parse_daily_report(uploaded)

            st.success("Fichier traité avec succès ✔")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("CA Total TTC", f"{data['total_ca']:.2f} €")

            with col2:
                st.metric("Total Couverts", data["total_couverts"])

            with col3:
                st.metric("CA Midi – Nourriture", f"{data['midi_nourriture']:.2f} €")

            with col4:
                st.metric("CA Soir – Nourriture", f"{data['soir_nourriture']:.2f} €")

            col5, col6 = st.columns(2)
            with col5:
                st.metric("CA Midi – Boissons", f"{data['midi_boissons']:.2f} €")
            with col6:
                st.metric("CA Soir – Boissons", f"{data['soir_boissons']:.2f} €")

            # Graphique composition
            df_graph = pd.DataFrame({
                "Service": ["Midi", "Midi", "Soir", "Soir"],
                "Catégorie": ["Nourriture", "Boissons", "Nourriture", "Boissons"],
                "CA": [
                    data["midi_nourriture"],
                    data["midi_boissons"],
                    data["soir_nourriture"],
                    data["soir_boissons"],
                ]
            })

            fig = px.bar(
                df_graph,
                x="Service",
                y="CA",
                color="Catégorie",
                barmode="group",
                title="Répartition du CA par service",
                text_auto=True
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 📄 Détails bruts du fichier")
            st.dataframe(data["details"], use_container_width=True)

        except Exception as e:
            st.error(f"Erreur lors du traitement : {e}")


# -----------------------------------------------------------
# PAGE 2 — ANALYSE MENSUELLE
# -----------------------------------------------------------
elif menu == "Analyse Mensuelle – Budget / N-1 / Réalisé":

    st.markdown("## 📊 Analyse Mensuelle — Budget / N-1 / Réalisé")

    colA, colB, colC = st.columns(3)

    with colA:
        fichier_n1 = st.file_uploader("Importer fichier N-1 (mois complet)", type=["xlsx"], key="n1")

    with colB:
        fichier_budget = st.file_uploader("Importer Budget Annuel", type=["xlsx"], key="budget")

    with colC:
        fichier_resto = st.file_uploader("Importer les fichiers journaliers 2025", type=["xlsx"], accept_multiple_files=True, key="resto")

    if fichier_n1 and fichier_budget and fichier_resto:
        try:
            df_n1 = parse_n1_month(fichier_n1)
            df_budget = load_budget(fichier_budget)

            # Agrégation du réalisé 2025
            df_journalier = []
            for f in fichier_resto:
                parsed = parse_daily_report(f)
                df_journalier.append({
                    "ca": parsed["total_ca"],
                    "couverts": parsed["total_couverts"]
                })
            df_reel = pd.DataFrame(df_journalier)
            df_reel_month = df_reel.sum()

            # Display section
            st.success("Tous les fichiers ont été traités ✔")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("CA Réalisé", f"{df_reel_month['ca']:.2f} €")
            with col2:
                st.metric("CA Budget", f"{df_budget['CA TTC'].sum():.2f} €")
            with col3:
                st.metric("CA N-1", f"{df_n1['ca_total'].sum():.2f} €")

            st.markdown("---")
            st.markdown("### Comparatif Graphique")

            compar = pd.DataFrame({
                "Catégorie": ["Réalisé", "Budget", "N-1"],
                "Montant": [
                    df_reel_month["ca"],
                    df_budget["CA TTC"].sum(),
                    df_n1["ca_total"].sum(),
                ]
            })

            fig2 = px.bar(
                compar,
                x="Catégorie",
                y="Montant",
                text_auto=True,
                color="Catégorie",
                title="Comparatif Réalisé / Budget / N-1",
            )
            st.plotly_chart(fig2, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur dans l'analyse mensuelle : {e}")


# -----------------------------------------------------------
# PAGE 3 — ANALYSE ANNUELLE
# -----------------------------------------------------------
else:
    st.markdown("## 📈 Analyse Annuelle")

    st.info("Cette section sera activée une fois que tu m’auras envoyé tous les fichiers 2025 + Budget + N-1.")
    st.write("On pourra ensuite générer :")
    st.write("✔ Tendances de CA TTC")
    st.write("✔ Projection fin d'année")
    st.write("✔ Comparatif avec budget cumulatif")
    st.write("✔ KPI couverts / PM / CA catégorie")
