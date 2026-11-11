from .autenticacion import bp as auth_bp
from .directorioTelefonico import bp as directory_bp
from .estructuraOrganizacional import bp as structure_bp
from .jerarquia import bp as hierarchy_bp
from .colaboradores import bp as collaborators_bp
from .telecomunicaciones import bp as telecom_bp
from .flota import bp as fleet_bp

BLUEPRINTS = (auth_bp, directory_bp, structure_bp, hierarchy_bp, collaborators_bp, telecom_bp, fleet_bp)
