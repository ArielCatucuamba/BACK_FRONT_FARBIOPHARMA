"""Punto de entrada compatible con Docker: `python app.py`."""
import os
import time

from server import create_app
from server.extensiones import mysql

app = create_app()


def wait_for_db(max_retries=20):
    """Espera a MySQL sin cargar ni sincronizar modelos ni ejecutar migraciones."""
    for attempt in range(1, max_retries + 1):
        try:
            with app.app_context():
                cursor = mysql.connection.cursor()
                cursor.execute('SELECT 1')
                cursor.close()
            app.logger.info('Conexión a MySQL establecida')
            return
        except Exception as error:
            app.logger.warning('MySQL aún no está disponible (%s/%s): %s', attempt, max_retries, type(error).__name__)
            if attempt < max_retries:
                time.sleep(3)
    raise RuntimeError(f'No se pudo conectar a MySQL después de {max_retries} intentos')


if __name__ == '__main__':
    wait_for_db()
    app.run(host='0.0.0.0', debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
