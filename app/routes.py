"""
Módulo de Rotas HTTP e Controladores REST (Flask Blueprint).
Expõe as interfaces de páginas (templates Jinja2) e os endpoints de API RESTful
para integração assíncrona (Fetch API) com modais, FullCalendar e máscaras.
"""

from datetime import date, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.models import db, Driver, Vehicle, ServiceSchedule
from app.services import (
    BusinessRuleException,
    ConflictException,
    DriverService,
    VehicleService,
    ScheduleService,
    format_cpf
)

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')


# ==============================================================================
# TRATAMENTO CENTRALIZADO DE EXCEÇÕES DA API
# ==============================================================================

@api_bp.errorhandler(ConflictException)
def handle_conflict_exception(error):
    """Retorna erro 409 em caso de colisão de horário/escala."""
    return jsonify({
        'success': False,
        'error_type': 'CONFLICT',
        'message': error.message
    }), 409


@api_bp.errorhandler(BusinessRuleException)
def handle_business_rule_exception(error):
    """Retorna erro com código customizado para violações de validação."""
    return jsonify({
        'success': False,
        'error_type': 'VALIDATION_ERROR',
        'message': error.message
    }), error.status_code


@api_bp.errorhandler(Exception)
def handle_unexpected_exception(error):
    """Tratamento genérico para erros inesperados com segurança."""
    return jsonify({
        'success': False,
        'error_type': 'INTERNAL_SERVER_ERROR',
        'message': 'Ocorreu um erro interno ao processar a requisição. Tente novamente.'
    }), 500


# ==============================================================================
# ROTAS DE PÁGINAS (FRONTEND VIEWS)
# ==============================================================================

@main_bp.route('/')
def index_view():
    """Redireciona a raiz para o Painel de Agendamento (Calendário)."""
    return redirect(url_for('main.calendar_view'))


@main_bp.route('/calendar')
def calendar_view():
    """Renderiza a visualização principal do Calendário Logístico interativo."""
    drivers = DriverService.get_all()
    vehicles = VehicleService.get_all(active_only=True)
    metrics = ScheduleService.get_dashboard_metrics()
    return render_template(
        'calendar.html',
        active_page='calendar',
        drivers=drivers,
        vehicles=vehicles,
        metrics=metrics
    )


@main_bp.route('/drivers')
def drivers_view():
    """Renderiza a página de Gestão e Cadastro de Motoristas."""
    search = request.args.get('search', '')
    drivers = DriverService.get_all(search=search)
    return render_template(
        'drivers.html',
        active_page='drivers',
        drivers=drivers,
        search=search
    )


@main_bp.route('/vehicles')
def vehicles_view():
    """Renderiza a página de Gestão e Cadastro de Veículos da Frota."""
    search = request.args.get('search', '')
    vehicles = VehicleService.get_all(search=search)
    return render_template(
        'vehicles.html',
        active_page='vehicles',
        vehicles=vehicles,
        search=search
    )


# ==============================================================================
# ENDPOINTS REST: MOTORISTAS (DRIVERS API)
# ==============================================================================

@api_bp.route('/drivers', methods=['GET'])
def list_drivers():
    """Lista motoristas em formato JSON, com suporte a busca textual."""
    search = request.args.get('search')
    drivers = DriverService.get_all(search=search)
    return jsonify({
        'success': True,
        'data': [d.to_dict(include_stats=True) for d in drivers]
    })


@api_bp.route('/drivers/<int:driver_id>', methods=['GET'])
def get_driver(driver_id: int):
    """Retorna detalhes de um motorista específico por ID."""
    driver = DriverService.get_by_id(driver_id)
    return jsonify({
        'success': True,
        'data': driver.to_dict(include_stats=True)
    })


@api_bp.route('/drivers', methods=['POST'])
def create_driver():
    """Cadastra um novo motorista validando CPF e unicidade."""
    data = request.get_json() or {}
    driver = DriverService.create(data)
    return jsonify({
        'success': True,
        'message': f"Motorista '{driver.name}' cadastrado com sucesso!",
        'data': driver.to_dict()
    }), 201


@api_bp.route('/drivers/<int:driver_id>', methods=['PUT'])
def update_driver(driver_id: int):
    """Atualiza dados cadastrais de um motorista."""
    data = request.get_json() or {}
    driver = DriverService.update(driver_id, data)
    return jsonify({
        'success': True,
        'message': f"Dados do motorista '{driver.name}' atualizados com sucesso!",
        'data': driver.to_dict()
    })


@api_bp.route('/drivers/<int:driver_id>', methods=['DELETE'])
def delete_driver(driver_id: int):
    """Remove um motorista se não houver agendamentos ativos vinculados."""
    DriverService.delete(driver_id)
    return jsonify({
        'success': True,
        'message': "Motorista removido com sucesso!"
    })


# ==============================================================================
# ENDPOINTS REST: VEÍCULOS (VEHICLES API)
# ==============================================================================

@api_bp.route('/vehicles', methods=['GET'])
def list_vehicles():
    """Lista veículos em formato JSON."""
    active_only = request.args.get('active_only', '').lower() in ['true', '1']
    search = request.args.get('search')
    vehicles = VehicleService.get_all(active_only=active_only, search=search)
    return jsonify({
        'success': True,
        'data': [v.to_dict(include_stats=True) for v in vehicles]
    })


@api_bp.route('/vehicles/<int:vehicle_id>', methods=['GET'])
def get_vehicle(vehicle_id: int):
    """Retorna detalhes de um veículo específico por ID."""
    vehicle = VehicleService.get_by_id(vehicle_id)
    return jsonify({
        'success': True,
        'data': vehicle.to_dict(include_stats=True)
    })


@api_bp.route('/vehicles', methods=['POST'])
def create_vehicle():
    """Cadastra um novo veículo com validação de placa padrão Mercosul ou tradicional."""
    data = request.get_json() or {}
    vehicle = VehicleService.create(data)
    return jsonify({
        'success': True,
        'message': f"Veículo '{vehicle.model}' cadastrado com sucesso!",
        'data': vehicle.to_dict()
    }), 201


@api_bp.route('/vehicles/<int:vehicle_id>', methods=['PUT'])
def update_vehicle(vehicle_id: int):
    """Atualiza dados de modelo, cor, placa e status ativo do veículo."""
    data = request.get_json() or {}
    vehicle = VehicleService.update(vehicle_id, data)
    return jsonify({
        'success': True,
        'message': f"Veículo '{vehicle.model}' atualizado com sucesso!",
        'data': vehicle.to_dict()
    })


@api_bp.route('/vehicles/<int:vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id: int):
    """Remove um veículo caso não possua agendamentos ativos."""
    VehicleService.delete(vehicle_id)
    return jsonify({
        'success': True,
        'message': "Veículo removido com sucesso!"
    })


# ==============================================================================
# ENDPOINTS REST: AGENDAMENTOS E CALENDÁRIO (SCHEDULES API)
# ==============================================================================

@api_bp.route('/schedules/calendar', methods=['GET'])
def get_calendar_events():
    """
    Endpoint consumido pelo FullCalendar 6.x via AJAX/Fetch.
    Retorna a lista de eventos com cores e propriedades estendidas conforme os filtros.
    """
    start = request.args.get('start')
    end = request.args.get('end')
    driver_id = request.args.get('driver_id', type=int)
    vehicle_id = request.args.get('vehicle_id', type=int)
    status = request.args.get('status')

    events = ScheduleService.get_calendar_events(
        start_date=start,
        end_date=end,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        status=status
    )
    return jsonify(events)


@api_bp.route('/schedules', methods=['GET'])
def list_schedules():
    """Lista agendamentos em formato estruturado."""
    schedules = ServiceSchedule.query.order_by(ServiceSchedule.schedule_date.desc()).all()
    return jsonify({
        'success': True,
        'data': [s.to_dict() for s in schedules]
    })


@api_bp.route('/schedules/<int:schedule_id>', methods=['GET'])
def get_schedule(schedule_id: int):
    """Retorna detalhes de um agendamento individual."""
    schedule = ServiceSchedule.query.get_or_404(schedule_id)
    return jsonify({
        'success': True,
        'data': schedule.to_dict()
    })


@api_bp.route('/schedules', methods=['POST'])
def create_schedule():
    """
    Cria uma nova ordem de serviço após validação de conflito no mesmo dia.
    Retorna 409 Conflict se motorista ou veículo já estiverem alocados.
    """
    data = request.get_json() or {}
    schedule = ScheduleService.create(data)
    return jsonify({
        'success': True,
        'message': f"Agendamento para '{schedule.client_name}' registrado com sucesso!",
        'data': schedule.to_dict()
    }), 201


@api_bp.route('/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id: int):
    """
    Atualiza detalhes do agendamento ou altera status operacional.
    Verifica conflito se houver alteração de data, condutor ou veículo.
    """
    data = request.get_json() or {}
    schedule = ScheduleService.update(schedule_id, data)
    return jsonify({
        'success': True,
        'message': "Agendamento atualizado com sucesso!",
        'data': schedule.to_dict()
    })


@api_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id: int):
    """Exclui um agendamento específico."""
    ScheduleService.delete(schedule_id)
    return jsonify({
        'success': True,
        'message': "Agendamento excluído com sucesso!"
    })


@api_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """Retorna as métricas operacionais consolidadas."""
    metrics = ScheduleService.get_dashboard_metrics()
    return jsonify({
        'success': True,
        'data': metrics
    })


@api_bp.route('/seed', methods=['POST'])
def seed_demo_data():
    """
    Popula o banco de dados com dados iniciais de demonstração (motoristas, veículos e agendamentos)
    para permitir teste imediato de todas as funcionalidades e conflitos.
    """
    try:
        # Se já existirem dados, não duplica a menos que seja forçado
        force = request.args.get('force', 'false').lower() == 'true'
        if not force and Driver.query.first():
            return jsonify({
                'success': True,
                'message': 'Base de dados já contém registros. Parâmetro force=true não informado.'
            })

        # 1. Criação de Motoristas com CPFs válidos
        drivers_data = [
            {'name': 'Carlos Eduardo Silva', 'tax_id': '01234567890'}, # Exemplo normalizado
            {'name': 'Mariana Souza Santos', 'tax_id': '12345678909'},
            {'name': 'Rodrigo Pereira Lima', 'tax_id': '23456789018'},
            {'name': 'Fernanda Oliveira Castro', 'tax_id': '34567890127'},
        ]
        
        # Gera CPFs com algoritmo válido para demonstração
        valid_sample_cpfs = ['83138865007', '52998224725', '11144477735', '45826978809']
        for i, d in enumerate(drivers_data):
            d['tax_id'] = valid_sample_cpfs[i % len(valid_sample_cpfs)]

        created_drivers = []
        for d in drivers_data:
            existing = Driver.query.filter_by(tax_id=d['tax_id']).first()
            if not existing:
                driver = Driver(name=d['name'], tax_id=d['tax_id'])
                db.session.add(driver)
                created_drivers.append(driver)
            else:
                created_drivers.append(existing)
        db.session.commit()

        # 2. Criação de Veículos da Frota
        vehicles_data = [
            {'model': 'Mercedes-Benz Sprinter 416', 'color': 'Branco', 'license_plate': 'BRA2E19', 'is_active': True},
            {'model': 'Volkswagen Delivery Express', 'color': 'Prata', 'license_plate': 'LOG8F24', 'is_active': True},
            {'model': 'Renault Master Furgão', 'color': 'Azul', 'license_plate': 'FLX4A55', 'is_active': True},
            {'model': 'Fiat Fiorino Endurance', 'color': 'Branco', 'license_plate': 'AGD9K82', 'is_active': True},
            {'model': 'Iveco Daily 35S15', 'color': 'Vermelho', 'license_plate': 'TRK7B31', 'is_active': False},
        ]

        created_vehicles = []
        for v in vehicles_data:
            existing = Vehicle.query.filter_by(license_plate=v['license_plate']).first()
            if not existing:
                vehicle = Vehicle(
                    model=v['model'],
                    color=v['color'],
                    license_plate=v['license_plate'],
                    is_active=v['is_active']
                )
                db.session.add(vehicle)
                created_vehicles.append(vehicle)
            else:
                created_vehicles.append(existing)
        db.session.commit()

        # 3. Criação de Agendamentos para a semana atual
        today = date.today()
        schedules_data = [
            {
                'schedule_date': today,
                'driver_id': created_drivers[0].id,
                'vehicle_id': created_vehicles[0].id,
                'client_name': 'Supermercados Horizonte Ltda',
                'delivery_address': 'Av. Paulista, 1578 - Bela Vista, São Paulo - SP',
                'order_number': 'NF-104928',
                'notes': 'Entrega de perecíveis na doca 3 das 08h às 11h.',
                'status': 'IN_PROGRESS'
            },
            {
                'schedule_date': today,
                'driver_id': created_drivers[1].id,
                'vehicle_id': created_vehicles[1].id,
                'client_name': 'TechLog Distribuidora',
                'delivery_address': 'Rua Funchal, 418 - Vila Olímpia, São Paulo - SP',
                'order_number': 'NF-104929',
                'notes': 'Carga frágil com equipamentos de informática.',
                'status': 'SCHEDULED'
            },
            {
                'schedule_date': today + timedelta(days=1),
                'driver_id': created_drivers[2].id,
                'vehicle_id': created_vehicles[2].id,
                'client_name': 'Farmácias Central Vida',
                'delivery_address': 'Rua Vergueiro, 2030 - Paraíso, São Paulo - SP',
                'order_number': 'NF-104930',
                'notes': 'Transporte refrigerado com monitoramento térmico.',
                'status': 'SCHEDULED'
            },
            {
                'schedule_date': today + timedelta(days=2),
                'driver_id': created_drivers[0].id,
                'vehicle_id': created_vehicles[3].id,
                'client_name': 'Construções & Reformas Aliança',
                'delivery_address': 'Estrada do Campo Limpo, 890 - São Paulo - SP',
                'order_number': 'NF-104931',
                'notes': 'Entrega de ferramentas especiais para o canteiro.',
                'status': 'SCHEDULED'
            },
            {
                'schedule_date': today - timedelta(days=1),
                'driver_id': created_drivers[3].id,
                'vehicle_id': created_vehicles[0].id,
                'client_name': 'Mega Atacadista Sul',
                'delivery_address': 'Av. dos Bandeirantes, 3200 - Planalto Paulista, SP',
                'order_number': 'NF-104920',
                'notes': 'Entrega concluída com comprovante assinado.',
                'status': 'COMPLETED'
            }
        ]

        for s in schedules_data:
            # Evita duplicar se já existir agendamento para aquele cliente na data
            exists = ServiceSchedule.query.filter_by(
                schedule_date=s['schedule_date'],
                driver_id=s['driver_id']
            ).first()
            if not exists:
                sched = ServiceSchedule(**s)
                db.session.add(sched)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Dados de demonstração populados com sucesso!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao popular base: {str(e)}'
        }), 500
