"""Utilidades pequeñas compartidas entre dominios del monolito."""
import math

from flask import request, url_for


PAGE_SIZE = 10


def _paginas_visibles(pagina, paginas):
    if paginas <= 7:
        return list(range(1, paginas + 1))
    if pagina <= 4:
        centro = range(2, 6)
    elif pagina >= paginas - 3:
        centro = range(paginas - 4, paginas)
    else:
        centro = range(pagina - 1, pagina + 2)
    numeros = sorted({1, paginas, *centro})
    resultado = []
    anterior = 0
    for numero in numeros:
        if anterior and numero - anterior > 1:
            resultado.append(None)
        resultado.append(numero)
        anterior = numero
    return resultado


def rol_normalizado(rol):
    return ''.join(str(rol or '').strip().lower().split())


def paginar_consulta(cursor, consulta, parametros, consulta_total, parametros_total=()):
    try:
        pagina = max(1, int(request.args.get('page', '1')))
    except (TypeError, ValueError):
        pagina = 1
    if parametros_total:
        cursor.execute(consulta_total, tuple(parametros_total))
    else:
        cursor.execute(consulta_total)
    total = int(cursor.fetchone()[0] or 0)
    paginas = max(1, math.ceil(total / PAGE_SIZE))
    pagina = min(pagina, paginas)
    cursor.execute(consulta + " LIMIT %s OFFSET %s", tuple(parametros) + (PAGE_SIZE, (pagina - 1) * PAGE_SIZE))
    datos = cursor.fetchall()
    def url_pagina(numero):
        query_args = request.args.to_dict()
        query_args.pop('format', None)
        query_args['page'] = numero
        return url_for(request.endpoint, **query_args)

    enlaces = [
        {'page': numero, 'url': url_pagina(numero)} if numero is not None else {'ellipsis': True}
        for numero in _paginas_visibles(pagina, paginas)
    ] if total else []
    return datos, {
        'page': pagina, 'pages': paginas, 'total': total,
        'start': (pagina - 1) * PAGE_SIZE + 1 if total else 0,
        'end': min(pagina * PAGE_SIZE, total),
        'previous_url': url_pagina(pagina - 1) if pagina > 1 else None,
        'next_url': url_pagina(pagina + 1) if pagina < paginas else None,
        'page_links': enlaces,
    }
