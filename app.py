import streamlit as st
import pandas as pd
import requests
import time
import os

# --- 1. CONFIGURATION DES SECRETS ---
# Cherche d'abord dans Streamlit Secrets (Cloud), sinon dans l'environnement local
API_TOKEN = st.secrets.get("APIFY_API_TOKEN") or os.getenv("APIFY_API_TOKEN")
ACTOR_ID = "shu8hvrXbJbY3Eb9W" 

st.set_page_config(page_title="Insta Performance Pro", layout="wide", page_icon="📊")

# Style CSS pour améliorer l'affichage sur mobile
st.markdown("""
    <style>
    .main { padding-top: 1rem; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_status=True)

st.title("📊 Instagram Performance Analyzer")

# --- 2. FONCTION DE RÉCUPÉRATION AVEC CACHE (1 HEURE) ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_insta_data(insta_url, num_posts):
    if not API_TOKEN:
        return {"error": "Clé API manquante. Configurez APIFY_API_TOKEN dans les secrets Streamlit."}

    # Étape A : Lancement du Scraper (POST)
    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={API_TOKEN}"
    payload = {
        "directUrls": [insta_url],
        "resultsLimit": num_posts,
        "resultsType": "posts"
    }
    
    try:
        res_post = requests.post(run_url, json=payload, timeout=30)
        if res_post.status_code != 201:
            return {"error": f"Erreur Apify {res_post.status_code}: {res_post.text}"}
        
        run_data = res_post.json()
        dataset_id = run_data.get("data", {}).get("defaultDatasetId")
        
        if not dataset_id:
            return {"error": "L'API n'a pas retourné d'ID de données."}

        # Étape B : Attente (Le temps que le scraper travaille)
        # Pour une app pro, on pourrait boucler sur l'état du run, mais 15s suffit pour 10-20 posts
        time.sleep(15)
        
        # Étape C : Récupération des résultats (GET)
        get_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_TOKEN}&format=json"
        res_get = requests.get(get_url, timeout=30)
        return res_get.json()
        
    except Exception as e:
        return {"error": f"Erreur de connexion : {str(e)}"}

# --- 3. INTERFACE UTILISATEUR ---
with st.sidebar:
    st.header("Paramètres")
    limit = st.slider("Nombre de posts à analyser", 5, 50, 12)
    st.info("Le cache garde les résultats en mémoire pendant 1h pour économiser vos crédits.")

url_input = st.text_input("Lien du profil Instagram", placeholder="https://www.instagram.com/nom_du_compte/")

if st.button("🚀 Analyser la performance"):
    if not url_input:
        st.warning("Veuillez entrer une URL de profil valide.")
    else:
        with st.status("Récupération des données Instagram...") as status:
            data = fetch_insta_data(url_input, limit)
            
            if isinstance(data, dict) and "error" in data:
                status.update(label="Échec de l'analyse", state="error")
                st.error(data["error"])
            elif not data or len(data) == 0:
                status.update(label="Aucun résultat", state="error")
                st.error("Aucune donnée reçue. Vérifiez que le profil est public.")
            else:
                status.update(label="Données analysées avec succès !", state="complete")
                
                # --- 4. TRAITEMENT DES DONNÉES (SÉCURISÉ) ---
                df = pd.DataFrame(data)

                # Sécurité : On crée les colonnes si elles manquent dans le JSON
                for col in ['likesCount', 'videoPlayCount', 'commentsCount', 'displayUrl', 'url', 'timestamp']:
                    if col not in df.columns:
                        df[col] = 0 if 'Count' in col else ""

                # Conversion numérique propre
                df['likesCount'] = pd.to_numeric(df['likesCount'], errors='coerce').fillna(0)
                df['videoPlayCount'] = pd.to_numeric(df['videoPlayCount'], errors='coerce').fillna(0)
                df['commentsCount'] = pd.to_numeric(df['commentsCount'], errors='coerce').fillna(0)
                
                # Calcul de la visibilité (Engagement + Portée vidéo)
                df['Total_Visibility'] = df['likesCount'] + df['videoPlayCount']
                
                # Tri par performance
                df_sorted = df.sort_values(by='Total_Visibility', ascending=False)

                # --- 5. AFFICHAGE DES RÉSULTATS ---
                
                # Top 3 en visuels
                st.subheader("🏆 Top 3 des posts les plus performants")
                top3 = df_sorted.head(3)
                cols = st.columns(3)
                
                for i, (idx, row) in enumerate(top3.iterrows()):
                    with cols[i]:
                        img = row['displayUrl'] if row['displayUrl'] else "https://via.placeholder.com/300"
                        st.image(img, use_container_width=True)
                        st.metric("❤️ Likes", f"{int(row['likesCount']):,}")
                        
                        v_count = int(row['videoPlayCount'])
                        st.metric("👁️ Vues Vidéo", f"{v_count:,}" if v_count > 0 else "📸 Photo")
                        
                        st.write(f"[🔗 Voir le post]({row['url']})")

                # Graphique d'évolution (Optionnel)
                st.subheader("📈 Évolution de la visibilité")
                if 'timestamp' in df.columns:
                    df['date'] = pd.to_datetime(df['timestamp']).dt.date
                    chart_data = df.groupby('date')['Total_Visibility'].sum()
                    st.line_chart(chart_data)

                # Tableau complet
                st.subheader("📋 Détails de tous les posts")
                display_df = df_sorted[['timestamp', 'likesCount', 'videoPlayCount', 'commentsCount', 'url']].copy()
                st.dataframe(display_df, use_container_width=True)

# --- FIN DU CODE ---