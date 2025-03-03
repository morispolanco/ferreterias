import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from io import BytesIO

# Configuración inicial
st.set_page_config(page_title="Inventario Ferretería", layout="wide")
st.title("Sistema de Inventario - Ferretería")

# Archivos
CSV_FILE = "inventario_ferreteria.csv"
HISTORIAL_FILE = "historial_cambios.csv"
VENTAS_FILE = "ventas.csv"
USERS = {"admin": "ferreteria123"}  # Usuario y contraseña simples

# Datos de demostración con precios en dos decimales
DEMO_DATA = pd.DataFrame({
    "ID": ["001", "002", "003", "004", "005"],
    "Producto": ["Taladro Eléctrico", "Pintura Blanca", "Tornillos 1/4", "Martillo", "Cable 10m"],
    "Categoría": ["Herramientas", "Pinturas", "Materiales", "Herramientas", "Electricidad"],
    "Cantidad": [10, 5, 100, 8, 15],
    "Precio": [150.50, 25.75, 0.10, 12.00, 8.90],  # Precios ya con dos decimales
    "Proveedor": ["Bosch", "Sherwin", "Genérico", "Truper", "Voltex"],
    "Última Actualización": ["2025-03-02 10:00:00", "2025-03-01 15:30:00", "2025-02-28 09:15:00", 
                            "2025-03-01 12:00:00", "2025-03-02 14:20:00"]
})

# Función para cargar inventario (redondear precios a dos decimales)
def cargar_inventario():
    if not os.path.exists(CSV_FILE):
        DEMO_DATA.to_csv(CSV_FILE, index=False)
        return DEMO_DATA.copy()
    df = pd.read_csv(CSV_FILE)
    df["Precio"] = df["Precio"].round(2)  # Redondear precios a dos decimales al cargar
    return df

# Función para guardar inventario (asegurar dos decimales)
def guardar_inventario(df):
    df["Precio"] = df["Precio"].round(2)  # Redondear precios antes de guardar
    df.to_csv(CSV_FILE, index=False)

# Función para cargar ventas
def cargar_ventas():
    if os.path.exists(VENTAS_FILE):
        df = pd.read_csv(VENTAS_FILE)
        df["Precio Unitario"] = df["Precio Unitario"].round(2)  # Redondear precios en ventas también
        df["Total"] = df["Total"].round(2)
        return df
    return pd.DataFrame(columns=["Fecha", "ID", "Producto", "Cantidad Vendida", "Precio Unitario", "Total", "Usuario"])

# Función para guardar ventas
def guardar_ventas(df):
    df["Precio Unitario"] = df["Precio Unitario"].round(2)
    df["Total"] = df["Total"].round(2)
    df.to_csv(VENTAS_FILE, index=False)

# Registrar cambios en historial
def registrar_cambio(accion, id_producto, usuario):
    historial = pd.DataFrame({
        "Fecha": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Acción": [accion],
        "ID Producto": [id_producto],
        "Usuario": [usuario]
    })
    if os.path.exists(HISTORIAL_FILE):
        historial_existente = pd.read_csv(HISTORIAL_FILE)
        historial = pd.concat([historial_existente, historial], ignore_index=True)
    historial.to_csv(HISTORIAL_FILE, index=False)

# Autenticación
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("Iniciar Sesión")
    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")
    if st.button("Iniciar Sesión"):
        if usuario in USERS and USERS[usuario] == contraseña:
            st.session_state.authenticated = True
            st.session_state.usuario = usuario
            st.success("Sesión iniciada con éxito!")
        else:
            st.error("Usuario o contraseña incorrectos.")
else:
    # Cargar inventario y ventas
    inventario = cargar_inventario()
    ventas = cargar_ventas()

    # Barra lateral con menú
    menu = st.sidebar.selectbox(
        "Menú",
        ["Ver Inventario", "Registrar Ventas", "Cargar CSV", "Agregar Producto", "Buscar Producto", 
         "Editar Producto", "Eliminar Producto", "Reporte", "Historial"]
    )
    st.sidebar.write(f"Usuario: {st.session_state.usuario}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.session_state.pop("usuario")

    # Opción 1: Ver Inventario
    if menu == "Ver Inventario":
        st.subheader("Inventario Actual")
        if inventario.empty:
            st.warning("El inventario está vacío.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                categoria_filtro = st.selectbox("Filtrar por Categoría", ["Todas"] + inventario["Categoría"].unique().tolist())
            with col2:
                proveedor_filtro = st.selectbox("Filtrar por Proveedor", ["Todos"] + inventario["Proveedor"].unique().tolist())
            
            inventario_filtrado = inventario
            if categoria_filtro != "Todas":
                inventario_filtrado = inventario_filtrado[inventario_filtrado["Categoría"] == categoria_filtro]
            if proveedor_filtro != "Todos":
                inventario_filtrado = inventario_filtrado[inventario_filtrado["Proveedor"] == proveedor_filtro]
            
            def color_stock(row):
                if row["Cantidad"] == 0:
                    return ['background-color: red'] * len(row)
                elif row["Cantidad"] < 5:
                    return ['background-color: yellow'] * len(row)
                return [''] * len(row)
            
            # Formatear precios a dos decimales en la visualización
            st.dataframe(inventario_filtrado.style.apply(color_stock, axis=1).format({"Precio": "{:.2f}"}))
            st.download_button(
                label="Descargar Inventario como CSV",
                data=inventario_filtrado.to_csv(index=False),
                file_name=f"inventario_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    # Opción 2: Registrar Ventas
    elif menu == "Registrar Ventas":
        st.subheader("Registrar Ventas del Día")
        inventario["ID"] = inventario["ID"].astype(str)
        productos_disponibles = [f"{row['Producto']} (ID: {row['ID']}, Stock: {row['Cantidad']})" 
                                for _, row in inventario.iterrows() if row['Cantidad'] > 0]
        
        with st.form(key="ventas_form"):
            if productos_disponibles:
                producto_seleccionado = st.selectbox("Selecciona un Producto", productos_disponibles)
                cantidad_vendida = st.number_input("Cantidad Vendida", min_value=1, step=1)
                submit_venta = st.form_submit_button(label="Registrar Venta")

                if submit_venta:
                    try:
                        id_venta = producto_seleccionado.split("ID: ")[1].split(",")[0].strip()
                        st.write(f"ID extraído para depuración: '{id_venta}'")  # Depuración

                        if id_venta in inventario["ID"].values:
                            producto = inventario[inventario["ID"] == id_venta].iloc[0]
                            if producto["Cantidad"] >= cantidad_vendida:
                                inventario.loc[inventario["ID"] == id_venta, "Cantidad"] -= cantidad_vendida
                                inventario.loc[inventario["ID"] == id_venta, "Última Actualización"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                guardar_inventario(inventario)

                                total_venta = cantidad_vendida * producto["Precio"]
                                nueva_venta = pd.DataFrame({
                                    "Fecha": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                    "ID": [id_venta],
                                    "Producto": [producto["Producto"]],
                                    "Cantidad Vendida": [cantidad_vendida],
                                    "Precio Unitario": [producto["Precio"]],
                                    "Total": [total_venta],
                                    "Usuario": [st.session_state.usuario]
                                })
                                ventas = pd.concat([ventas, nueva_venta], ignore_index=True)
                                guardar_ventas(ventas)

                                registrar_cambio("Venta", id_venta, st.session_state.usuario)
                                st.success(f"Venta registrada: {cantidad_vendida} de '{producto['Producto']}' por ${total_venta:.2f}")
                                inventario = cargar_inventario()
                            else:
                                st.error(f"No hay suficiente stock. Disponible: {producto['Cantidad']}")
                        else:
                            st.error(f"El ID '{id_venta}' no se encontró en el inventario. IDs disponibles: {list(inventario['ID'])}")
                    except IndexError:
                        st.error("Error al procesar el producto seleccionado. Verifica el formato del menú.")
            else:
                st.warning("No hay productos en stock para vender.")

        st.subheader("Ventas Registradas Hoy")
        hoy = datetime.now().strftime("%Y-%m-%d")
        ventas_hoy = ventas[ventas["Fecha"].str.startswith(hoy)]
        if not ventas_hoy.empty:
            # Formatear precios a dos decimales en la visualización de ventas
            st.dataframe(ventas_hoy.style.format({"Precio Unitario": "{:.2f}", "Total": "{:.2f}"}))
            total_dia = ventas_hoy["Total"].sum()
            st.write(f"**Total de Ventas del Día:** ${total_dia:.2f}")
        else:
            st.info("No hay ventas registradas para hoy.")

    # Opción 3: Cargar CSV
    elif menu == "Cargar CSV":
        st.subheader("Cargar Inventario desde CSV")
        uploaded_file = st.file_uploader("Selecciona un archivo CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                nuevo_inventario = pd.read_csv(uploaded_file)
                columnas_esperadas = ["ID", "Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]
                if not all(col in nuevo_inventario.columns for col in columnas_esperadas):
                    st.error("El CSV debe contener las columnas: ID, Producto, Categoría, Cantidad, Precio, Proveedor, Última Actualización")
                else:
                    if nuevo_inventario["ID"].duplicated().any():
                        st.error("El CSV contiene IDs duplicados. Corrige el archivo y vuelve a intentarlo.")
                    elif nuevo_inventario["Cantidad"].lt(0).any() or nuevo_inventario["Precio"].lt(0).any():
                        st.error("Cantidad y Precio no pueden ser negativos.")
                    else:
                        # Redondear precios a dos decimales antes de cargar
                        nuevo_inventario["Precio"] = nuevo_inventario["Precio"].round(2)
                        st.write("Vista previa del CSV:")
                        st.dataframe(nuevo_inventario.style.format({"Precio": "{:.2f}"}))
                        if st.button("Confirmar Carga"):
                            inventario = nuevo_inventario.copy()
                            guardar_inventario(inventario)
                            registrar_cambio("Cargar CSV", "Todos", st.session_state.usuario)
                            st.success("Inventario actualizado desde el CSV con éxito!")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
        st.info("Asegúrate de que el CSV tenga el formato correcto.")

    # Opción 4: Agregar Producto (con CSV)
    elif menu == "Agregar Producto":
        st.subheader("Agregar Productos desde CSV")
        uploaded_file = st.file_uploader("Selecciona un archivo CSV con nuevos productos", type=["csv"])
        if uploaded_file is not None:
            try:
                nuevos_productos = pd.read_csv(uploaded_file)
                columnas_esperadas = ["ID", "Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]
                if not all(col in nuevos_productos.columns for col in columnas_esperadas):
                    st.error("El CSV debe contener las columnas: ID, Producto, Categoría, Cantidad, Precio, Proveedor, Última Actualización")
                else:
                    if nuevos_productos["ID"].duplicated().any():
                        st.error("El CSV contiene IDs duplicados entre sí. Corrige el archivo y vuelve a intentarlo.")
                    elif nuevos_productos["ID"].isin(inventario["ID"]).any():
                        st.error("Algunos IDs en el CSV ya existen en el inventario. Usa IDs únicos.")
                    elif nuevos_productos["Cantidad"].lt(0).any() or nuevos_productos["Precio"].lt(0).any():
                        st.error("Cantidad y Precio no pueden ser negativos.")
                    else:
                        # Redondear precios a dos decimales antes de agregar
                        nuevos_productos["Precio"] = nuevos_productos["Precio"].round(2)
                        st.write("Vista previa de los nuevos productos:")
                        st.dataframe(nuevos_productos.style.format({"Precio": "{:.2f}"}))
                        if st.button("Confirmar Agregado"):
                            inventario = pd.concat([inventario, nuevos_productos], ignore_index=True)
                            guardar_inventario(inventario)
                            for id_prod in nuevos_productos["ID"]:
                                registrar_cambio("Agregar", id_prod, st.session_state.usuario)
                            st.success(f"{len(nuevos_productos)} producto(s) agregado(s) con éxito!")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
        st.info("Asegúrate de que el CSV tenga el formato correcto y IDs únicos.")

    # Opción 5: Buscar Producto
    elif menu == "Buscar Producto":
        st.subheader("Buscar Producto")
        busqueda = st.text_input("Ingrese ID, Nombre o Proveedor")
        if busqueda:
            resultado = inventario[
                inventario["ID"].str.contains(busqueda, case=False, na=False) |
                inventario["Producto"].str.contains(busqueda, case=False, na=False) |
                inventario["Proveedor"].str.contains(busqueda, case=False, na=False)
            ]
            if not resultado.empty:
                st.dataframe(resultado.style.format({"Precio": "{:.2f}"}))
            else:
                st.warning("No se encontraron productos con ese criterio.")

    # Opción 6: Editar Producto
    elif menu == "Editar Producto":
        st.subheader("Editar Producto")
        id_editar = st.text_input("Ingrese el ID del producto a editar")
        if id_editar and id_editar in inventario["ID"].values:
            producto = inventario[inventario["ID"] == id_editar].iloc[0]
            with st.form(key="editar_form"):
                nombre = st.text_input("Nombre del Producto", value=producto["Producto"])
                categoria = st.selectbox("Categoría", ["Herramientas", "Materiales", "Pinturas", "Electricidad", "Otros"], 
                                       index=["Herramientas", "Materiales", "Pinturas", "Electricidad", "Otros"].index(producto["Categoría"]))
                cantidad = st.number_input("Cantidad", min_value=0, step=1, value=int(producto["Cantidad"]))
                precio = st.number_input("Precio Unitario", min_value=0.0, step=0.01, value=float(producto["Precio"]), format="%.2f")
                proveedor = st.text_input("Proveedor", value=producto["Proveedor"])
                submit_edit = st.form_submit_button(label="Guardar Cambios")

                if submit_edit:
                    inventario.loc[inventario["ID"] == id_editar, ["Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]] = \
                        [nombre, categoria, cantidad, round(precio, 2), proveedor, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                    guardar_inventario(inventario)
                    registrar_cambio("Editar", id_editar, st.session_state.usuario)
                    st.success(f"Producto con ID '{id_editar}' actualizado con éxito!")
        elif id_editar:
            st.error("ID no encontrado en el inventario.")

    # Opción 7: Eliminar Producto
    elif menu == "Eliminar Producto":
        st.subheader("Eliminar Producto")
        id_eliminar = st.text_input("Ingrese el ID del producto a eliminar")
        if id_eliminar and id_eliminar in inventario["ID"].values:
            producto = inventario[inventario["ID"] == id_eliminar].iloc[0]
            st.write(f"Producto a eliminar: {producto['Producto']} (Cantidad: {producto['Cantidad']})")
            confirmar = st.button("Confirmar Eliminación")
            if confirmar:
                inventario = inventario[inventario["ID"] != id_eliminar]
                guardar_inventario(inventario)
                registrar_cambio("Eliminar", id_eliminar, st.session_state.usuario)
                st.success(f"Producto con ID '{id_eliminar}' eliminado con éxito!")
        elif id_eliminar:
            st.error("ID no encontrado en el inventario.")

    # Opción 8: Reporte
    elif menu == "Reporte":
        st.subheader("Reporte del Inventario")
        if inventario.empty:
            st.warning("No hay datos para generar un reporte.")
        else:
            total_valor = (inventario["Cantidad"] * inventario["Precio"]).sum()
            bajo_stock = inventario[inventario["Cantidad"] < 5]
            st.write(f"**Valor Total del Inventario:** ${total_valor:.2f}")
            st.write(f"**Productos con Bajo Stock (menos de 5 unidades):** {len(bajo_stock)}")
            if not bajo_stock.empty:
                st.dataframe(bajo_stock.style.format({"Precio": "{:.2f}"}))
            
            fig = px.bar(inventario.groupby("Categoría")["Cantidad"].sum().reset_index(), 
                        x="Categoría", y="Cantidad", title="Cantidad por Categoría")
            st.plotly_chart(fig)

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            title_style = ParagraphStyle(
                name='Title',
                fontSize=14,
                leading=16,
                alignment=1,
                spaceAfter=12
            )
            elements.append(Paragraph("Reporte de Inventario", title_style))
            data = [inventario.columns.tolist()] + inventario.values.tolist()
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            doc.build(elements)
            st.download_button(
                label="Descargar Reporte como PDF",
                data=buffer.getvalue(),
                file_name=f"reporte_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

    # Opción 9: Historial
    elif menu == "Historial":
        st.subheader("Historial de Cambios")
        if os.path.exists(HISTORIAL_FILE):
            historial = pd.read_csv(HISTORIAL_FILE)
            st.dataframe(historial)
        else:
            st.info("No hay historial de cambios registrado aún.")

    # Nota al final
    st.markdown("---")
    st.write(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
