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

st.set_page_config(page_title="Insta Analytics Pro", layout="wide", page_icon="📊")

# --- 2. STYLE CSS PROFESSIONNEL (Design Cartes) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; padding-top: 1rem; }
    
    /* Style de la carte individuelle */
    .insta-card {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e1e4e8;
        margin-bottom: 20px;
        overflow: hidden;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Image du post */
    .card-image {
        width: 100%;
        height: 280px;
        object-fit: cover;
        display: block;
    }

    /* Section des statistiques */
    .card-stats {
        padding: 20px;
    }

    /* Ligne de statistique individuelle */
    .stat-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid #f0f2f6;
    }
    .stat-row:last-child {
        border-bottom: none;
    }

    /* Label (ex: Likes) */
    .stat-label {
        color: #586069;
        font-size: 14px;
        font-weight: 500;
    }

    /* Valeur (ex: 1.2K) */
    .stat-value {
        color: #1b1f23;
        font-size: 15px;
        font-weight: 700;
    }

    /* Lien Voir le post */
    .card-link {
        text-align: center;
        padding: 12px;
        background-color: #ffffff;
        border-top: 1px solid #f0f2f6;
    }
    .card-link a {
        color: #0095f6;
        text-decoration: none;
        font-size: 14px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Analyse de compte Instagram")

# --- 3. FONCTION DE RÉCUPÉRATION AVEC CACHE ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_insta_data(insta_url, num_posts):
    if not API_TOKEN:
        return {"error": "Clé API manquante. Configurez APIFY_API_TOKEN."}

    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={API_TOKEN}"
    payload = {
        "directUrls": [insta_url],
        "resultsLimit": num_posts,
        "resultsType": "posts"
    }
    
    try:
        res_post = requests.post(run_url, json=payload, timeout=30)
        if res_post.status_code != 201:
            return {"error": f"Erreur Apify {res_post.status_code}"}
        
        run_data = res_post.json()
        dataset_id = run_data.get("data", {}).get("defaultDatasetId")
        
        # Attente pour garantir la génération des médias
        time.sleep(20)
        
        get_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_TOKEN}&format=json"
        res_get = requests.get(get_url, timeout=30)
        return res_get.json()
        
    except Exception as e:
        return {"error": str(e)}

# --- 4. FONCTION DE FORMATAGE (1200 -> 1.2K) ---
def format_num(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(int(n))

# --- 5. INTERFACE UTILISATEUR ---
with st.sidebar:
    st.header("Paramètres")
    limit = st.slider("Nombre de posts", 5, 50, 12)

url_input = st.text_input("URL du profil Instagram", placeholder="https://www.instagram.com/nom_du_compte/")

if st.button("Lancer l'analyse"):
    if not url_input:
        st.warning("Veuillez entrer une URL.")
    else:
        with st.spinner("Récupération des données..."):
            data = fetch_insta_data(url_input, limit)
            
            if isinstance(data, dict) and "error" in data:
                st.error(data["error"])
            elif not data:
                st.error("Aucune donnée trouvée.")
            else:
                df = pd.DataFrame(data)

                # Nettoyage et sécurité des colonnes
                for col in ['likesCount', 'videoPlayCount', 'commentsCount', 'displayUrl', 'url']:
                    if col not in df.columns: df[col] = 0 if 'Count' in col else ""
                
                df['likesCount'] = pd.to_numeric(df['likesCount']).fillna(0)
                df['videoPlayCount'] = pd.to_numeric(df['videoPlayCount']).fillna(0)
                df['commentsCount'] = pd.to_numeric(df['commentsCount']).fillna(0)
                df['Total_Visibility'] = df['likesCount'] + df['videoPlayCount']
                
                df_sorted = df.sort_values(by='Total_Visibility', ascending=False)

                # --- 6. AFFICHAGE DES TOP 3 (DESIGN CARTES) ---
                st.subheader("Top Performance")
                top3 = df_sorted.head(3)
                cols = st.columns(3)
                
                for i, (idx, row) in enumerate(top3.iterrows()):
                    with cols[i]:
                        # Préparation Image Proxy
                        raw_url = row.get('displayUrl', '')
                        img_src = f"https://images.weserv.nl/?url={quote(raw_url)}&w=500&h=500&fit=cover" if raw_url else "https://via.placeholder.com/500"
                        
                        # Calcul Taux Engagement
                        total_int = row['likesCount'] + row['commentsCount']
                        vues = row['videoPlayCount']
                        engage_rate = f"{(total_int / vues * 100):.2f}%" if vues > 0 else "N/A"

                        # HTML de la carte (Sans Emojis, style épuré)
                        card_html = f"""
                        <div class="insta-card">
                            <img src="{img_src}" class="card-image">
                            <div class="card-stats">
                                <div class="stat-row">
                                    <span class="stat-label">Likes</span>
                                    <span class="stat-value">{format_num(row['likesCount'])}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Vues Vidéo</span>
                                    <span class="stat-value">{format_num(vues) if vues > 0 else "Photo"}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Engagement</span>
                                    <span class="stat-value">{format_num(total_int)}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Taux d'eng.</span>
                                    <span class="stat-value">{engage_rate}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Commentaires</span>
                                    <span class="stat-value">{format_num(row['commentsCount'])}</span>
                                </div>
                            </div>
                            <div class="card-link">
                                <a href="{row['url']}" target="_blank">Voir le post</a>
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)

                # --- 7. TABLEAU RÉCAPITULATIF ---
                st.divider()
                st.subheader("Liste complète")
                if 'timestamp' in df_sorted.columns:
                    df_sorted['Date'] = pd.to_datetime(df_sorted['timestamp']).dt.strftime('%d/%m/%Y')
                
                cols_final = [c for c in ['Date', 'likesCount', 'videoPlayCount', 'commentsCount', 'url'] if c in df_sorted.columns]
                st.dataframe(df_sorted[cols_final], use_container_width=True)