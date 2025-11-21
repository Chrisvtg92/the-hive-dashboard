import pandas as pd
import numpy as np
import streamlit as st

# ----------------------------------------------------------
#  PARSER RESTOTRACK PRO — The Hive (2024–2026 compatible)
# ----------------------------------------------------------

def clean_amount(x):
    """Convertit un montant style '1 234,56 €' → float"""
    if pd.isna(x):
        return 0.0
    x = str(x).replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(x)
    except:
        return 0.0


def parse_daily_report(uploaded_file):
    try:
        df_raw = pd.read_excel(uploaded_file, header=None, dtype=str)
    except:
        st.error("Erreur : impossible de lire le fichier XLSX")
        return None

    # ----------------------------------------------------------
    # 1️⃣ DÉTECTION DU TABLEAU PRINCIPAL
    # ----------------------------------------------------------

    # Cherche la ligne où commence le tableau (celle avec 'Couverts')
    header_row = None
    for idx, row in df_raw.iterrows():
        if row.astype(str).str.contains("Couverts", case=False).any():
            header_row = idx
            break

    if header_row is None:
        st.error("❌ Impossible de détecter l'entête du tableau (ligne contenant 'Couverts').")
        return None

    # Le tableau principal fait toujours 4 lignes après l’entête
    df = df_raw.iloc[header_row:header_row + 5].reset_index(drop=True)

    # Première ligne = titres de colonnes
    df.columns = df.iloc[0]
    df = df[1:]

    # Garder uniquement les colonnes utiles
    expected_cols = ["Couverts", "Quantité du CA total", "C.A H.T.", "Total"]
    df = df[[c for c in expected_cols if c in df.columns]]

    # Nettoyage général
    df = df.replace("None", np.nan)

    # ----------------------------------------------------------
    # 2️⃣ EXTRACTION DES DONNÉES
    # ----------------------------------------------------------

    try:
        total_couverts = int(df["Couverts"].iloc[0])
    except:
        total_couverts = df["Couverts"].astype(str).str.replace(" ", "").replace("", 0).astype(int).sum()

    try:
        ca_total_ttc = clean_amount(df["Total"].iloc[0])
    except:
        ca_total_ttc = df["Total"].apply(clean_amount).sum()

    # Récupération des blocs Nourriture / Boissons
    # Ligne 1 = matin, ligne 2 = midi, ligne 3 = soir (structure stable)
    couverts_midi = int(df["Couverts"].iloc[2])
    couverts_soir = int(df["Couverts"].iloc[3])

    ca_food_midi = clean_amount(df["Total"].iloc[2])
    ca_food_soir = clean_amount(df["Total"].iloc[3])

    # Boissons = extrait via blocs supérieurs
    # On retrouve les lignes Boissons (bar) dans le fichier brut
    boissons = df_raw[df_raw.astype(str).apply(lambda r: r.str.contains("Boissons", case=False)).any(axis=1)]

    ca_boisson_midi = 0.0
    ca_boisson_soir = 0.0

    for _, row in boissons.iterrows():
        line = [clean_amount(x) for x in row if isinstance(x, str) and "€" in str(x)]
        if len(line) >= 2:
            ca_boisson_midi = max(ca_boisson_midi, line[0])
            ca_boisson_soir = max(ca_boisson_soir, line[-1])

    # ----------------------------------------------------------
    # 3️⃣ DÉTECTION DATE AUTOMATIQUE
    # ----------------------------------------------------------

    date_detected = None
    for col in df_raw.columns:
        for cell in df_raw[col]:
            try:
                date_detected = pd.to_datetime(cell, dayfirst=True, errors="ignore")
                if isinstance(date_detected, pd.Timestamp):
                    break
            except:
                continue
        if isinstance(date_detected, pd.Timestamp):
            break

    if not isinstance(date_detected, pd.Timestamp):
        date_detected = pd.Timestamp.today()

    # ----------------------------------------------------------
    # 4️⃣ RETOUR FORMAT APP
    # ----------------------------------------------------------

    return {
        "date": date_detected.date(),
        "couverts_total": total_couverts,
        "couverts_midi": couverts_midi,
        "couverts_soir": couverts_soir,
        "ca_total_ttc": ca_total_ttc,
        "food_midi": ca_food_midi,
        "food_soir": ca_food_soir,
        "boisson_midi": ca_boisson_midi,
        "boisson_soir": ca_boisson_soir
    }
