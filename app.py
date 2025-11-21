    import streamlit as st
import pandas as pd
import plotly.express as px

from parser_restotrack_daily import parse_daily_report
from parser_n1 import parse_n1_month
from budget_loader import load_budget

st.set_page_config(
    page_title="Dashboard – Reporting The Hive",
    layout="wide"
)

# -------------------- LOGO --------------------
st.image("logo.png", width=180)
st.markdown("<h1 style='color:#e67e22;'>Dashboard – Reporting The Hive</h1>", unsafe_allow_html=True)

# -------------------- NAVIGATION --------------------
menu = st.sidebar.selectbox(
    "📌 Choisir une page",
    ["Rapport Journalier", "Analyse N-1", "Budget"]
)

# =====================================================================
# ======================== PAGE 1 : JOURNALIER ========================
# =====================================================================

if menu == "Rapport Journalier":
    st.header("📅 Rapport Journalier – Import RestoTrack")

    file = st.file_uploader("Importer un fichier Cumulatif_YYYYMMDD.xlsx", type=["xlsx"])

    if file:
        try:
            data = parse_daily_report(file)

            if data is None:
                st.error("❌ Impossible de lire le fichier.")
                st.stop()

            st.success("Fichier chargé avec succès ✔️")

            # Convert dict → DataFrame pour affichage
            df_day = pd.DataFrame([
                {"Service": "Midi", "Couverts": data["couverts_midi"], "CA_TTC": data["food_midi"] + data["boisson_midi"]},
                {"Service": "Soir", "Couverts": data["couverts_soir"], "CA_TTC": data["food_soir"] + data["boisson_soir"]},
                {"Service": "Total", "Couverts": data["couverts_total"], "CA_TTC": data["ca_total_ttc"]},
            ])

            # Affichage
            st.subheader(f"Données journalières – {data['date']}")
            st.dataframe(df_day, use_container_width=True)

            # KPI
            total_ca = data["ca_total_ttc"]
            midi_ca = df_day.loc[df_day["Service"]=="Midi","CA_TTC"].values[0]
            soir_ca = df_day.loc[df_day["Service"]=="Soir","CA_TTC"].values[0]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("CA Total TTC", f"{total_ca:,.2f} €")
            c2.metric("Couverts Total", int(data["couverts_total"]))
            c3.metric("CA Midi", f"{midi_ca:,.2f} €")
            c4.metric("CA Soir", f"{soir_ca:,.2f} €")

            # Graphique
            st.subheader("📊 Répartition du CA TTC")
            st.bar_chart(df_day.set_index("Service")["CA_TTC"])

        except Exception as e:
            st.error(f"Erreur lors du traitement : {e}")

# =====================================================================
# ======================== PAGE 2 : ANALYSE N-1 ========================
# =====================================================================

elif menu == "Analyse N-1":

    st.header("📊 Analyse N-1 – RestoTrack")

    file_n1 = st.file_uploader("Importer un fichier N-1 (mois ou année)", type=["xlsx"])

    if file_n1:
        try:
            df_n1 = parse_n1_month(file_n1)

            st.success("Fichier N-1 chargé ✔️")

            df_n1["Date"] = pd.to_datetime(df_n1["Date"])
            df_n1 = df_n1.sort_values("Date")

            total_n1 = df_n1["CA_TTC"].sum()

            st.subheader("📌 Résumé global N-1")
            k1, k2 = st.columns(2)
            k1.metric("Total CA TTC N-1", f"{total_n1:,.2f} €")
            k2.metric("Nombre de jours", df_n1.shape[0])

            st.markdown("---")

            st.subheader("Détails par jour")
            st.dataframe(df_n1, use_container_width=True)

            st.subheader("📈 Évolution du CA TTC N-1")
            fig = px.line(df_n1, x="Date", y="CA_TTC", markers=True)
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier N-1 : {e}")

# =====================================================================
# ======================== PAGE 3 : BUDGET MULTI-ANNÉE =================
# =====================================================================

elif menu == "Budget":

    st.header("💰 Analyse Budget – Multi-années")

    annee = st.selectbox("Sélectionner l'année", ["2024","2025","2026","2027"])
    n1_annee = str(int(annee) - 1)

    st.info(f"📌 Analyse pour : {annee} — Comparé à N-1 : {n1_annee}")

    colA, colB, colC = st.columns(3)

    with colA:
        budget_file = st.file_uploader(f"📘 Importer le Budget {annee}", type=["xlsx"], key=f"budget_{annee}")

    with colB:
        n1_file = st.file_uploader(f"📙 Importer le N-1 ({n1_annee})", type=["xlsx"], key=f"n1_{n1_annee}")

    with colC:
        realised_files = st.file_uploader(
            f"📗 Importer les rapports journaliers {annee} (multiples fichiers)",
            type=["xlsx"],
            accept_multiple_files=True,
            key=f"real_{annee}"
        )

    if budget_file and realised_files:
        try:
            df_budget = load_budget(budget_file)
            total_budget = df_budget["CA_TOTAL"].sum()

            if n1_file:
                df_n1 = parse_n1_month(n1_file)
                total_n1 = df_n1["CA_TTC"].sum()
            else:
                total_n1 = 0

            realised_values = []
            for f in realised_files:
                parsed = parse_daily_report(f)
                realised_values.append(parsed["ca_total_ttc"])

            total_realised = sum(realised_values)

            st.subheader("📌 KPI – Vue d'ensemble")
            k1, k2, k3 = st.columns(3)
            k1.metric(f"CA Réalisé {annee}", f"{total_realised:,.2f} €")
            k2.metric(f"CA Budget {annee}", f"{total_budget:,.2f} €")
            k3.metric(f"CA N-1 ({n1_annee})", f"{total_n1:,.2f} €")

            st.markdown("---")

            st.subheader("📊 Comparatif Global")
            comp = pd.DataFrame({
                "Catégorie": [f"Réalisé {annee}", f"Budget {annee}", f"N-1 {n1_annee}"],
                "Montant": [total_realised, total_budget, total_n1]
            })
            fig = px.bar(comp, x="Catégorie", y="Montant", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            st.subheader(f"📈 Évolution journalière {annee}")
            df_jour = pd.DataFrame({
                "Jour": list(range(1, len(realised_values) + 1)),
                "CA Réalisé": realised_values
            })
            fig2 = px.line(df_jour, x="Jour", y="CA Réalisé", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur lors du traitement : {e}")


        except Exception as e:
            st.error(f"Erreur dans l'analyse du Budget : {e}")
