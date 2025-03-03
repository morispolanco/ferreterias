import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from io import BytesIO

# Configuración inicial
st.set_page_config(page_title="Inventario Ferretería", layout="wide")
st.title("Sistema de Inventario - Ferretería")

# Archivos
CSV_FILE = "inventario_ferreteria.csv"
HISTORIAL_FILE = "historial_cambios.csv"
USERS = {"admin": "ferreteria123"}  # Usuario y contraseña simples

# Función para cargar inventario
@st.cache_data
def cargar_inventario():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=["ID", "Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"])

# Función para guardar inventario
def guardar_inventario(df):
    df.to_csv(CSV_FILE, index=False)

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
    # Cargar inventario
    inventario = cargar_inventario()

    # Barra lateral
    menu = st.sidebar.selectbox(
        "Menú",
        ["Ver Inventario", "Agregar Producto", "Buscar Producto", "Editar Producto", "Eliminar Producto", "Reporte", "Historial"]
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
            # Filtros
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
            
            # Resaltar bajo stock o agotados
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
            
            # Gráfico de categorías
            fig = px.bar(inventario.groupby("Categoría")["Cantidad"].sum().reset_index(), 
                        x="Categoría", y="Cantidad", title="Cantidad por Categoría")
            st.plotly_chart(fig)

            # Generar PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            elements.append(Paragraph("Reporte de Inventario", style=TableStyle([('FONTSIZE', (0, 0), (-1, -1), 14)])))
            data = [inventario.columnstolist()] + inventario.values.tolist()
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

    # Nota al final
    st.markdown("---")
    st.write(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
