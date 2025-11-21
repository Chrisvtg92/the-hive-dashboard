# ----------------------------------------------------------
#     ANALYSE MENSUELLE – BUDGET / N-1 / RÉALISÉ
# ----------------------------------------------------------
import streamlit as st
from parser_restotrack import parse_restotrack_daily
from parser_n1 import parse_restotrack_month_n1
import pandas as pd

st.header("📅 Analyse Mensuelle – Budget / N-1 / Réalisé")

uploaded_budget = st.file_uploader("Importer Budget 2025", type=["xlsx"])
uploaded_n1 = st.file_uploader("Importer N-1 (mois complet)", type=["xlsx"])
uploaded_current = st.file_uploader("Importer les fichiers journaliers N", type=["xlsx"], accept_multiple_files=True)

if uploaded_budget and uploaded_n1 and uploaded_current:

    # ------- A) CALCUL N (2025) -------
    total_n = 0
    total_couverts = 0
    ca_nour_midi = 0
    ca_nour_soir = 0
    ca_boi_midi = 0
    ca_boi_soir = 0

    for file in uploaded_current:
        d = parse_restotrack_daily(file)
        total_n += d["total_ca"]
        total_couverts += d["couverts_midi"] + d["couverts_soir"]
        ca_nour_midi += d["ca_nourriture_midi"]
        ca_nour_soir += d["ca_nourriture_soir"]
        ca_boi_midi += d["ca_boissons_midi"]
        ca_boi_soir += d["ca_boissons_soir"]

    # ------- B) CALCUL N-1 -------
    d_n1 = parse_restotrack_month_n1(uploaded_n1)
    total_n1 = d_n1["total"]

    # ------- C) BUDGET -------
    df_budget = pd.read_excel(uploaded_budget)
    df_budget.columns = df_budget.columns.str.upper()

    # On cherche le mois automatiquement via N1 filename
    month_number = uploaded_n1.name[14:16]  # ex: "11"
    month_number = int(month_number)

    month_map = {
        1:"JANVIER",2:"FÉVRIER",3:"MARS",4:"AVRIL",5:"MAI",6:"JUIN",
        7:"JUILLET",8:"AOÛT",9:"SEPTEMBRE",10:"OCTOBRE",11:"NOVEMBRE",12:"DÉCEMBRE"
    }

    col_month = month_map[month_number]

    budget_total = float(df_budget.loc[df_budget["A"]=="CA RESTO TTC", col_month])

    # ------- D) KPI -------
    ecart_n1 = total_n - total_n1
    ecart_pct_n1 = (ecart_n1 / total_n1 * 100) if total_n1 else 0

    ecart_budget = total_n - budget_total
    ecart_pct_budget = (ecart_budget / budget_total * 100) if budget_total else 0

    st.subheader("📊 KPIs du mois")
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("CA Réalisé (N)", f"{total_n:,.2f} €")
    c2.metric("CA N-1", f"{total_n1:,.2f} €", f"{ecart_n1:,.2f} €")
    c3.metric("Écart % N/N-1", f"{ecart_pct_n1:.1f} %")
    c4.metric("Budget", f"{budget_total:,.2f} €", f"{ecart_budget:,.2f} €")
    c5.metric("Écart % vs Budget", f"{ecart_pct_budget:.1f} %")

    # ------- E) Graphique simple -------
    df_graph = pd.DataFrame({
        "Type": ["N", "N-1", "Budget"],
        "CA": [total_n, total_n1, budget_total]
    })

    st.bar_chart(df_graph.set_index("Type"))

    # ------- F) Répartition -------
    st.subheader("Répartition du CA")

    df_rep = pd.DataFrame({
        "Catégorie": ["Nourriture Midi","Nourriture Soir","Boissons Midi","Boissons Soir"],
        "CA": [ca_nour_midi, ca_nour_soir, ca_boi_midi, ca_boi_soir]
    })

    st.bar_chart(df_rep.set_index("Catégorie"))
