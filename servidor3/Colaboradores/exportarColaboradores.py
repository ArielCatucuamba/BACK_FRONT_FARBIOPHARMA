"""Exportación del padrón completo al formato de registro de Nómina."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


CABECERAS = (
    'Cédula', 'NOMBRE', 'EMPRESA', 'ESTADO COLABORADOR',
    'DEPARTAMENTO', 'AREA', 'CARGO',
)

# No usa los parámetros de búsqueda ni la paginación de la pantalla.
# Los LEFT JOIN conservan colaboradores con asignaciones incompletas.
CONSULTA_COLABORADORES = """
    SELECT col.CEDULA, col.NOMBRE, empresa.NOMBRE, col.ESTADO,
           departamento.DEPARTAMENTO, area.AREA, cargo.DESCRIPCION
    FROM Colaboradores col
    LEFT JOIN Empresas empresa ON col.EMPRESA = empresa.ID_EMPRESA
    LEFT JOIN Cargos cargo ON col.CARGO = cargo.ID_CARGOS
    LEFT JOIN Departamentos departamento ON cargo.DEPARTAMENTO = departamento.ID_DEPARTAMENTOS
    LEFT JOIN Areas area ON cargo.AREA = area.ID_AREAS
    ORDER BY col.NOMBRE ASC, col.ID_COLABORADOR ASC
"""


def generar_excel_colaboradores(cursor):
    """Devuelve un XLSX de una hoja; el llamador administra el cursor."""
    libro = Workbook(write_only=True)
    hoja = libro.create_sheet('Colaboradores')
    hoja.freeze_panes = 'A2'
    hoja.sheet_view.showGridLines = False
    for columna, ancho in zip('ABCDEFG', (15, 48, 25, 24, 38, 45, 60)):
        hoja.column_dimensions[columna].width = ancho
    hoja.row_dimensions[1].height = 44

    linea = Side(style='thin', color='000000')
    borde = Border(left=linea, right=linea, top=linea, bottom=linea)
    cabeceras = []
    for titulo in CABECERAS:
        celda = WriteOnlyCell(hoja, value=titulo)
        celda.font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        celda.fill = PatternFill('solid', fgColor='1F437D')
        celda.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        celda.border = borde
        cabeceras.append(celda)
    hoja.append(cabeceras)

    total = 0
    try:
        cursor.execute(CONSULTA_COLABORADORES)
        while True:
            filas = cursor.fetchmany(500)
            if not filas:
                break
            for fila in filas:
                celdas = []
                for valor in fila:
                    celda = WriteOnlyCell(hoja, value='' if valor is None else str(valor))
                    # Las entradas son texto, incluso si comienzan por =, +, - o @.
                    # Evita fórmulas procedentes de datos y conserva la cédula literal.
                    celda.data_type = 's'
                    celda.number_format = '@'
                    celda.font = Font(name='Calibri', size=11, color='000000')
                    celda.alignment = Alignment(vertical='center', wrap_text=True)
                    celda.border = borde
                    celdas.append(celda)
                hoja.append(celdas)
                total += 1
        hoja.auto_filter.ref = f'A1:G{total + 1}'
        salida = BytesIO()
        libro.save(salida)
        salida.seek(0)
        return salida
    finally:
        libro.close()
