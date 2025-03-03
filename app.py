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

# Datos de demostración
DEMO_DATA = pd.DataFrame({
    "ID": ["001", "002", "003", "004", "005"],
    "Producto": ["Taladro Eléctrico", "Pintura Blanca", "Tornillos 1/4", "Martillo", "Cable 10m"],
    "Categoría": ["Herramientas", "Pinturas", "Materiales", "Herramientas", "Electricidad"],
    "Cantidad": [10, 5, 100, 8, 15],
    "Precio": [150.50, 25.75, 0.10, 12.00, 8.90],
    "Proveedor": ["Bosch", "Sherwin", "Genérico", "Truper", "Voltex"],
    "Última Actualización": ["2025-03-02 10:00:00", "2025-03-01 15:30:00", "2025-02-28 09:15:00", 
                            "2025-03-01 12:00:00", "2025-03-02 14:20:00"]
})

# Función para cargar inventario (sin caché para siempre reflejar el archivo actualizado)
def cargar_inventario():
    if not os.path.exists(CSV_FILE):
        DEMO_DATA.to_csv(CSV_FILE, index=False)
        return DEMO_DATA.copy()
    return pd.read_csv(CSV_FILE)

# Función para guardar inventario
def guardar_inventario(df):
    df.to_csv(CSV_FILE, index=False)

# Función para cargar ventas
def cargar_ventas():
    if os.path.exists(VENTAS_FILE):
        return pd.read_csv(VENTAS_FILE)
    return pd.DataFrame(columns=["Fecha", "ID", "Producto", "Cantidad Vendida", "Precio Unitario", "Total", "Usuario"])

# Función para guardar ventas
def guardar_ventas(df):
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
    # Cargar inventario y ventas (recargamos cada vez para reflejar cambios)
    inventario = cargar_inventario()
    ventas = cargar_ventas()

    # Barra lateral
    menu = st.sidebar.selectbox(
        "Menú",
        ["Ver Inventario", "Agregar Producto", "Buscar Producto", "Editar Producto", "Eliminar Producto", 
         "Reporte", "Historial", "Cargar CSV", "Registrar Ventas"]
    )
    st.sidebar.write(f"Usuario: {st.session_state.usuario}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.session_state.pop("usuario")

    # Opción: Cargar CSV
    if menu == "Cargar CSV":
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
                        st.write("Vista previa del CSV:")
                        st.dataframe(nuevo_inventario)
                        if st.button("Confirmar Carga"):
                            inventario = nuevo_inventario.copy()
                            guardar_inventario(inventario)
                            registrar_cambio("Cargar CSV", "Todos", st.session_state.usuario)
                            st.success("Inventario actualizado desde el CSV con éxito!")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
        st.info("El CSV debe tener las columnas: ID, Producto, Categoría, Cantidad, Precio, Proveedor, Última Actualización.")

    # Opción 1: Ver Inventario
    elif menu == "Ver Inventario":
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
            
            st.dataframe(inventario_filtrado.style.apply(color_stock, axis=1))
            st.download_button(
                label="Descargar Inventario como CSV",
                data=inventario_filtrado.to_csv(index=False),
                file_name=f"inventario_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    # Opción 2: Agregar Producto
    elif menu == "Agregar Producto":
        st.subheader("Agregar Nuevo Producto")
        with st.form(key="agregar_form"):
            id_producto = st.text_input("ID del Producto (único)")
            nombre = st.text_input("Nombre del Producto")
            categoria = st.selectbox("Categoría", ["Herramientas", "Materiales", "Pinturas", "Electricidad", "Otros"])
            cantidad = st.number_input("Cantidad", min_value=0, step=1)
            precio = st.number_input("Precio Unitario", min_value=0.0, step=0.01)
            proveedor = st.text_input("Proveedor")
            submit_button = st.form_submit_button(label="Agregar")

            if submit_button:
                if not id_producto or not nombre:
                    st.error("El ID y el Nombre son obligatorios.")
                elif id_producto in inventario["ID"].values:
                    st.error("El ID ya existe. Use uno diferente.")
                else:
                    nuevo_producto = pd.DataFrame({
                        "ID": [id_producto],
                        "Producto": [nombre],
                        "Categoría": [categoria],
                        "Cantidad": [cantidad],
                        "Precio": [precio],
                        "Proveedor": [proveedor],
                        "Última Actualización": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                    })
                    inventario = pd.concat([inventario, nuevo_producto], ignore_index=True)
                    guardar_inventario(inventario)
                    registrar_cambio("Agregar", id_producto, st.session_state.usuario)
                    st.success(f"Producto '{nombre}' agregado con éxito!")

    # Opción 3: Buscar Producto
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
                st.dataframe(resultado)
            else:
                st.warning("No se encontraron productos con ese criterio.")

    # Opción 4: Editar Producto
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
                precio = st.number_input("Precio Unitario", min_value=0.0, step=0.01, value=float(producto["Precio"]))
                proveedor = st.text_input("Proveedor", value=producto["Proveedor"])
                submit_edit = st.form_submit_button(label="Guardar Cambios")

                if submit_edit:
                    inventario.loc[inventario["ID"] == id_editar, ["Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]] = \
                        [nombre, categoria, cantidad, precio, proveedor, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                    guardar_inventario(inventario)
                    registrar_cambio("Editar", id_editar, st.session_state.usuario)
                    st.success(f"Producto con ID '{id_editar}' actualizado con éxito!")
        elif id_editar:
            st.error("ID no encontrado en el inventario.")

    # Opción 5: Eliminar Producto
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

    # Opción 6: Reporte
    elif menu == "Reporte":
        st.subheader("Reporte del Inventario")
        if inventario.empty:
            st.warning("No hay datos para generar un reporte.")
        else:
            total_valor = (inventario["Cantidad"] * inventario["Precio"]).sum()
            bajo_stock = inventario[inventario["Cantidad"] < 5]
            st.write(f"**Valor Total del Inventario:** ${total_valor:,.2f}")
            st.write(f"**Productos con Bajo Stock (menos de 5 unidades):** {len(bajo_stock)}")
            if not bajo_stock.empty:
                st.dataframe(bajo_stock)
            
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

    # Opción 7: Historial
    elif menu == "Historial":
        st.subheader("Historial de Cambios")
        if os.path.exists(HISTORIAL_FILE):
            historial = pd.read_csv(HISTORIAL_FILE)
            st.dataframe(historial.sort_values("Fecha", ascending=False))
        else:
            st.info("No hay historial de cambios registrado aún.")

    # Opción 8: Registrar Ventas
    elif menu == "Registrar Ventas":
        st.subheader("Registrar Ventas del Día")
        # Asegurar que IDs sean strings
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
                        # Extraer ID del producto seleccionado
                        id_venta = producto_seleccionado.split("ID: ")[1].split(",")[0].strip()
                        st.write(f"ID extraído para depuración: '{id_venta}'")  # Depuración

                        # Verificar que el ID existe en el inventario
                        if id_venta in inventario["ID"].values:
                            producto = inventario[inventario["ID"] == id_venta].iloc[0]
                            if producto["Cantidad"] >= cantidad_vendida:
                                # Actualizar inventario
                                inventario.loc[inventario["ID"] == id_venta, "Cantidad"] -= cantidad_vendida
                                inventario.loc[inventario["ID"] == id_venta, "Última Actualización"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                guardar_inventario(inventario)

                                # Registrar venta
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

                                # Registrar en historial
                                registrar_cambio("Venta", id_venta, st.session_state.usuario)
                                st.success(f"Venta registrada: {cantidad_vendida} de '{producto['Producto']}' por ${total_venta:,.2f}")

                                # Recargar inventario para reflejar cambios inmediatamente
                                inventario = cargar_inventario()
                            else:
                                st.error(f"No hay suficiente stock. Disponible: {producto['Cantidad']}")
                        else:
                            st.error(f"El ID '{id_venta}' no se encontró en el inventario. IDs disponibles: {list(inventario['ID'])}")
                    except IndexError:
                        st.error("Error al procesar el producto seleccionado. Verifica el formato del menú.")
            else:
                st.warning("No hay productos en stock para vender.")

        # Mostrar ventas del día
        st.subheader("Ventas Registradas Hoy")
        hoy = datetime.now().strftime("%Y-%m-%d")
        ventas_hoy = ventas[ventas["Fecha"].str.startswith(hoy)]
        if not ventas_hoy.empty:
            st.dataframe(ventas_hoy)
            total_dia = ventas_hoy["Total"].sum()
            st.write(f"**Total de Ventas del Día:** ${total_dia:,.2f}")
        else:
            st.info("No hay ventas registradas para hoy.")

    # Nota al final
    st.markdown("---")
    st.write(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
