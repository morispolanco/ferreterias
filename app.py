""")

uploaded_file = st.file_uploader("Selecciona un archivo CSV", type=["csv"])
if uploaded_file is not None:
    try:
        nuevo_inventario = pd.read_csv(uploaded_file)
        columnas_esperadas = ["ID", "Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]
        columnas_requeridas = columnas_esperadas.copy()
        
        # Validar columnas
        if not all(col in nuevo_inventario.columns for col in columnas_requeridas):
            st.error(f"El CSV debe contener las columnas obligatorias: {', '.join(columnas_requeridas)}.")
        else:
            # Validar tipos y formatos básicos
            try:
                nuevo_inventario["Cantidad"] = nuevo_inventario["Cantidad"].astype(int)
                nuevo_inventario["Precio"] = nuevo_inventario["Precio"].astype(float)
                pd.to_datetime(nuevo_inventario["Última Actualización"], format="%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                st.error(f"Error en los datos: {str(e)}. Verifica que 'Cantidad' sea entero, 'Precio' sea número y 'Última Actualización' esté en formato `YYYY-MM-DD HH:MM:SS`.")
                st.stop()

            # Validaciones adicionales
            if nuevo_inventario["ID"].duplicated().any():
                st.error("El CSV contiene IDs duplicados. Corrige el archivo y vuelve a intentarlo.")
            elif nuevo_inventario["Cantidad"].lt(0).any():
                st.error("La columna 'Cantidad' no puede contener valores negativos.")
            elif nuevo_inventario["Precio"].lt(0).any():
                st.error("La columna 'Precio' no puede contener valores negativos.")
            else:
                nuevo_inventario["Precio"] = nuevo_inventario["Precio"].round(2)
                if "Demanda Estimada" not in nuevo_inventario.columns:
                    nuevo_inventario["Demanda Estimada"] = 0.0
                else:
                    nuevo_inventario["Demanda Estimada"] = nuevo_inventario["Demanda Estimada"].fillna(0.0).round(2)
                
                st.write("Vista previa del CSV:")
                st.dataframe(nuevo_inventario.style.format({"Precio": "{:.2f}", "Demanda Estimada": "{:.2f}"}))
                if st.button("Confirmar Carga"):
                    inventario = nuevo_inventario.copy()
                    guardar_inventario(inventario)
                    registrar_cambio("Cargar CSV", "Todos", st.session_state.usuario)
                    st.success("Inventario actualizado desde el CSV con éxito!")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}. Verifica el formato y contenido del CSV.")

# Opción 4: Reabastecer Stock
elif menu == "Reabastecer Stock":
st.subheader("Reabastecer Stock desde CSV")
uploaded_file = st.file_uploader("Selecciona un archivo CSV con nuevos productos", type=["csv"])
if uploaded_file is not None:
    try:
        nuevos_productos = pd.read_csv(uploaded_file)
        columnas_esperadas = ["ID", "Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]
        if not all(col in nuevos_productos.columns for col in columnas_esperadas):
            st.error("El CSV debe contener las columnas: ID, Producto, Categoría, Cantidad, Precio, Proveedor, Última Actualización")
        else:
            if nuevos_productos["ID"].duplicated().any():
                st.error("El CSV contiene IDs duplicados entre sí.")
            elif nuevos_productos["ID"].isin(inventario["ID"]).any():
                st.error("Algunos IDs en el CSV ya existen en el inventario.")
            elif nuevos_productos["Cantidad"].lt(0).any() or nuevos_productos["Precio"].lt(0).any():
                st.error("Cantidad y Precio no pueden ser negativos.")
            else:
                nuevos_productos["Precio"] = nuevos_productos["Precio"].round(2)
                if "Demanda Estimada" not in nuevos_productos.columns:
                    nuevos_productos["Demanda Estimada"] = 0.0
                st.write("Vista previa de los nuevos productos:")
                st.dataframe(nuevos_productos.style.format({"Precio": "{:.2f}", "Demanda Estimada": "{:.2f}"}))
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
        st.dataframe(resultado.style.format({"Precio": "{:.2f}", "Demanda Estimada": "{:.2f}"}))
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
        st.dataframe(bajo_stock.style.format({"Precio": "{:.2f}", "Demanda Estimada": "{:.2f}"}))
    
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
