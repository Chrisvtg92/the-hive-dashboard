import pandas as pd
from parser_restotrack import detect_category

def parse_restotrack_month_n1(path):
    df = pd.read_excel(path, header=None)

    # Colonnes utiles
    COL_LABEL = 0    # Libellé du centre (Boisson / Food etc.)
    COL_COUVERTS = 1
    COL_CA_TTC = 5   # F = CA TTC

    # Convertisseur CA TTC
    def get_ca(val):
        try:
            return float(str(val).replace("€", "").replace(",", ".").strip())
        except:
            return 0.0

    # Détection des blocs Midi / Soir
    midi_idx = df[df[COL_LABEL].astype(str).str.contains("Déjeuner/midi", case=False, na=False)].index
    soir_idx = df[df[COL_LABEL].astype(str).str.contains("Nuit", case=False, na=False)].index

    # Résultats
    result = {
        "ca_nourriture_midi": 0,
        "ca_boissons_midi": 0,
        "ca_nourriture_soir": 0,
        "ca_boissons_soir": 0,
        "couverts_midi": 0,
        "couverts_soir": 0,
        "total": 0
    }

    # ---------------- MIDI ----------------
    for i in midi_idx:
        # Couverts midi
        try:
            result["couverts_midi"] = int(df.loc[i, COL_COUVERTS])
        except:
            pass

        # Parcours du bloc CA immédiatement en dessous
        k = i + 1
        while isinstance(df.loc[k, COL_LABEL], str) and df.loc[k, COL_LABEL] != "":
            label = df.loc[k, COL_LABEL]
            categorie = detect_category(label)
            ca = get_ca(df.loc[k, COL_CA_TTC])

            if categorie == "nourriture":
                result["ca_nourriture_midi"] += ca
            elif categorie == "boissons":
                result["ca_boissons_midi"] += ca

            k += 1

    # ---------------- SOIR ----------------
    for i in soir_idx:
        try:
            result["couverts_soir"] = int(df.loc[i, COL_COUVERTS])
        except:
            pass

        k = i + 1
        while isinstance(df.loc[k, COL_LABEL], str) and df.loc[k, COL_LABEL] != "":
            label = df.loc[k, COL_LABEL]
            categorie = detect_category(label)
            ca = get_ca(df.loc[k, COL_CA_TTC])

            if categorie == "nourriture":
                result["ca_nourriture_soir"] += ca
            elif categorie == "boissons":
                result["ca_boissons_soir"] += ca

            k += 1

    result["total"] = (
        result["ca_nourriture_midi"] +
        result["ca_nourriture_soir"] +
        result["ca_boissons_midi"] +
        result["ca_boissons_soir"]
    )

    return result
