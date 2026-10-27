"""
Módulo de Inicialização e Fábrica da Aplicação (Application Factory Pattern).
Configura a instância do Flask, banco de dados relacional SQLite (logistics.db),
filtros customizados do Jinja2 e registro dos Blueprints de rotas.
"""

import os
from flask import Flask
from flask_cors import CORS
from app.models import db, Driver, Vehicle, ServiceSchedule
from app.routes import main_bp, api_bp
from app.services import format_cpf


def create_app(test_config=None) -> Flask:
    """
    Cria e configura a instância do aplicativo Flask.
    Implementa o padrão Application Factory para facilitar testes e modularidade.
    """
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )

    # Configurações do Banco de Dados SQLite
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(base_dir, 'logistics.db')

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'logistics-fleet-secure-secret-key-2026'),
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_AS_ASCII=False
    )

    if test_config:
        app.config.update(test_config)

    # Habilita CORS para permitir chamadas assíncronas
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Inicialização do SQLAlchemy com a aplicação
    db.init_app(app)

    # Registro de filtros customizados no motor de templates Jinja2
    @app.template_filter('format_cpf')
    def jinja_format_cpf(value):
        """Filtro Jinja para formatação de CPF em tabelas HTML."""
        if not value:
            return ""
        return format_cpf(str(value))

    @app.template_filter('format_date')
    def jinja_format_date(value):
        """Filtro Jinja para conversão de datas (YYYY-MM-DD -> DD/MM/YYYY)."""
        if not value:
            return ""
        if hasattr(value, 'strftime'):
            return value.strftime('%d/%m/%Y')
        try:
            parts = str(value).split('-')
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass
        return str(value)

    # Registro dos Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # Criação automática de tabelas e carregamento inicial de demonstração
    with app.app_context():
        db.create_all()
        # Se for a primeira execução e o banco estiver vazio, carrega dados de demonstração
        _auto_seed_initial_data()

    return app


def _auto_seed_initial_data():
    """Popula registros iniciais caso a base esteja totalmente vazia."""
    from datetime import date, timedelta
    if Driver.query.first() is None:
        # Motoristas iniciais com CPFs matematicamente válidos
        drivers = [
            Driver(name='Carlos Eduardo Silva', tax_id='83138865007'),
            Driver(name='Mariana Souza Santos', tax_id='52998224725'),
            Driver(name='Rodrigo Pereira Lima', tax_id='11144477735'),
            Driver(name='Fernanda Oliveira Castro', tax_id='45826978809'),
        ]
        db.session.add_all(drivers)
        db.session.commit()

        # Veículos da frota
        vehicles = [
            Vehicle(model='Mercedes-Benz Sprinter 416', color='Branco', license_plate='BRA2E19', is_active=True),
            Vehicle(model='Volkswagen Delivery Express', color='Prata', license_plate='LOG8F24', is_active=True),
            Vehicle(model='Renault Master Furgão', color='Azul', license_plate='FLX4A55', is_active=True),
            Vehicle(model='Fiat Fiorino Endurance', color='Branco', license_plate='AGD9K82', is_active=True),
            Vehicle(model='Iveco Daily 35S15', color='Vermelho', license_plate='TRK7B31', is_active=False),
        ]
        db.session.add_all(vehicles)
        db.session.commit()

        # Agendamentos distribuídos na semana
        today = date.today()
        schedules = [
            ServiceSchedule(
                schedule_date=today,
                driver_id=drivers[0].id,
                vehicle_id=vehicles[0].id,
                client_name='Supermercados Horizonte Ltda',
                delivery_address='Av. Paulista, 1578 - Bela Vista, São Paulo - SP',
                order_number='NF-104928',
                notes='Entrega de perecíveis na doca 3 com agendamento prioritário.',
                status='IN_PROGRESS'
            ),
            ServiceSchedule(
                schedule_date=today,
                driver_id=drivers[1].id,
                vehicle_id=vehicles[1].id,
                client_name='TechLog Distribuidora',
                delivery_address='Rua Funchal, 418 - Vila Olímpia, São Paulo - SP',
                order_number='NF-104929',
                notes='Carga frágil com equipamentos de informática.',
                status='SCHEDULED'
            ),
            ServiceSchedule(
                schedule_date=today + timedelta(days=1),
                driver_id=drivers[2].id,
                vehicle_id=vehicles[2].id,
                client_name='Farmácias Central Vida',
                delivery_address='Rua Vergueiro, 2030 - Paraíso, São Paulo - SP',
                order_number='NF-104930',
                notes='Transporte de medicamentos com monitoramento térmico.',
                status='SCHEDULED'
            ),
            ServiceSchedule(
                schedule_date=today + timedelta(days=2),
                driver_id=drivers[0].id,
                vehicle_id=vehicles[3].id,
                client_name='Construções & Reformas Aliança',
                delivery_address='Estrada do Campo Limpo, 890 - São Paulo - SP',
                order_number='NF-104931',
                notes='Entrega matutina de ferramentas elétricas.',
                status='SCHEDULED'
            ),
            ServiceSchedule(
                schedule_date=today - timedelta(days=1),
                driver_id=drivers[3].id,
                vehicle_id=vehicles[0].id,
                client_name='Mega Atacadista Sul',
                delivery_address='Av. dos Bandeirantes, 3200 - Planalto Paulista, SP',
                order_number='NF-104920',
                notes='Entrega finalizada com canhoto digital assinado.',
                status='COMPLETED'
            ),
        ]
        db.session.add_all(schedules)
        db.session.commit()
