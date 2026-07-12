"""
Helper Utilities
================
General utility functions for icons, downloads, and UI elements.
"""

import pandas as pd
import streamlit as st
from io import BytesIO


def icon(name: str, size: str = "", color: str = "") -> str:
    """Genera HTML para un Bootstrap Icon.
    
    Args:
        name: Nombre del icono (sin prefijo 'fa-')
        size: 'lg' para grande, '' para normal
        color: 'green', 'yellow', 'red' para colores semáforo
    
    Returns:
        HTML string del icono
    """
    classes = f"fas fa-{name}"
    if size == "lg":
        classes += " fa-lg"
    if color:
        classes += f" status-{color}"
    return f'<i class="{classes}"></i>'


def icon_text(icon_name: str, text: str, size: str = "") -> str:
    """Genera HTML para icono + texto."""
    return f'{icon(icon_name, size)} {text}'


def descargar_datos_grafico(df: pd.DataFrame, nombre_archivo: str, titulo: str = "Descargar datos"):
    """
    Genera un botón de descarga Excel para los datos de un gráfico.
    
    Args:
        df: DataFrame con los datos del gráfico
        nombre_archivo: Nombre base del archivo (sin extensión)
        titulo: Texto del botón
    """
    if df is not None and not df.empty:
        # Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Datos')
        excel_data = output.getvalue()
        st.download_button(
            label=titulo,
            data=excel_data,
            file_name=f"{nombre_archivo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_{nombre_archivo}_{hash(nombre_archivo) % 10000}",
            icon=":material/download:"
        )
