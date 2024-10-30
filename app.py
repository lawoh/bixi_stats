import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os
import matplotlib.pyplot as plt
import folium
from folium import plugins
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# Définition des couleurs BIXI
BIXI_COLORS = {
    'blue': '#2D2E83',
    'red': '#BC1E45',
    'white': '#FFFFFF',
    'light_gray': '#F8F9FA'
}

# Définition des fonds de carte disponibles
BASEMAPS = {
    'OpenStreetMap': {
        'tiles': 'cartodbpositron',
        'attr': '© OpenStreetMap contributors'
    },
    'Satellite': {
        'tiles': 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        'attr': '© Google Maps'
    },
    'Terrain': {
        'tiles': 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
        'attr': '© Google Maps'
    },
    'Sombre': {
        'tiles': 'cartodbdark_matter',
        'attr': '© OpenStreetMap contributors'
    }
}

# CSS personnalisé
css = f"""
<style>
    .stApp {{
        background-color: {BIXI_COLORS['white']};
    }}
    
    .header-container {{
        padding: 2rem;
        background-color: {BIXI_COLORS['red']};
        color: {BIXI_COLORS['white']};
        border-radius: 0 0 20px 20px;
        margin-bottom: 2rem;
        text-align: center;
    }}
    
    .main-title {{
        color: {BIXI_COLORS['white']};
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }}
    
    .metric-card {{
        background-color: {BIXI_COLORS['white']};
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 0.5rem;
        text-align: center;
    }}
    
    .metric-title {{
        color: {BIXI_COLORS['blue']};
        font-size: 1rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }}
    
    .metric-value {{
        color: {BIXI_COLORS['red']};
        font-size: 1.5rem;
        font-weight: bold;
    }}
    
    .section-header {{
        color: {BIXI_COLORS['blue']};
        font-size: 1.2rem;
        font-weight: bold;
        margin: 1.5rem 0;
        text-align: left;
    }}
    
    @media (max-width: 768px) {{
        .metric-card {{
            text-align: center;
            margin: 1rem 0;
        }}
        
        .section-header {{
            text-align: center;
        }}
    }}
    
    div[data-baseweb="select"] {{
        background-color: {BIXI_COLORS['white']};
        border-radius: 8px;
        border: 2px solid {BIXI_COLORS['blue']};
    }}
</style>
"""

@st.cache_data
def charger_donnees(annee):
    """
    Charge et analyse les données BIXI pour une année spécifique.
    
    Args:
        annee (str): L'année pour laquelle charger les données
        
    Returns:
        dict: Dictionnaire contenant toutes les analyses calculées
    """
    resultats = {}
    chemin_bixis = './bixis'
    chemin_annee = os.path.join(chemin_bixis, str(annee))
    
    try:
        # Chargement du fichier des stations
        stations_file = f"Stations_{annee}.csv"
        stations_path = os.path.join(chemin_annee, stations_file)
        df_stations = pd.read_csv(stations_path)
        if len(df_stations.columns) == 1 and ';' in df_stations.columns[0]:
            df_stations = pd.read_csv(stations_path, sep=';')
            
        # Création du GeoDataFrame pour les stations
        geometry = [Point(xy) for xy in zip(df_stations['longitude'], df_stations['latitude'])]
        gdf_stations = gpd.GeoDataFrame(df_stations, geometry=geometry, crs="EPSG:4326")
        
        # Chargement des fichiers de trajets
        fichiers = [f for f in os.listdir(chemin_annee) 
                   if f.endswith('.csv') and not f.startswith('Stations')]
        
        df_list = []
        for fichier in fichiers:
            chemin_complet = os.path.join(chemin_annee, fichier)
            df = pd.read_csv(chemin_complet, low_memory=False)
            df_list.append(df)

        df_annee = pd.concat(df_list, ignore_index=True)
        df_annee['start_date'] = pd.to_datetime(df_annee['start_date'])
        df_annee['end_date'] = pd.to_datetime(df_annee['end_date'])

        # Calcul des différentes statistiques
        resultats['stations'] = gdf_stations
        resultats['duree_moyenne'] = df_annee['duration_sec'].mean() / 60
        
        trajets_boucle = df_annee[df_annee['start_station_code'] == df_annee['end_station_code']]
        resultats['proportion_boucle'] = (len(trajets_boucle) / len(df_annee)) * 100
        
        resultats['membres'] = len(df_annee[df_annee['is_member'] == 1])
        resultats['occasionnels'] = len(df_annee[df_annee['is_member'] == 0])
        
        # Analyse de la répartition par période
        df_annee['hour'] = df_annee['start_date'].dt.hour
        bins = [0, 6, 12, 18, 24]
        labels = ['0h-6h', '6h-12h', '12h-18h', '18h-24h']
        df_annee['period'] = pd.cut(df_annee['hour'], bins=bins, labels=labels, include_lowest=True)
        compte_periodes = df_annee['period'].value_counts()
        resultats['repartition_periodes'] = (compte_periodes / len(df_annee)) * 100

        return resultats
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return None

def creer_carte(gdf_stations):
    """Crée une carte Folium avec clustering des stations"""
    # Création de la carte avec OpenStreetMap par défaut
    carte = folium.Map(
        location=[45.5236, -73.5985],
        zoom_start=12,
        tiles=None  # On commence sans fond de carte
    )
    
    # Ajout des différents fonds de carte disponibles
    
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='© Google Maps',
        name='Satellite',
        control=True
    ).add_to(carte)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
        attr='© Google Maps',
        name='Terrain',
        control=True
    ).add_to(carte)

    folium.TileLayer(
        tiles='cartodbdark_matter',
        attr='© OpenStreetMap contributors',
        name='Sombre',
        control=True
    ).add_to(carte)

    folium.TileLayer(
        tiles='cartodbpositron',
        attr='© OpenStreetMap contributors',
        name='OpenStreetMap',
        control=True
    ).add_to(carte)

    # Création du cluster de marqueurs
    marker_cluster = MarkerCluster(
        name='Stations BIXI',
        overlay=True,
        control=True
    )

    # Ajout des stations au cluster
    for _, station in gdf_stations.iterrows():
        folium.CircleMarker(
            location=[float(station.geometry.y), float(station.geometry.x)],
            radius=10,
            popup=f"<b>{station['name']}</b>",
            color=BIXI_COLORS['red'],
            fill=True,
            fill_color=BIXI_COLORS['red'],
            fill_opacity=0.7,
            weight=2
        ).add_to(marker_cluster)

    marker_cluster.add_to(carte)
    
    # Ajout du contrôle de couches en haut à droite
    folium.LayerControl(position='topright').add_to(carte)
    
    return carte

def main():
    # Injection du CSS
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(f"""
        <div class="header-container">
            <h1 class="main-title">Analyse des données BIXI Montréal</h1>
        </div>
    """, unsafe_allow_html=True)

    # Liste des années disponibles
    chemin_bixis = './bixis'
    annees_disponibles = [d for d in os.listdir(chemin_bixis) 
                       if os.path.isdir(os.path.join(chemin_bixis, d))]
    annees_disponibles.sort()

    # Sélecteur d'année uniquement
    annee_selectionnee = st.selectbox(
        'Sélectionnez une année',
        annees_disponibles,
        index=annees_disponibles.index('2014')
    )

    # Chargement des données
    resultats_annee = charger_donnees(annee_selectionnee)

    if resultats_annee:
        # Affichage des métriques
        st.markdown('<div class="section-header">Statistiques générales</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Durée moyenne des trajets</div>
                    <div class="metric-value">{resultats_annee['duree_moyenne']:.1f} min</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Proportion de boucles</div>
                    <div class="metric-value">{resultats_annee['proportion_boucle']:.1f}%</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Trajets membres</div>
                    <div class="metric-value">{resultats_annee['membres']:,}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Trajets occasionnels</div>
                    <div class="metric-value">{resultats_annee['occasionnels']:,}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('<br>', unsafe_allow_html=True)
        
        # Visualisations
        col_carte, col_graphe = st.columns(2, gap="small")
        
        with col_carte:
            st.markdown('<div class="section-header">Stations BIXI</div>', unsafe_allow_html=True)
            carte = creer_carte(resultats_annee['stations'])
            st_folium(carte, width=None, height=500)
        
        with col_graphe:
            st.markdown('<div class="section-header">Répartition des trajets par période</div>', unsafe_allow_html=True)
            
            fig, ax = plt.subplots(figsize=(10, 8))
            donnees_triees = resultats_annee['repartition_periodes'].sort_values(ascending=False)
            
            bars = donnees_triees.plot(
                kind='bar',
                ax=ax,
                color=BIXI_COLORS['red'],
                width=0.7
            )
            
            plt.xticks(rotation=45)
            ax.set_ylabel('')
            ax.tick_params(colors=BIXI_COLORS['blue'])
            
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            ax.yaxis.grid(True, linestyle='--', alpha=0.7)
            ax.set_axisbelow(True)
            
            plt.tight_layout(pad=0.5)
            
            st.pyplot(fig)

        # Footer
        st.markdown(f"""
            <div style='text-align: center; color: #666; padding: 20px; margin-top: 0.5rem;'>
                Analyse des données BIXI Montréal par Laouali ADA AYA - {annee_selectionnee}
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    st.set_page_config(page_title="Analyse Bixi", layout="wide")
    main()
