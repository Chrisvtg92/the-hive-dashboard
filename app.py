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
# EXTRACT DATE FROM FIRST ROW
# --------------------------------------------------------------
def extract_date(df):
    """Détecte automatiquement une date dans la première ligne (ex : C1)."""
    first_row = df.iloc[0].astype(str)
    detected_date = None

    for value in first_row:
        try:
            parsed = pd.to_datetime(value, dayfirst=True, errors="ignore")
            if isinstance(parsed, pd.Timestamp):
                detected_date = parsed
                break
        except:
            pass

    return detected_date

# --------------------------------------------------------------
# DASHBOARD PAGE
# --------------------------------------------------------------
if page == "Dashboard":
    st.title("📊 Dashboard – The Hive (Vue journalière)")

    if df is None:
        st.warning("Veuillez importer le fichier cumulatif pour commencer.")
        st.stop()

    # --- Extraire la date du fichier ---
    detected_date = extract_date(df)

    if detected_date is None:
        st.error("Impossible de détecter la date du rapport (ex : cellule C1).")
        st.stop()

    # Ajouter la colonne Date à tout le dataset
    df["Date"] = detected_date

    # --- Nettoyage du tableau : retirer les lignes du haut si besoin ---
    df_clean = df.copy()
    df_clean = df_clean.dropna(how="all")  # supprime lignes vides

    # Vérifier que les colonnes essentielles existent
    required_columns = ["CA_total", "Couverts", "Ticket_moyen"]
    for col in required_columns:
        if col not in df_clean.columns:
            st.error(f"Colonne manquante dans le fichier : {col}")
            st.stop()

    # ---------------- KPIs ----------------
    today_data = df_clean.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CA Total", f"{today_data['CA_total']:.2f} €")
    col2.metric("Couverts", int(today_data["Couverts"]))
    col3.metric("Ticket Moyen", f"{today_data['Ticket_moyen']:.2f} €")

    if len(df_clean) >= 2:
        col4.metric("Variation J-1", f"{today_data['CA_total'] - df_clean.iloc[-2]['CA_total']:.2f} €")
    else:
        col4.metric("Variation J-1", "N/A")

    # ---------------- Graphique CA ----------------
    st.subheader("📈 Historique journalier du CA")
    fig = px.line(df_clean, x="Date", y="CA_total", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_clean)

    # ---------------- Budget & N-1 ----------------
    if df_prev is not None and df_budget is not None:
        st.subheader("📊 Comparaison Budget & N-1")

        df_prev["Date"] = detected_date
        df_budget["Date"] = detected_date

        merged = df_clean.merge(df_prev, on="Date", suffixes=("", "_N1"))
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

    detected_date = extract_date(df)
    df["Date"] = detected_date

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
