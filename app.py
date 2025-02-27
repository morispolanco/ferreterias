import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
from authlib.integrations.requests_client import OAuth2Session
import os
import json

# Configuración de OpenID Connect (ajusta según tu proveedor)
OIDC_PROVIDER = {
    "authorization_endpoint": "https://dev-60yow3raw63cgke4.us.auth0.com",  # Ejemplo: Google
    "token_endpoint": "https://oauth2.googleapis.com/token",
    "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
    "client_id": "heDVFbcZy9EUDlf76Yki626Mfuup77ST",  # Reemplaza con tu Client ID del proveedor
    "client_secret": "TlnPlkvE8dzodXSevqaYJRUQQTiYejWc7MJia6P9-4MLLy3wk-PmFF-wuwaTzDQxu",  # Reemplaza con tu Client Secret
    "redirect_uri": "http://localhost:8501",  # URI de redirección de tu app
    "scope": "openid email profile"
}

# Conexión a la base de datos SQLite
conn = sqlite3.connect('ferreteria.db', check_same_thread=False)
c = conn.cursor()

# Crear tablas si no existen
c.execute('''CREATE TABLE IF NOT EXISTS inventario 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              producto TEXT UNIQUE, 
              cantidad INTEGER, 
              precio REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS cotizaciones 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              cliente TEXT, 
              total REAL, 
              fecha TEXT)''')
conn.commit()

# Configuración inicial de la aplicación
st.title("Gestor de Ferretería")

# Funciones auxiliares
@st.cache_data
def cargar_inventario(_conn):
    return pd.read_sql_query("SELECT producto, cantidad, precio FROM inventario", _conn)

def guardar_inventario(producto, cantidad, precio):
    c.execute("INSERT OR REPLACE INTO inventario (producto, cantidad, precio) VALUES (?, ?, ?)", 
              (producto, cantidad, precio))
    conn.commit()
    st.cache_data.clear()

def actualizar_inventario(producto, cantidad):
    c.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE producto = ?", (cantidad, producto))
    conn.commit()
    st.cache_data.clear()

def guardar_cotizacion(cliente, total):
    fecha = datetime.now().strftime('%Y-%m-%d')
    c.execute("INSERT INTO cotizaciones (cliente, total, fecha) VALUES (?, ?, ?)", 
              (cliente, total, fecha))
    conn.commit()

# Autenticación con OpenID Connect
def get_auth_url():
    client = OAuth2Session(OIDC_PROVIDER["client_id"], OIDC_PROVIDER["client_secret"], 
                           redirect_uri=OIDC_PROVIDER["redirect_uri"], scope=OIDC_PROVIDER["scope"])
    auth_uri, state = client.create_authorization_url(OIDC_PROVIDER["authorization_endpoint"])
    st.session_state["oidc_state"] = state
    return auth_uri

def handle_callback():
    if "code" in st.query_params and "oidc_state" in st.session_state:
        client = OAuth2Session(OIDC_PROVIDER["client_id"], OIDC_PROVIDER["client_secret"], 
                               redirect_uri=OIDC_PROVIDER["redirect_uri"], state=st.session_state["oidc_state"])
        token = client.fetch_token(OIDC_PROVIDER["token_endpoint"], code=st.query_params["code"])
        user_info = client.get(OIDC_PROVIDER["userinfo_endpoint"]).json()
        st.session_state["user"] = user_info
        st.session_state["token"] = token
        st.query_params.clear()

# Estado de autenticación
if "user" not in st.session_state:
    st.session_state["user"] = None

# Lógica de autenticación
if not st.session_state["user"]:
    st.write("Por favor, inicia sesión para acceder a la aplicación.")
    if st.button("Iniciar Sesión con OpenID"):
        auth_url = get_auth_url()
        st.markdown(f"[Haz clic aquí para autenticarte]({auth_url})")
    
    # Manejar callback de OIDC
    handle_callback()
else:
    st.sidebar.write(f"Bienvenido, {st.session_state['user']['email']}")
    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state["user"]
        del st.session_state["token"]
        st.session_state["oidc_state"] = None
        st.success("Sesión cerrada con éxito.")
        st.rerun()

    # Menú principal (solo visible si está autenticado)
    menu = st.sidebar.selectbox("Menú", ["Inventario", "Catálogo", "Cotizaciones", "Reportes"])

    # Sección 1: Gestión de Inventario
    if menu == "Inventario":
        st.header("Control de Inventario")
        
        with st.form(key='agregar_producto'):
            producto = st.text_input("Nombre del Producto")
            cantidad = st.number_input("Cantidad", min_value=0)
            precio = st.number_input("Precio Unitario", min_value=0.0, format="%.2f")
            submit = st.form_submit_button(label="Agregar Producto")
            
            if submit:
                guardar_inventario(producto, cantidad, precio)
                st.success(f"Producto '{producto}' agregado o actualizado con éxito.")
        
        st.subheader("Inventario Actual")
        inventario_df = cargar_inventario(conn)
        st.dataframe(inventario_df)
        
        stock_bajo = inventario_df[inventario_df["cantidad"] < 5]
        if not stock_bajo.empty:
            st.warning("¡Alerta! Productos con stock bajo:")
            st.write(stock_bajo)

    # Sección 2: Catálogo
    elif menu == "Catálogo":
        st.header("Catálogo de Productos")
        inventario_df = cargar_inventario(conn)
        if not inventario_df.empty:
            st.write("Lista de productos disponibles:")
            for index, row in inventario_df.iterrows():
                st.write(f"**{row['producto']}** - Cantidad: {row['cantidad']} - Precio: ${row['precio']:.2f}")
        else:
            st.info("No hay productos en el inventario aún.")

    # Sección 3: Cotizaciones
    elif menu == "Cotizaciones":
        st.header("Generar Cotización")
        
        cliente = st.text_input("Nombre del Cliente")
        inventario_df = cargar_inventario(conn)
        productos_cotizar = st.multiselect("Seleccionar Productos", inventario_df["producto"].tolist())
        cantidades = {}
        
        for prod in productos_cotizar:
            stock_disponible = inventario_df[inventario_df["producto"] == prod]["cantidad"].values[0]
            cantidades[prod] = st.number_input(f"Cantidad de {prod} (Stock: {stock_disponible})", 
                                               min_value=1, max_value=stock_disponible, key=prod)
        
        if st.button("Generar Cotización"):
            if cliente and productos_cotizar:
                error = False
                for prod in productos_cotizar:
                    stock_disponible = inventario_df[inventario_df["producto"] == prod]["cantidad"].values[0]
                    if cantidades[prod] > stock_disponible:
                        st.error(f"No hay suficiente stock de {prod}. Disponible: {stock_disponible}")
                        error = True
                        break
                
                if not error:
                    total = 0
                    cotizacion_detalle = []
                    for prod in productos_cotizar:
                        precio = inventario_df[inventario_df["producto"] == prod]["precio"].values[0]
                        subtotal = precio * cantidades[prod]
                        total += subtotal
                        cotizacion_detalle.append([prod, cantidades[prod], precio, subtotal])
                    
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt="Cotización - Ferretería", ln=True, align="C")
                    pdf.cell(200, 10, txt=f"Cliente: {cliente}", ln=True)
                    pdf.cell(200, 10, txt=f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
                    pdf.ln(10)
                    pdf.cell(50, 10, "Producto", 1)
                    pdf.cell(30, 10, "Cantidad", 1)
                    pdf.cell(30, 10, "Precio", 1)
                    pdf.cell(30, 10, "Subtotal", 1)
                    pdf.ln()
                    for item in cotizacion_detalle:
                        pdf.cell(50, 10, item[0], 1)
                        pdf.cell(30, 10, str(item[1]), 1)
                        pdf.cell(30, 10, f"${item[2]:.2f}", 1)
                        pdf.cell(30, 10, f"${item[3]:.2f}", 1)
                        pdf.ln()
                    pdf.cell(110, 10, "Total", 1)
                    pdf.cell(30, 10, f"${total:.2f}", 1)
                    
                    pdf_file = f"cotizacion_{cliente}_{datetime.now().strftime('%Y%m%d')}.pdf"
                    pdf.output(pdf_file)
                    
                    for prod in productos_cotizar:
                        actualizar_inventario(prod, cantidades[prod])
                    guardar_cotizacion(cliente, total)
                    
                    st.success("Cotización generada y stock actualizado.")
                    with open(pdf_file, "rb") as file:
                        st.download_button("Descargar Cotización", file, file_name=pdf_file)
            else:
                st.error("Por favor, completa todos los campos.")

    # Sección 4: Reportes
    elif menu == "Reportes":
        st.header("Reportes")
        cotizaciones_df = pd.read_sql_query("SELECT cliente, total, fecha FROM cotizaciones", conn)
        if cotizaciones_df.empty:
            st.info("No hay cotizaciones registradas aún.")
        else:
            st.subheader("Ventas Registradas")
            st.dataframe(cotizaciones_df)
            st.subheader("Ganancias Totales")
            st.write(f"${cotizaciones_df['total'].sum():.2f}")

# Instrucciones
st.sidebar.info("Instala: `pip install streamlit==1.42.0 pandas fpdf authlib` y ejecuta con `streamlit run nombre_del_archivo.py`.")
