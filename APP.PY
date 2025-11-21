import streamlit as st
from pathlib import Path

# ---------------------------------------------------
# CONFIG  
# ---------------------------------------------------
st.set_page_config(
    page_title="The Hive Dashboard",
    page_icon="🐝",
    layout="wide"
)

# ---------------------------------------------------
# CUSTOM CSS (from /assets/theme.css)
# ---------------------------------------------------
def load_css():
    css_path = Path("assets/theme.css")
    if css_path.exists():
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ---------------------------------------------------
# HEADER  
# ---------------------------------------------------
col1, col2 = st.columns([1, 5])
with col1:
    st.image("assets/logo.png", width=180)

with col2:
    st.markdown("""
        <h1 style='margin-bottom:0px;'>The Hive – Dashboard Premium</h1>
        <h3 style='color:gray;margin-top:5px;'>Pilotage - Analyse - Performance</h3>
    """, unsafe_allow_html=True)

st.markdown("---")
# ---------------------------------------------------
# ACCUEIL
# ---------------------------------------------------

st.markdown("""
Bienvenue dans **The Hive Dashboard Premium**, votre plateforme complète pour :
- Le reporting **journalier**
- L’analyse **mensuelle N / N-1 / Budget**
- Le suivi **annuel**
- Le chargement et traitement des fichiers Restotrack
- Le suivi **des couverts**, **des ventes Food/Boisson**, **des écarts Budget**
- L’historique consolidé

👉 Utilisez le menu à gauche pour naviguer entre les pages.
""")

st.info("💡 Astuce : chargez d'abord votre Budget 2025 + vos fichiers N-1 pour activer les comparaisons.")
# ---------------------------------------------------
# MULTIPAGE HANDLING
# ---------------------------------------------------

st.sidebar.title("Navigation")
st.sidebar.markdown("Choisissez une vue :")

# Pas besoin d'ajouter les pages ici — Streamlit détecte automatiquement
# les fichiers dans /pages grâce au naming "1_", "2_", etc.

st.sidebar.markdown("---")
st.sidebar.caption("© The Hive Dashboard – Powered by Christophe & GPT 🚀")
