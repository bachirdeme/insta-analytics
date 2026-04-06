import streamlit as st
import pandas as pd
import requests
import time
import os
from urllib.parse import quote

# --- 1. CONFIGURATION DES SECRETS & TOKEN ---
try:
    API_TOKEN = st.secrets["APIFY_API_TOKEN"]
except Exception:
    API_TOKEN = os.getenv("APIFY_API_TOKEN")

ACTOR_ID = "shu8hvrXbJbY3Eb9W" 

st.set_page_config(page_title="Rila Analytics | Insta Performance", layout="wide", page_icon="✨")

# --- 2. STYLE CSS SIGNATURE RILA STUDIO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;600&display=swap');

    .main { background-color: #FDFCFB; }
    
    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: #1A1A1A !important;
        font-weight: 400 !important;
        letter-spacing: 0.05em;
    }

    .rila-card {
        background-color: #ffffff;
        border-radius: 4px;
        border: 1px solid #EAE7E2;
        margin-bottom: 25px;
        overflow: hidden;
        transition: transform 0.3s ease;
    }

    .card-image {
        width: 100%;
        height: 300px;
        object-fit: cover;
    }

    .card-stats {
        padding: 25px;
        font-family: 'Inter', sans-serif;
    }

    .stat-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid #F5F2EF;
    }
    .stat-row:last-child { border-bottom: none; }

    .stat-label {
        color: #8C8279;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.15em;
    }

    .stat-value {
        color: #1A1A1A;
        font-size: 14px;
        font-weight: 600;
    }

    .card-link {
        text-align: center;
        padding: 20px;
        background-color: #FDFCFB;
    }
    .card-link a {
        color: #D4C2AD;
        text-decoration: none;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        border-bottom: 1px solid #D4C2AD;
    }

    div.stButton > button {
        background-color: #D4C2AD !important;
        color: white !important;
        border: none !important;
        border-radius: 0px !important;
        letter-spacing: 0.1em;
        padding: 0.6rem 2.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Instagram Insights")
st.markdown("---")

# --- 3. FONCTIONS TECHNIQUES ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_insta_data(insta_url, num_posts):
    if not API_TOKEN: return {"error": "API Token manquant."}
    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={API_TOKEN}"
    payload = {"directUrls": [insta_url], "resultsLimit": num_posts, "resultsType": "posts"}
    try:
        res = requests.post(run_url, json=payload, timeout=30)
        if res.status_code != 201: return {"error": f"Erreur API ({res.status_code})"}
        ds_id = res.json().get("data", {}).get("defaultDatasetId")
        time.sleep(20)
        items = requests.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?token={API_TOKEN}").json()
        return items
    except Exception as e: return {"error": str(e)}

def format_num(n):
    try:
        n = float(n) # Conversion sécurisée
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000: return f"{n/1_000:.1f}K"
        return str(int(n))
    except (ValueError, TypeError):
        return "0"

# --- 4. INTERFACE ---
with st.sidebar:
    st.header("Configuration")
    limit = st.slider("Nombre de publications", 3, 24, 6)

url_input = st.text_input("Profil Instagram", placeholder="Lien du profil...")

if st.button("Lancer l'analyse"):
    if url_input:
        with st.spinner("Analyse du feed en cours..."):
            data = fetch_insta_data(url_input, limit)
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                
                # NETTOYAGE ET CONVERSION ROBUSTE
                for col in ['likesCount', 'videoPlayCount', 'commentsCount']:
                    if col not in df.columns:
                        df[col] = 0
                    else:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                if 'displayUrl' not in df.columns: df['displayUrl'] = ""
                if 'url' not in df.columns: df['url'] = "https://instagram.com"

                df['Total'] = df['likesCount'] + df['videoPlayCount']
                df_sorted = df.sort_values(by='Total', ascending=False)

                # AFFICHAGE TOP 3 DESIGN RILA
                st.subheader("Contenus Performants")
                top3 = df_sorted.head(3)
                cols = st.columns(3)
                
                for i, (idx, row) in enumerate(top3.iterrows()):
                    with cols[i]:
                        raw_url = row.get('displayUrl', '')
                        img_src = f"https://images.weserv.nl/?url={quote(str(raw_url))}&w=600&h=750&fit=cover" if raw_url else "https://via.placeholder.com/600x750"
                        
                        l_val = row['likesCount']
                        v_val = row['videoPlayCount']
                        c_val = row['commentsCount']
                        
                        # Taux Engagement (Engagements / Vues)
                        rate = f"{( (l_val + c_val) / v_val * 100):.1f}%" if v_val > 0 else "N/A"

                        card_html = f"""
                        <div class="rila-card">
                            <img src="{img_src}" class="card-image">
                            <div class="card-stats">
                                <div class="stat-row">
                                    <span class="stat-label">Interactions</span>
                                    <span class="stat-value">{format_num(l_val)}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Visibilité</span>
                                    <span class="stat-value">{format_num(v_val) if v_val > 0 else "Photo"}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Engagement</span>
                                    <span class="stat-value">{rate}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Commentaires</span>
                                    <span class="stat-value">{format_num(c_val)}</span>
                                </div>
                            </div>
                            <div class="card-link">
                                <a href="{row['url']}" target="_blank">DÉCOUVRIR LE POST</a>
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)

                st.divider()
                st.subheader("Historique récent")
                # Affichage d'un tableau propre avec des colonnes renommées
                df_table = df_sorted[['likesCount', 'videoPlayCount', 'commentsCount', 'url']].copy()
                df_table.columns = ['Likes', 'Vues', 'Comms', 'Lien']
                st.dataframe(df_table.head(10), use_container_width=True)
            else:
                st.error("Impossible de récupérer les données. Vérifiez si le compte est public.")