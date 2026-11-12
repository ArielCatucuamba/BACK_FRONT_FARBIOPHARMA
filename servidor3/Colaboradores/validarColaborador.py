"""Validación común para crear y editar los datos de Nómina."""
import re

ESTADOS_COLABORADOR = ('ACTIVO', 'INACTIVO', 'FAMILIAR')


def validar_colaborador(formulario, cursor, colaborador_id=None):
    datos = {campo: str(formulario.get(campo) or '').strip()
             for campo in ('cedula', 'nombre', 'empresa', 'cargo', 'ubicacion', 'estado')}
    datos['estado'] = datos['estado'].upper()
    if not all(datos.values()):
        raise ValueError('Cédula, nombre, empresa, cargo, ubicación y estado son obligatorios.')
    if not re.fullmatch(r'[0-9]{10}', datos['cedula']):
        raise ValueError('La cédula debe contener exactamente 10 dígitos.')
    if len(datos['nombre']) > 100 or not any(letra.isalpha() for letra in datos['nombre']):
        raise ValueError('El nombre debe contener letras y tener como máximo 100 caracteres.')
    if datos['estado'] not in ESTADOS_COLABORADOR:
        raise ValueError('Selecciona un estado válido: ACTIVO, INACTIVO o FAMILIAR.')
    for campo, tabla, clave, etiqueta in (
        ('empresa', 'Empresas', 'ID_EMPRESA', 'empresa'),
        ('ubicacion', 'Ubicaciones', 'ID_UBICACIONES', 'ubicación'),
    ):
        if not re.fullmatch(r'[0-9]{1,10}', datos[campo]) or not 0 < int(datos[campo]) <= 2147483647:
            raise ValueError(f'Selecciona una {etiqueta} válida.')
        cursor.execute(f'SELECT {clave} FROM {tabla} WHERE {clave} = %s', (int(datos[campo]),))
        if not cursor.fetchone():
            raise ValueError(f'La {etiqueta} seleccionada no existe.')
        datos[campo] = int(datos[campo])
    if not datos['cargo'].isascii() or not datos['cargo'].isdigit():
        cursor.execute('SELECT ID_CARGOS FROM Cargos WHERE DESCRIPCION = %s LIMIT 2', (datos['cargo'],))
        cargos = cursor.fetchall()
        if len(cargos) != 1:
            raise ValueError('Selecciona un cargo válido de la lista.')
        datos['cargo'] = str(cargos[0][0])
    if not re.fullmatch(r'[0-9]{1,10}', datos['cargo']) or not 0 < int(datos['cargo']) <= 2147483647:
        raise ValueError('Selecciona un cargo válido de la lista.')
    datos['cargo'] = int(datos['cargo'])
    cursor.execute('SELECT AREA, DEPARTAMENTO FROM Cargos WHERE ID_CARGOS = %s', (datos['cargo'],))
    contexto = cursor.fetchone()
    if not contexto or contexto[0] is None or contexto[1] is None:
        raise ValueError('El cargo debe tener área y departamento asignados.')
    for campo, valor in zip(('area', 'departamento'), contexto):
        recibido = str(formulario.get(campo) or '').strip()
        if recibido and (not re.fullmatch(r'[0-9]{1,10}', recibido) or int(recibido) != valor):
            raise ValueError('El área y departamento deben corresponder al cargo seleccionado.')
    consulta = 'SELECT ID_COLABORADOR FROM Colaboradores WHERE CEDULA = %s'
    parametros = (datos['cedula'],)
    if colaborador_id is not None:
        consulta += ' AND ID_COLABORADOR <> %s'
        parametros += (colaborador_id,)
    cursor.execute(consulta + ' LIMIT 1', parametros)
    if cursor.fetchone():
        raise ValueError('La cédula ya está registrada en otro colaborador.')
    return datos
