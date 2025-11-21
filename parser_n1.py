import pandas as pd

def parse_n1_month(file):
    df = pd.read_excel(file)

    # Chercher colonnes contenant "CA TTC"
    ca_cols = [c for c in df.columns if "CA" in c or "TTC" in c]

    df = df[["Date", "Service"] + ca_cols]
    df["CA_TTC"] = df[ca_cols].sum(axis=1)

    return df[["Date", "Service", "CA_TTC"]]

