import pandas as pd

def load_budget(path, month_name):
    df = pd.read_excel(path)
    df.columns = df.columns.str.upper()

    # Exemple : colonne = "NOVEMBRE"
    if month_name not in df.columns:
        return None

    # Ligne contenant "CA TTC TOTAL"
    mask = df.iloc[:,0].astype(str).str.contains("CA", case=False) & \
           df.iloc[:,0].astype(str).str.contains("TTC", case=False)

    val = df.loc[mask, month_name].values
    if len(val) == 0:
        return None

    try:
        return float(str(val[0]).replace(",","."))
    except:
        return None
