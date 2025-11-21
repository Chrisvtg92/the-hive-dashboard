import pandas as pd

# ---------------------------------------------------------
#  PARSER RESTOTRACK — Rapport Journalier
# ---------------------------------------------------------
# - Récupère la date du rapport
# - Détecte les blocs "Nourriture" / "Boissons"
# - Calcule CA TTC Midi / Soir
# - Sépare les couverts pour midi / soir
# ---------------------------------------------------------

def parse_daily_report(file):
    # Lecture du fichier Excel
    df = pd.read_excel(file, header=None)

    # ---------------------------
    # 1. Extraction de la date
    # ---------------------------
    report_date = None
    for col in df.columns:
        for row in df[col].dropna().astype(str):
            if "/" in row and len(row) >= 8:
                try:
                    report_date = pd.to_datetime(row, dayfirst=True)
                    break
                except:
                    pass
        if report_date is not None:
            break

    if report_date is None:
        raise ValueError("Impossible de détecter la date du rapport.")

    # ---------------------------
    # 2. Détection des index utiles
    # ---------------------------

    # Index du bloc "Total / Matin / Déjeuner-Midi / Nuit"
    idx_total = df[df.astype(str).apply(lambda row: row.str.contains("Total", na=False)).any(axis=1)].index
    if len(idx_total) == 0:
        raise ValueError("Impossible de trouver la ligne 'Total'.")

    row_total = idx_total[0]

    # Extraction couverts
    couverts_total = int(df.iloc[row_total, 1])

    # Matin (souvent = petit dej → mis dans MIDI Nourriture ou Boisson selon catégorie)
    row_matin = row_total + 1
    couverts_matin = int(df.iloc[row_matin, 1])
    ca_matin_ttc = float(str(df.iloc[row_matin, 5]).replace("€", "").replace(",", ".").strip())

    # Déjeuner / Midi
    row_midi = row_total + 2
    couverts_midi = int(df.iloc[row_midi, 1])
    ca_midi_ttc = float(str(df.iloc[row_midi, 5]).replace("€", "").replace(",", ".").strip())

    # Soir
    row_soir = row_total + 3
    couverts_soir = int(df.iloc[row_soir, 1])
    ca_soir_ttc = float(str(df.iloc[row_soir, 5]).replace("€", "").replace(",", ".").strip())

    # ---------------------------
    # 3. Répartition nourriture / boisson
    # ---------------------------

    # Recherche du bloc Nourriture
    idx_food = df[df.astype(str).apply(
        lambda row: row.str.contains("Nourriture", na=False)
    ).any(axis=1)].index

    if len(idx_food) == 0:
        raise ValueError("Impossible de trouver le bloc Nourriture.")

    row_food = idx_food[0]

    food_midi = float(str(df.iloc[row_food + 1, 5]).replace("€", "").replace(",", ".").strip())
    food_soir = float(str(df.iloc[row_food + 2, 5]).replace("€", "").replace(",", ".").strip())

    # Recherche du bloc Boissons
    idx_bar = df[df.astype(str).apply(
        lambda row: row.str.contains("Boisson", na=False)
    ).any(axis=1)].index

    if len(idx_bar) == 0:
        raise ValueError("Impossible de trouver le bloc Boissons.")

    row_bar = idx_bar[0]

    bar_midi = float(str(df.iloc[row_bar + 1, 5]).replace("€", "").replace(",", ".").strip())
    bar_soir = float(str(df.iloc[row_bar + 2, 5]).replace("€", "").replace(",", ".").strip())

    # ---------------------------
    # 4. Construction du dataframe final
    # ---------------------------

    data = {
        "Date": [report_date],
        "Couverts_midi": [couverts_midi],
        "Couverts_soir": [couverts_soir],
        "Couverts_total": [couverts_total],

        "Food_midi_TTC": [food_midi],
        "Food_soir_TTC": [food_soir],

        "Bar_midi_TTC": [bar_midi],
        "Bar_soir_TTC": [bar_soir],

        "CA_total_TTC": [food_midi + food_soir + bar_midi + bar_soir],
    }

    return pd.DataFrame(data)
