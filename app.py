import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from folium import Popup
from io import BytesIO

st.set_page_config(page_title="Optimización de Rutas", layout="wide")

LAT_ORIGEN = -33.28436
LON_ORIGEN = -70.84775

archivo = st.file_uploader("📤 Sube el archivo Excel con los pedidos", type=["xlsx"])

if archivo:
    df = pd.read_excel(archivo)

    # Normalizar columnas
    df.columns = df.columns.str.strip().str.lower().str.normalize('NFKD') \
        .str.encode('ascii', errors='ignore').str.decode('utf-8')

    df["direccion"] = df["direccion"].fillna("").astype(str)
    df["cliente"] = df["cliente"].astype(str)
    df["latitud"] = df["latitud"].astype(float)
    df["longitud"] = df["longitud"].astype(float)

    total_pedidos = len(df)
    capacidad = {"1": 45, "2": 45, "3": 30}

    if "furgon" not in df.columns or df["furgon"].isnull().all():
        if total_pedidos <= capacidad["1"]:
            usados = ["1"]
        elif total_pedidos <= capacidad["1"] + capacidad["2"]:
            usados = ["1", "2"]
        else:
            usados = ["1", "2", "3"]

        total_capacidad = sum([capacidad[f] for f in usados])
        proporcion = {f: capacidad[f] / total_capacidad for f in usados}

        asignaciones = []
        acumulado = 0
        for f in usados:
            cantidad = round(proporcion[f] * total_pedidos)
            asignaciones.extend([f] * cantidad)
            acumulado += cantidad

        if acumulado < total_pedidos:
            asignaciones.extend([usados[-1]] * (total_pedidos - acumulado))
        elif acumulado > total_pedidos:
            asignaciones = asignaciones[:total_pedidos]

        df["furgon"] = asignaciones

    # Editor para modificar furgones
    st.markdown("### ✏️ Editar asignación de clientes a furgones")
    df_editable = st.data_editor(df.copy(), num_rows="dynamic")
    df_editable["furgon"] = df_editable["furgon"].astype(str)

    # Filtrar por furgón
    furgones_disponibles = sorted(df_editable["furgon"].unique())
    filtro_furgon = st.multiselect("🚚 Filtrar por furgón para visualizar en el mapa:", furgones_disponibles, default=furgones_disponibles)
    df_filtrado = df_editable[df_editable["furgon"].isin(filtro_furgon)]

    # Agrupación para mapa
    df_grouped = df_filtrado.groupby(["latitud", "longitud", "furgon"]).agg({
        "cliente": "count",
        "direccion": "first"
    }).reset_index().rename(columns={"cliente": "pedidos"})

    # Crear mapa
    mapa = folium.Map(location=[LAT_ORIGEN, LON_ORIGEN], zoom_start=12)
    colores = {"1": "red", "2": "blue", "3": "green"}

    folium.Marker(
        [LAT_ORIGEN, LON_ORIGEN],
        tooltip="Centro de distribución",
        icon=folium.Icon(color="orange", icon="truck", prefix="fa")
    ).add_to(mapa)

    for _, row in df_grouped.iterrows():
        popup_text = f"Dirección: {row['direccion']}<br>Pedidos: {row['pedidos']}<br>Furgón: {row['furgon']}"
        popup = Popup(popup_text, max_width=300)
        folium.Marker(
            location=[row["latitud"], row["longitud"]],
            popup=popup,
            tooltip=popup_text,
            icon=folium.Icon(color=colores.get(row["furgon"], "gray"))
        ).add_to(mapa)

    st.markdown("### 🗺️ Mapa de Rutas")
    folium_static(mapa)

    # Descargar resultado
    output = BytesIO()
    df_editable.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        label="📥 Descargar asignación editada (Excel)",
        data=output,
        file_name="asignacion_editada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
