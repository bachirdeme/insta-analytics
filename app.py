import streamlit as st
import pandas as pd
import requests
import time
import os

# --- CONFIGURATION DES SECRETS ---
# Streamlit Cloud cherchera dans "Secrets", en local il cherchera dans tes variables d'env
API_TOKEN = st.secrets.get("APIFY_API_TOKEN") or os.getenv("APIFY_API_TOKEN")
ACTOR_ID = "shu8hvrXbJbY3Eb9W" 

st.set_page_config(page_title="Insta Analytics", layout="wide")
st.title("📊 Analyseur de Performance Instagram")

# --- FONCTION AVEC CACHE (1 HEURE) ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_instagram_data(insta_url, num_posts):
    if not API_TOKEN:
        return {"error": "Clé API manquante. Configurez APIFY_API_TOKEN dans les secrets."}

    # 1. Lancement du Run (POST)
    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={API_TOKEN}"
    payload = {
        "directUrls": [insta_url],
        "resultsLimit": num_posts,
        "resultsType": "posts"
    }
    
    try:
        res_post = requests.post(run_url, json=payload)
        if res_post.status_code != 201:
            return {"error": f"Apify Error {res_post.status_code}: {res_post.text}"}
        
        run_data = res_post.json()
        dataset_id = run_data.get("data", {}).get("defaultDatasetId")
        
        if not dataset_id:
            return {"error": "Impossible de récupérer l'ID du dataset."}

        # 2. Attente de sécurité (On peut améliorer ça, mais 15s est un bon début)
        time.sleep(15)
        
        # 3. Récupération des données (GET)
        get_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_TOKEN}&format=json"
        res_get = requests.get(get_url)
        return res_get.json()
        
    except Exception as e:
        return {"error": str(e)}

# --- INTERFACE ---
# L'URL est maintenant vide par défaut ou utilise un exemple, mais c'est l'utilisateur qui décide
url_input = st.text_input("Lien du profil Instagram", placeholder="https://www.instagram.com/nom_du_compte/")
limit = st.slider("Nombre de posts à analyser", 5, 50, 10)

if st.button("🚀 Lancer l'analyse"):
    if not url_input:
        st.warning("Veuillez entrer une URL Instagram.")
    else:
        with st.status("Récupération des données (API Apify)...") as status:
            data = get_instagram_data(url_input, limit)
            
            if isinstance(data, dict) and "error" in data:
                status.update(label="Erreur détectée", state="error")
                st.error(data["error"])
            elif not data:
                status.update(label="Aucune donnée", state="error")
                st.error("L'API n'a retourné aucun résultat. Le profil est peut-être privé ou l'URL est fausse.")
            else:
                status.update(label="Données récupérées !", state="complete")
                
                df = pd.DataFrame(data)

                # --- NETTOYAGE & CALCULS ---
                df['likesCount'] = pd.to_numeric(df['likesCount'], errors='coerce').fillna(0)
                df['videoPlayCount'] = pd.to_numeric(df['videoPlayCount'], errors='coerce').fillna(0)
                df['Total_Visibility'] = df['likesCount'] + df['videoPlayCount']

                # --- AFFICHAGE DES TOP PERFORMANCES ---
                st.subheader("🏆 Top des Posts par Visibilité")
                df_sorted = df.sort_values(by='Total_Visibility', ascending=False)

                top3 = df_sorted.head(3)
                cols = st.columns(3)
                for i, (index, row) in enumerate(top3.iterrows()):
                    with cols[i]:
                        # Gestion de l'image (si absente)
                        img = row.get('displayUrl') or "https://via.placeholder.com/300"
                        st.image(img, use_container_width=True)
                        st.metric("❤️ Likes", f"{int(row['likesCount']):,}")
                        st.metric("👁️ Vues", f"{int(row['videoPlayCount']):,}")
                        st.write(f"[Voir le post]({row.get('url', '#')})")

                # --- TABLEAU COMPLET ---
                st.subheader("📋 Liste détaillée des posts")
                # On ne prend que les colonnes qui existent vraiment
                cols_target = ['timestamp', 'likesCount', 'videoPlayCount', 'commentsCount', 'url']
                cols_present = [c for c in cols_target if c in df.columns]
                st.dataframe(df_sorted[cols_present], use_container_width=True)
                
                st.caption("ℹ️ Les résultats sont mis en cache pendant 1 heure pour économiser vos crédits.")