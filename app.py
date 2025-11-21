import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------
st.set_page_config(page_title="The Hive Dashboard", layout="wide")

# --------------------------------------------------------------
# SIDEBAR UPLOADS
# --------------------------------------------------------------
st.sidebar.header("📂 Import des fichiers")
file_current = st.sidebar.file_uploader("Fichier courant (Cumulatif)", type=["xlsx"])
file_prev = st.sidebar.file_uploader("Fichier N-1 (optionnel)", type=["xlsx"])
file_budget = st.sidebar.file_uploader("Fichier Budget (optionnel)", type=["xlsx"])

# --------------------------------------------------------------
# LOAD FILES
# --------------------------------------------------------------
def load_file(file):
    if file is None:
        return None
    return pd.read_excel(file)

df = load_file(file_current)
df_prev = load_file(file_prev)
df_budget = load_file(file_budget)

# --------------------------------------------------------------
# NAVIGATION
# --------------------------------------------------------------
st.sidebar.header("📌 Navigation")
page = st.sidebar.radio(
    "Aller à :",
    ["Dashboard", "Analyse Mensuelle", "Analyse Annuelle", "Productivité", "Export"]
)

# --------------------------------------------------------------
# DASHBOARD PAGE
# --------------------------------------------------------------
if page == "Dashboard":
    st.title("📊 Dashboard – The Hive (Vue journalière)")

    if df is None:
        st.warning("Veuillez importer le fichier cumulatif pour commencer.")
        st.stop()

    df["Date"] = pd.to_datetime(df["Date"])

    # Dernière ligne = jour courant
    today_data = df.iloc[-1]

    # ---------------- KPIs ----------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CA Total", f"{today_data['CA_total']:.2f} €")
    col2.metric("Couverts", int(today_data["Couverts"]))
    col3.metric("Ticket Moyen", f"{today_data['Ticket_moyen']:.2f} €")

    if len(df) >= 2:
        col4.metric("Variation J-1", f"{today_data['CA_total'] - df.iloc[-2]['CA_total']:.2f} €")
    else:
        col4.metric("Variation J-1", "N/A")

    # ---------------- Historique ----------------
    st.subheader("📈 Historique journalier du CA")
    fig = px.line(df, x="Date", y="CA_total", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df)

    # ---------------- Budget & N-1 ----------------
    if df_prev is not None and df_budget is not None:
        st.subheader("📊 Comparaison Budget & N-1")

        merged = df.merge(df_prev, on="Date", suffixes=("", "_N1"))
        merged = merged.merge(df_budget, on="Date")

        merged["Var vs N-1"] = merged["CA_total"] - merged["CA_total_N1"]
        merged["Var vs Budget"] = merged["CA_total"] - merged["Budget"]

        st.dataframe(merged)

# --------------------------------------------------------------
# MONTHLY ANALYSIS
# --------------------------------------------------------------
if page == "Analyse Mensuelle":
    st.title("📆 Analyse Mensuelle")

    if df is None:
        st.warning("Importez un fichier cumulatif.")
        st.stop()

    df["Date"] = pd.to_datetime(df["Date"])
    df["Mois"] = df["Date"].dt.to_period("M").astype(str)

    monthly = df.groupby("Mois").agg({
        "CA_total": "sum",
        "Couverts": "sum"
    }).reset_index()

    monthly["Ticket_moyen"] = monthly["CA_total"] / monthly["Couverts"]

    col1, col2 = st.columns(2)

    col1.subheader("CA par mois")
    fig1 = px.bar(monthly, x="Mois", y="CA_total")
    col1.plotly_chart(fig1, use_container_width=True)

    col2.subheader("Couverts par mois")
    fig2 = px.bar(monthly, x="Mois", y="Couverts")
    col2.plotly_chart(fig2, use_container_width=True)

    st.subheader("Tableau mensuel complet")
    st.dataframe(monthly)

# --------------------------------------------------------------
# ANNUAL ANALYSIS
# --------------------------------------------------------------
if page == "Analyse Annuelle":
    st.title("📅 Analyse Annuelle")

    if df is None:
        st.warning("Importez un fichier cumulatif.")
        st.stop()

    df["Année"] = pd.to_datetime(df["Date"]).dt.year

    annual = df.groupby("Année").agg({
        "CA_total": "sum",
        "Couverts": "sum"
    }).reset_index()

    annual["Ticket_moyen"] = annual["CA_total"] / annual["Couverts"]

    st.subheader("CA annuel")
    fig = px.bar(annual, x="Année", y="CA_total")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tableau annuel")
    st.dataframe(annual)

# --------------------------------------------------------------
# PRODUCTIVITÉ
# --------------------------------------------------------------
if page == "Productivité":
    st.title("⚙️ Productivité par service")

    if df is None:
        st.warning("Importez un fichier cumulatif.")
        st.stop()

    st.subheader("Paramètres personnels (à saisir manuellement)")
    colA, colB, colC = st.columns(3)

    personnel_matin = colA.number_input("Personnel Matin", min_value=0, value=2)
    personnel_midi = colB.number_input("Personnel Midi", min_value=0, value=3)
    personnel_soir = colC.number_input("Personnel Soir", min_value=0, value=3)

    taux_horaire = st.number_input("Taux horaire (€)", min_value=0.0, value=15.0)

    df_prod = df.copy()

    # Coûts
    df_prod["Coût Matin"] = personnel_matin * taux_horaire
    df_prod["Coût Midi"] = personnel_midi * taux_horaire
    df_prod["Coût Soir"] = personnel_soir * taux_horaire

    # Productivités
    df_prod["Prod Matin"] = df_prod.get("Matin", 0) / df_prod["Coût Matin"]
    df_prod["Prod Midi"] = df_prod.get("Midi", 0) / df_prod["Coût Midi"]
    df_prod["Prod Soir"] = df_prod.get("Soir", 0) / df_prod["Coût Soir"]

    # Ratio global
    df_prod["Ratio Total"] = (
        df_prod.get("Matin", 0) +
        df_prod.get("Midi", 0) +
        df_prod.get("Soir", 0)
    ) / (
        df_prod["Coût Matin"] +
        df_prod["Coût Midi"] +
        df_prod["Coût Soir"]
    )

    # Seuil d'alerte
    seuil = st.number_input("Seuil alerte productivité", min_value=0.0, value=1.5)
    last_ratio = df_prod.iloc[-1]["Ratio Total"]

    if last_ratio < seuil:
        st.error(f"⚠️ Productivité faible aujourd'hui : {last_ratio:.2f} (seuil : {seuil})")
    else:
        st.success(f"✅ Productivité correcte : {last_ratio:.2f}")

    # Graphique
    st.subheader("📉 Graphique productivité par service")
    figP = px.line(
        df_prod,
        x="Date",
        y=["Prod Matin", "Prod Midi", "Prod Soir"],
        markers=True,
        title="Productivité (CA / Coût du personnel)"
    )
    st.plotly_chart(figP, use_container_width=True)

    st.subheader("📋 Tableau complet productivité")
    df_export = df_prod[[
        "Date", "Matin", "Midi", "Soir",
        "Coût Matin", "Coût Midi", "Coût Soir",
        "Prod Matin", "Prod Midi", "Prod Soir",
        "Ratio Total"
    ]]
    st.dataframe(df_export)

    # Export Excel
    st.subheader("📤 Export Productivité")
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False)

    st.download_button(
        "Télécharger Productivité.xlsx",
        data=buffer.getvalue(),
        file_name="productivite.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --------------------------------------------------------------
# EXPORT PAGE
# --------------------------------------------------------------
if page == "Export":
    st.title("📤 Export des données")

    if df is None:
        st.warning("Importez un fichier cumulatif.")
        st.stop()

    if st.button("Télécharger le fichier Excel consolidé"):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "Télécharger Excel",
            data=buffer.getvalue(),
            file_name="dashboard_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
