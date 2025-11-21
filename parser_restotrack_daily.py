import pandas as pd

def parse_daily_report(file):
    # Lire sans header
    df = pd.read_excel(file, header=None)

    # Trouver la ligne où commence le bloc (ligne contenant "Cumulatif" ou "Total")
    start_idx = df[df[0].astype(str).str.contains("Total", na=False)].index[0]

    # Extraire les lignes utiles (Total, Midi, Soir)
    block = df.loc[start_idx:start_idx+3, [0,1,4,6]]
    block.columns = ["Service", "Couverts", "CA_TTC", "Total"]

    # Nettoyage
    block["Couverts"] = pd.to_numeric(block["Couverts"], errors="coerce").fillna(0).astype(int)
    block["CA_TTC"]   = pd.to_numeric(block["CA_TTC"], errors="coerce").fillna(0).astype(float)

    # Renommage standard
    block["Service"] = block["Service"].replace({
        "Déjeuner/midi (11:00 - 17:00)": "Midi",
        "Nuit (17:00 - 04:00)": "Soir"
    })

    # On ne retourne que les vraies données
    return block[block["Service"].isin(["Midi","Soir","Total"])]

