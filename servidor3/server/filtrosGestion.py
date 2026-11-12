"""Búsqueda y opciones de filtros sobre el conjunto completo de cada gestión."""
import re

from flask import request

from .utilidades import paginar_consulta


# Solo estas columnas, definidas por el servidor, pueden formar la búsqueda.
CAMPOS_BUSQUEDA = {
    'structure.crud_areas': ('AREA',),
    'structure.departamentos': ('DEPARTAMENTO',),
    'structure.ubicaciones': ('DESCRIPCION', 'DIRECCION', 'GEOLOCALIZACION'),
    'structure.crud_cargos': ('c.DESCRIPCION', 'a.AREA', 'd.DEPARTAMENTO'),
    'fleet.crud_empresas': ('NOMBRE',),
    'fleet.crud_vehiculos': ('PLACA', 'MARCA', 'MODELO', 'COLOR', 'CONDUCTOR_ASIGNADO'),
    'collaborators.crud_colaboradores': ('col.CEDULA', 'col.NOMBRE', 'c.DESCRIPCION', 'a.AREA', 'd.DEPARTAMENTO'),
    'telecom.crud_extensiones': ('c.NOMBRE', 'e.EXTENSION', 'a.AREA', 'd.DEPARTAMENTO'),
    'telecom.crud_celulares': ('col.NOMBRE', 'c.CELULAR', 'a.AREA', 'd.DEPARTAMENTO'),
    'telecom.crud_correos': ('col.NOMBRE', 'c.CORREO', 'a.AREA', 'd.DEPARTAMENTO'),
    'hierarchy.crud_jerarquia': ('c.DESCRIPCION', 's.DESCRIPCION', 'j.PLANTA', 'a.AREA', 'd.DEPARTAMENTO'),
}


def paginar_gestion(cursor, consulta, parametros, consulta_total, parametros_total=()):
    campos = CAMPOS_BUSQUEDA[request.endpoint]
    base, orden = re.split(r'\bORDER\s+BY\b', consulta, flags=re.IGNORECASE)
    origen = re.split(r'\bFROM\b', base, maxsplit=1, flags=re.IGNORECASE)[1]
    condiciones = []
    valores = list(parametros)
    termino = (request.args.get('q') or '').strip()
    departamento = (request.args.get('departamento') or '').strip()
    area = (request.args.get('area') or '').strip()
    if termino:
        condiciones.append('(' + ' OR '.join(f'CAST({campo} AS CHAR) LIKE %s' for campo in campos) + ')')
        valores.extend([f'%{termino}%'] * len(campos))
    filtros = {}
    if 'a.AREA' in campos:
        cursor.execute("SELECT DISTINCT DEPARTAMENTO FROM Departamentos WHERE DEPARTAMENTO IS NOT NULL AND DEPARTAMENTO <> '' ORDER BY DEPARTAMENTO")
        filtros['departamentos'] = [fila[0] for fila in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT AREA FROM Areas WHERE AREA IS NOT NULL AND AREA <> '' ORDER BY AREA")
        filtros['areas'] = [fila[0] for fila in cursor.fetchall()]
        cursor.execute('SELECT DISTINCT a.AREA, d.DEPARTAMENTO FROM ' + origen)
        filtros['relaciones'] = [{'area': fila[0], 'departamento': fila[1]} for fila in cursor.fetchall() if fila[0] and fila[1]]
        if departamento:
            condiciones.append('d.DEPARTAMENTO = %s')
            valores.append(departamento)
        if area:
            condiciones.append('a.AREA = %s')
            valores.append(area)
    where = ' WHERE ' + ' AND '.join(condiciones) if condiciones else ''
    datos, paginacion = paginar_consulta(
        cursor, base + where + ' ORDER BY ' + orden, tuple(valores),
        'SELECT COUNT(*) FROM ' + origen + where, tuple(valores),
    )
    paginacion['filters'] = filtros
    return datos, paginacion
