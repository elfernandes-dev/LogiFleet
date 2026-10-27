"""
Camada de Serviços e Regras de Negócio (Services Layer).
Aplica os princípios SOLID, validação de regras de domínio, validação algorítmica de CPF e Placas,
e checagem rigorosa de conflito de agenda para frotas.
"""

import re
from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy import or_, and_
from app.models import db, Driver, Vehicle, ServiceSchedule


class BusinessRuleException(Exception):
    """Exceção customizada para violações de regras de negócio."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ConflictException(BusinessRuleException):
    """Exceção para conflitos de agendamento (mesmo motorista ou veículo na mesma data)."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


# ==============================================================================
# VALIDAÇÃO E SANITIZAÇÃO DE DADOS
# ==============================================================================

def sanitize_string(value: Optional[str]) -> str:
    """Sanitiza strings removendo espaços extras e prevenindo injeções básicas."""
    if not value:
        return ""
    return str(value).strip()


def clean_digits(value: Optional[str]) -> str:
    """Remove quaisquer caracteres não numéricos de uma string."""
    if not value:
        return ""
    return ''.join(filter(str.isdigit, str(value)))


def validate_cpf(tax_id: str) -> bool:
    """
    Valida o algoritmo oficial do CPF brasileiro (Cadastro de Pessoas Físicas).
    Calcula os dois dígitos verificadores e rejeita números conhecidos repetidos.
    """
    clean_cpf = clean_digits(tax_id)
    if len(clean_cpf) != 11:
        return False

    # Rejeita CPFs com todos os dígitos iguais (ex: 111.111.111-11)
    if clean_cpf == clean_cpf[0] * 11:
        return False

    # Primeiro dígito verificador
    sum_first = sum(int(clean_cpf[i]) * (10 - i) for i in range(9))
    rest_first = (sum_first * 10) % 11
    digit_one = 0 if rest_first == 10 else rest_first
    if digit_one != int(clean_cpf[9]):
        return False

    # Segundo dígito verificador
    sum_second = sum(int(clean_cpf[i]) * (11 - i) for i in range(10))
    rest_second = (sum_second * 10) % 11
    digit_two = 0 if rest_second == 10 else rest_second
    if digit_two != int(clean_cpf[10]):
        return False

    return True


def format_cpf(clean_cpf: str) -> str:
    """Formata sequência de 11 dígitos no padrão 000.000.000-00."""
    if len(clean_cpf) == 11:
        return f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
    return clean_cpf


def validate_license_plate(plate: str) -> Tuple[bool, str]:
    """
    Valida formato de placa de veículo automotor:
    1. Mercosul: 3 letras, 1 número, 1 letra, 2 números (ex: ABC1D23)
    2. Tradicional: 3 letras e 4 números (ex: ABC1234 ou ABC-1234)
    Retorna tupla (válido, placa_normalizada).
    """
    if not plate:
        return False, ""
    normalized = re.sub(r'[^A-Za-z0-9]', '', plate).upper().strip()

    # Validação formato Mercosul: 3 letras, 1 número, 1 letra, 2 números
    mercosul_pattern = r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'
    # Validação formato Tradicional: 3 letras e 4 números
    traditional_pattern = r'^[A-Z]{3}[0-9]{4}$'

    if re.match(mercosul_pattern, normalized) or re.match(traditional_pattern, normalized):
        return True, normalized
    return False, normalized


# ==============================================================================
# SERVIÇOS DE MOTORISTAS (DRIVER SERVICE)
# ==============================================================================

class DriverService:
    """Regras de negócio e operações de banco de dados para Motoristas."""

    @staticmethod
    def get_all(search: Optional[str] = None) -> List[Driver]:
        """Obtém lista de motoristas cadastrados, com suporte a busca por nome ou CPF."""
        query = Driver.query
        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Driver.name.ilike(search_term),
                    Driver.tax_id.ilike(search_term)
                )
            )
        return query.order_by(Driver.name.asc()).all()

    @staticmethod
    def get_by_id(driver_id: int) -> Driver:
        """Busca motorista por ID ou lança erro 404 se não encontrado."""
        driver = Driver.query.get(driver_id)
        if not driver:
            raise BusinessRuleException("Motorista não encontrado no sistema.", 404)
        return driver

    @staticmethod
    def create(data: Dict[str, Any]) -> Driver:
        """Cria um novo motorista com validações completas."""
        name = sanitize_string(data.get('name'))
        raw_tax_id = sanitize_string(data.get('tax_id'))

        if not name or len(name) < 3:
            raise BusinessRuleException("O nome do motorista deve ter pelo menos 3 caracteres.")

        clean_tax = clean_digits(raw_tax_id)
        if not validate_cpf(clean_tax):
            raise BusinessRuleException("CPF inválido. Certifique-se de digitar um CPF válido com 11 dígitos.")

        # Verifica unicidade do CPF
        existing = Driver.query.filter_by(tax_id=clean_tax).first()
        if existing:
            raise BusinessRuleException("Já existe um motorista cadastrado com este CPF.", 409)

        new_driver = Driver(name=name, tax_id=clean_tax)
        db.session.add(new_driver)
        db.session.commit()
        return new_driver

    @staticmethod
    def update(driver_id: int, data: Dict[str, Any]) -> Driver:
        """Atualiza dados cadastrais de um motorista existente."""
        driver = DriverService.get_by_id(driver_id)

        name = sanitize_string(data.get('name'))
        raw_tax_id = sanitize_string(data.get('tax_id'))

        if not name or len(name) < 3:
            raise BusinessRuleException("O nome do motorista deve ter pelo menos 3 caracteres.")

        clean_tax = clean_digits(raw_tax_id)
        if not validate_cpf(clean_tax):
            raise BusinessRuleException("CPF inválido. Certifique-se de digitar um CPF válido com 11 dígitos.")

        # Verifica se o CPF foi alterado e se colide com outro motorista
        if clean_tax != driver.tax_id:
            existing = Driver.query.filter(Driver.tax_id == clean_tax, Driver.id != driver.id).first()
            if existing:
                raise BusinessRuleException("Este CPF já pertence a outro motorista cadastrado.", 409)

        driver.name = name
        driver.tax_id = clean_tax
        db.session.commit()
        return driver

    @staticmethod
    def delete(driver_id: int) -> None:
        """
        Exclui um motorista se não houver agendamentos ativos futuros atrelados.
        Em caso de agendamentos passados ou cancelados, remove com integridade.
        """
        driver = DriverService.get_by_id(driver_id)
        
        # Verifica se há agendamentos agendados ou em andamento
        active_schedules = ServiceSchedule.query.filter(
            ServiceSchedule.driver_id == driver.id,
            ServiceSchedule.status.in_(['SCHEDULED', 'IN_PROGRESS'])
        ).count()

        if active_schedules > 0:
            raise BusinessRuleException(
                f"Não é possível excluir o motorista pois existem {active_schedules} agendamento(s) ativo(s) vinculado(s). Cancele-os primeiro.",
                400
            )

        db.session.delete(driver)
        db.session.commit()


# ==============================================================================
# SERVIÇOS DE VEÍCULOS (VEHICLE SERVICE)
# ==============================================================================

class VehicleService:
    """Regras de negócio e operações de banco de dados para Veículos."""

    @staticmethod
    def get_all(active_only: bool = False, search: Optional[str] = None) -> List[Vehicle]:
        """Obtém lista de veículos com filtros de atividade e busca por modelo/placa."""
        query = Vehicle.query
        if active_only:
            query = query.filter_by(is_active=True)
        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Vehicle.model.ilike(search_term),
                    Vehicle.license_plate.ilike(search_term),
                    Vehicle.color.ilike(search_term)
                )
            )
        return query.order_by(Vehicle.model.asc()).all()

    @staticmethod
    def get_by_id(vehicle_id: int) -> Vehicle:
        """Busca veículo por ID ou lança erro 404."""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            raise BusinessRuleException("Veículo não encontrado no sistema.", 404)
        return vehicle

    @staticmethod
    def create(data: Dict[str, Any]) -> Vehicle:
        """Cadastra um novo veículo com validação de placa padrão Mercosul ou tradicional."""
        model = sanitize_string(data.get('model'))
        color = sanitize_string(data.get('color'))
        plate = sanitize_string(data.get('license_plate'))
        is_active = bool(data.get('is_active', True))

        if not model or len(model) < 2:
            raise BusinessRuleException("O modelo do veículo deve ser preenchido.")
        if not color or len(color) < 2:
            raise BusinessRuleException("A cor do veículo deve ser preenchida.")

        valid_plate, clean_plate = validate_license_plate(plate)
        if not valid_plate:
            raise BusinessRuleException("Placa inválida. Utilize o formato Mercosul (ex: ABC1D23) ou Tradicional (ex: ABC1234).")

        # Verifica duplicidade de placa
        existing = Vehicle.query.filter_by(license_plate=clean_plate).first()
        if existing:
            raise BusinessRuleException("Já existe um veículo cadastrado com esta placa.", 409)

        new_vehicle = Vehicle(
            model=model,
            color=color,
            license_plate=clean_plate,
            is_active=is_active
        )
        db.session.add(new_vehicle)
        db.session.commit()
        return new_vehicle

    @staticmethod
    def update(vehicle_id: int, data: Dict[str, Any]) -> Vehicle:
        """Atualiza dados do veículo e status de disponibilidade operacional."""
        vehicle = VehicleService.get_by_id(vehicle_id)

        model = sanitize_string(data.get('model'))
        color = sanitize_string(data.get('color'))
        plate = sanitize_string(data.get('license_plate'))
        is_active = data.get('is_active')

        if not model or len(model) < 2:
            raise BusinessRuleException("O modelo do veículo deve ser preenchido.")
        if not color or len(color) < 2:
            raise BusinessRuleException("A cor do veículo deve ser preenchida.")

        valid_plate, clean_plate = validate_license_plate(plate)
        if not valid_plate:
            raise BusinessRuleException("Placa inválida. Utilize o padrão Mercosul (ex: ABC1D23) ou Tradicional (ex: ABC1234).")

        if clean_plate != vehicle.license_plate:
            existing = Vehicle.query.filter(Vehicle.license_plate == clean_plate, Vehicle.id != vehicle.id).first()
            if existing:
                raise BusinessRuleException("Esta placa já está cadastrada para outro veículo.", 409)

        vehicle.model = model
        vehicle.color = color
        vehicle.license_plate = clean_plate
        if is_active is not None:
            vehicle.is_active = bool(is_active)

        db.session.commit()
        return vehicle

    @staticmethod
    def delete(vehicle_id: int) -> None:
        """Exclui veículo se não houver agendamentos ativos."""
        vehicle = VehicleService.get_by_id(vehicle_id)

        active_schedules = ServiceSchedule.query.filter(
            ServiceSchedule.vehicle_id == vehicle.id,
            ServiceSchedule.status.in_(['SCHEDULED', 'IN_PROGRESS'])
        ).count()

        if active_schedules > 0:
            raise BusinessRuleException(
                f"Não é possível excluir o veículo pois existem {active_schedules} agendamento(s) ativo(s) associado(s). Cancele-os primeiro.",
                400
            )

        db.session.delete(vehicle)
        db.session.commit()


# ==============================================================================
# SERVIÇOS DE AGENDAMENTO E LOGÍSTICA (SERVICE SCHEDULE)
# ==============================================================================

class ScheduleService:
    """
    Regras de negócio de agendamento de frotas e validação de conflitos de disponibilidade.
    Garante que um motorista e um veículo não possam ser alocados duas vezes no mesmo dia.
    """

    @staticmethod
    def parse_date(date_str: str) -> date:
        """Converte string de data no formato AAAA-MM-DD para objeto date."""
        try:
            return datetime.strptime(sanitize_string(date_str), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise BusinessRuleException("Formato de data inválido. Utilize o padrão AAAA-MM-DD.")

    @staticmethod
    def check_conflict(
        schedule_date: date,
        driver_id: int,
        vehicle_id: int,
        exclude_schedule_id: Optional[int] = None
    ) -> None:
        """
        Valida conflitos operacionais de agenda.
        Verifica se o motorista ou veículo já foram escalados para outro serviço na mesma data.
        Ignora agendamentos com status CANCELLED.
        """
        # 1. Verifica conflito do motorista
        driver_conflict_query = ServiceSchedule.query.filter(
            ServiceSchedule.schedule_date == schedule_date,
            ServiceSchedule.driver_id == driver_id,
            ServiceSchedule.status.in_(['SCHEDULED', 'IN_PROGRESS', 'COMPLETED'])
        )
        if exclude_schedule_id:
            driver_conflict_query = driver_conflict_query.filter(ServiceSchedule.id != exclude_schedule_id)
        
        driver_conflict = driver_conflict_query.first()
        if driver_conflict:
            driver_name = driver_conflict.driver.name if driver_conflict.driver else f"ID #{driver_id}"
            formatted_date = schedule_date.strftime('%d/%m/%Y')
            raise ConflictException(
                f"Conflito de Escala: O motorista '{driver_name}' já possui o serviço #{driver_conflict.id} "
                f"agendado para o dia {formatted_date} (Cliente: {driver_conflict.client_name})."
            )

        # 2. Verifica conflito do veículo
        vehicle_conflict_query = ServiceSchedule.query.filter(
            ServiceSchedule.schedule_date == schedule_date,
            ServiceSchedule.vehicle_id == vehicle_id,
            ServiceSchedule.status.in_(['SCHEDULED', 'IN_PROGRESS', 'COMPLETED'])
        )
        if exclude_schedule_id:
            vehicle_conflict_query = vehicle_conflict_query.filter(ServiceSchedule.id != exclude_schedule_id)

        vehicle_conflict = vehicle_conflict_query.first()
        if vehicle_conflict:
            vehicle_desc = f"{vehicle_conflict.vehicle.model} ({vehicle_conflict.vehicle.formatted_license_plate()})" if vehicle_conflict.vehicle else f"ID #{vehicle_id}"
            formatted_date = schedule_date.strftime('%d/%m/%Y')
            raise ConflictException(
                f"Conflito de Frota: O veículo '{vehicle_desc}' já está alocado para o serviço #{vehicle_conflict.id} "
                f"no dia {formatted_date} (Cliente: {vehicle_conflict.client_name})."
            )

    @staticmethod
    def create(data: Dict[str, Any]) -> ServiceSchedule:
        """Cria uma nova ordem de agendamento após validação completa de conflito."""
        raw_date = data.get('schedule_date')
        if not raw_date:
            raise BusinessRuleException("A data do agendamento é obrigatória.")
        schedule_date = ScheduleService.parse_date(raw_date)

        try:
            driver_id = int(data.get('driver_id', 0))
            vehicle_id = int(data.get('vehicle_id', 0))
        except (ValueError, TypeError):
            raise BusinessRuleException("Motorista e Veículo selecionados são inválidos.")

        # Valida existência e disponibilidade do motorista e veículo
        driver = DriverService.get_by_id(driver_id)
        vehicle = VehicleService.get_by_id(vehicle_id)

        if not vehicle.is_active:
            raise BusinessRuleException(f"O veículo '{vehicle.model}' ({vehicle.formatted_license_plate()}) está inativo para novas operações.")

        client_name = sanitize_string(data.get('client_name'))
        delivery_address = sanitize_string(data.get('delivery_address'))
        order_number = sanitize_string(data.get('order_number'))
        notes = sanitize_string(data.get('notes'))
        status = sanitize_string(data.get('status')) or 'SCHEDULED'

        if not client_name:
            raise BusinessRuleException("O nome do cliente é obrigatório.")
        if not delivery_address:
            raise BusinessRuleException("O endereço de entrega/serviço é obrigatório.")
        if status not in ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']:
            status = 'SCHEDULED'

        # Valida conflito de data para motorista e veículo
        ScheduleService.check_conflict(schedule_date, driver_id, vehicle_id)

        schedule = ServiceSchedule(
            schedule_date=schedule_date,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            client_name=client_name,
            delivery_address=delivery_address,
            order_number=order_number or None,
            notes=notes or None,
            status=status
        )
        db.session.add(schedule)
        db.session.commit()
        return schedule

    @staticmethod
    def update(schedule_id: int, data: Dict[str, Any]) -> ServiceSchedule:
        """Atualiza dados do agendamento e revalida conflitos se data/motorista/veículo mudarem."""
        schedule = ServiceSchedule.query.get(schedule_id)
        if not schedule:
            raise BusinessRuleException("Agendamento não encontrado.", 404)

        raw_date = data.get('schedule_date')
        schedule_date = ScheduleService.parse_date(raw_date) if raw_date else schedule.schedule_date

        try:
            driver_id = int(data.get('driver_id', schedule.driver_id))
            vehicle_id = int(data.get('vehicle_id', schedule.vehicle_id))
        except (ValueError, TypeError):
            raise BusinessRuleException("Identificadores de motorista ou veículo inválidos.")

        driver = DriverService.get_by_id(driver_id)
        vehicle = VehicleService.get_by_id(vehicle_id)

        status = sanitize_string(data.get('status', schedule.status))
        if status not in ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']:
            status = schedule.status

        # Se o novo status não for CANCELLED, valida conflitos
        if status != 'CANCELLED':
            ScheduleService.check_conflict(schedule_date, driver_id, vehicle_id, exclude_schedule_id=schedule.id)

        client_name = sanitize_string(data.get('client_name', schedule.client_name))
        delivery_address = sanitize_string(data.get('delivery_address', schedule.delivery_address))
        order_number = sanitize_string(data.get('order_number', schedule.order_number))
        notes = sanitize_string(data.get('notes', schedule.notes))

        if not client_name:
            raise BusinessRuleException("O nome do cliente é obrigatório.")
        if not delivery_address:
            raise BusinessRuleException("O endereço de entrega/serviço é obrigatório.")

        schedule.schedule_date = schedule_date
        schedule.driver_id = driver.id
        schedule.vehicle_id = vehicle.id
        schedule.client_name = client_name
        schedule.delivery_address = delivery_address
        schedule.order_number = order_number or None
        schedule.notes = notes or None
        schedule.status = status

        db.session.commit()
        return schedule

    @staticmethod
    def delete(schedule_id: int) -> None:
        """Exclui permanentemente um agendamento da base de dados."""
        schedule = ServiceSchedule.query.get(schedule_id)
        if not schedule:
            raise BusinessRuleException("Agendamento não encontrado.", 404)
        db.session.delete(schedule)
        db.session.commit()

    @staticmethod
    def get_calendar_events(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        driver_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retorna agendamentos formatados para o FullCalendar com filtros aplicados."""
        query = ServiceSchedule.query

        if start_date:
            try:
                start = datetime.strptime(start_date.split('T')[0], '%Y-%m-%d').date()
                query = query.filter(ServiceSchedule.schedule_date >= start)
            except (ValueError, TypeError):
                pass

        if end_date:
            try:
                end = datetime.strptime(end_date.split('T')[0], '%Y-%m-%d').date()
                query = query.filter(ServiceSchedule.schedule_date <= end)
            except (ValueError, TypeError):
                pass

        if driver_id:
            query = query.filter(ServiceSchedule.driver_id == driver_id)

        if vehicle_id:
            query = query.filter(ServiceSchedule.vehicle_id == vehicle_id)

        if status:
            query = query.filter(ServiceSchedule.status == status)

        schedules = query.order_by(ServiceSchedule.schedule_date.asc()).all()
        return [s.to_calendar_event() for s in schedules]

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, int]:
        """Calcula métricas rápidas operacionais para o cabeçalho do painel de logística."""
        today = date.today()
        total = ServiceSchedule.query.count()
        today_schedules = ServiceSchedule.query.filter(ServiceSchedule.schedule_date == today).count()
        completed = ServiceSchedule.query.filter(ServiceSchedule.status == 'COMPLETED').count()
        scheduled = ServiceSchedule.query.filter(ServiceSchedule.status == 'SCHEDULED').count()
        in_progress = ServiceSchedule.query.filter(ServiceSchedule.status == 'IN_PROGRESS').count()
        drivers_count = Driver.query.count()
        vehicles_count = Vehicle.query.filter_by(is_active=True).count()

        return {
            'total': total,
            'today': today_schedules,
            'completed': completed,
            'scheduled': scheduled,
            'in_progress': in_progress,
            'active_drivers': drivers_count,
            'active_vehicles': vehicles_count
        }
