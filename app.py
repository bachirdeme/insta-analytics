import streamlit as st
import pandas as pd
import requests
import time
import os

# --- CONFIGURATION ---
API_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = "shu8hvrXbJbY3Eb9W"  # L'ID de l'Instagram Scraper

st.set_page_config(page_title="Insta Analytics", layout="wide")
st.title("📊 Analyseur de Performance Instagram")

# --- INTERFACE ---
url_input = st.text_input("Lien du profil Instagram", "https://www.instagram.com/cedricgrolet/")
limit = st.slider("Nombre de posts à analyser", 5, 50, 10)

if st.button("🚀 Lancer l'analyse"):
    with st.status("Communication avec Apify en cours...") as status:
        
        # 1. ENVOI DU POST (Comme ton tRESTClient 1)
        run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={API_TOKEN}"
        payload = {
            "directUrls": [url_input],
            "resultsLimit": limit,
            "resultsType": "posts"
        }
        
        res_post = requests.post(run_url, json=payload)
        run_data = res_post.json()
        run_id = run_data["data"]["id"]
        dataset_id = run_data["data"]["defaultDatasetId"]
        
        # 2. ATTENTE (Le scraper doit travailler)
        status.update(label="Le scraper travaille sur Instagram... patientez.")
        time.sleep(15) # On attend un peu que les premiers résultats arrivent
        
        # 3. RÉCUPÉRATION DU GET (Comme ton tRESTClient 2)
        get_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_TOKEN}&format=json"
        res_get = requests.get(get_url)
        data = res_get.json()
        
        status.update(label="Analyse terminée !", state="complete")

    if data:
        df = pd.DataFrame(data)

        # --- NETTOYAGE & CALCULS ---
        # On s'assure que les colonnes numériques sont bien des nombres
        df['likesCount'] = pd.to_numeric(df['likesCount'], errors='coerce').fillna(0)
        df['videoPlayCount'] = pd.to_numeric(df['videoPlayCount'], errors='coerce').fillna(0)
        
        # Calcul de la visibilité totale (Likes + Vues)
        df['Total_Visibility'] = df['likesCount'] + df['videoPlayCount']

        # --- AFFICHAGE DES TOP PERFORMANCES ---
        st.subheader("🏆 Top des Posts par Visibilité")
        
        # On trie par visibilité décroissante
        df_sorted = df.sort_values(by='Total_Visibility', ascending=False)

        # Affichage en colonnes des 3 meilleurs
        top3 = df_sorted.head(3)
        cols = st.columns(3)
        for i, (index, row) in enumerate(top3.iterrows()):
            with cols[i]:
                st.image(row['displayUrl'], use_container_width=True)
                st.metric("❤️ Likes", f"{int(row['likesCount']):,}")
                st.metric("👁️ Vues", f"{int(row['videoPlayCount']):,}")
                st.write(f"[Voir le post]({row['url']})")

        # --- TABLEAU COMPLET ---
        st.subheader("📋 Liste détaillée des posts")
        st.dataframe(df_sorted[['timestamp', 'likesCount', 'videoPlayCount', 'commentsCount', 'url']], 
                     use_container_width=True)
    else:
        st.error("Aucune donnée trouvée. Vérifie l'URL du profil.")