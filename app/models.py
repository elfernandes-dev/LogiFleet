"""
Módulo de Modelos do Banco de Dados (ORM SQLAlchemy).
Define as entidades Driver (Motorista), Vehicle (Veículo) e ServiceSchedule (Agendamento de Serviço).
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def get_utc_now():
    """Retorna o timestamp atual em UTC com timezone configurado."""
    return datetime.now(timezone.utc)


class Driver(db.Model):
    """
    Entidade de Motorista.
    Armazena os dados cadastrais do condutor responsável pelas entregas e serviços.
    """
    __tablename__ = 'drivers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    tax_id = db.Column(db.String(14), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)

    # Relacionamento com agendamentos vinculados
    schedules = db.relationship('ServiceSchedule', back_populates='driver', cascade='all, delete-orphan', lazy='dynamic')

    def formatted_tax_id(self) -> str:
        """Retorna o CPF formatado como 000.000.000-00."""
        clean = ''.join(filter(str.isdigit, self.tax_id or ''))
        if len(clean) == 11:
            return f"{clean[0:3]}.{clean[3:6]}.{clean[6:9]}-{clean[9:11]}"
        return self.tax_id

    def to_dict(self, include_stats: bool = False) -> dict:
        """Serializa o motorista para representação em dicionário/JSON."""
        data = {
            'id': self.id,
            'name': self.name,
            'tax_id': self.tax_id,
            'formatted_tax_id': self.formatted_tax_id(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_stats:
            data['total_schedules'] = self.schedules.count()
        return data

    def __repr__(self) -> str:
        return f"<Driver id={self.id} name='{self.name}' tax_id='{self.tax_id}'>"


class Vehicle(db.Model):
    """
    Entidade de Veículo da Frota.
    Representa os automóveis, utilitários ou caminhões disponíveis para a operação logística.
    """
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(30), nullable=False)
    license_plate = db.Column(db.String(10), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)

    # Relacionamento com agendamentos vinculados
    schedules = db.relationship('ServiceSchedule', back_populates='vehicle', cascade='all, delete-orphan', lazy='dynamic')

    def formatted_license_plate(self) -> str:
        """Retorna a placa em letras maiúsculas e formato padronizado."""
        plate = (self.license_plate or '').upper().strip()
        # Formata placa tradicional ABC1234 para ABC-1234 se aplicável
        if len(plate) == 7 and plate[:3].isalpha() and plate[3:].isdigit():
            return f"{plate[:3]}-{plate[3:]}"
        return plate

    def to_dict(self, include_stats: bool = False) -> dict:
        """Serializa o veículo para representação em dicionário/JSON."""
        data = {
            'id': self.id,
            'model': self.model,
            'color': self.color,
            'license_plate': self.formatted_license_plate(),
            'raw_license_plate': self.license_plate,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_stats:
            data['total_schedules'] = self.schedules.count()
        return data

    def __repr__(self) -> str:
        return f"<Vehicle id={self.id} model='{self.model}' plate='{self.license_plate}'>"


class ServiceSchedule(db.Model):
    """
    Entidade de Agendamento / Ordem de Serviço de Transporte.
    Mapeia o compromisso logístico alocando um motorista e um veículo para uma data e cliente específicos.
    """
    __tablename__ = 'service_schedules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    schedule_date = db.Column(db.Date, nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id', ondelete='CASCADE'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    client_name = db.Column(db.String(120), nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    order_number = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='SCHEDULED', nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)

    # Relacionamentos
    driver = db.relationship('Driver', back_populates='schedules')
    vehicle = db.relationship('Vehicle', back_populates='schedules')

    def to_dict(self) -> dict:
        """Serializa o agendamento em formato estruturado incluindo dados do motorista e veículo."""
        return {
            'id': self.id,
            'schedule_date': self.schedule_date.strftime('%Y-%m-%d') if self.schedule_date else None,
            'driver_id': self.driver_id,
            'vehicle_id': self.vehicle_id,
            'driver_name': self.driver.name if self.driver else None,
            'vehicle_model': self.vehicle.model if self.vehicle else None,
            'vehicle_plate': self.vehicle.formatted_license_plate() if self.vehicle else None,
            'vehicle_color': self.vehicle.color if self.vehicle else None,
            'client_name': self.client_name,
            'delivery_address': self.delivery_address,
            'order_number': self.order_number or '',
            'notes': self.notes or '',
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def to_calendar_event(self) -> dict:
        """
        Formata o agendamento no formato de evento aceito pelo FullCalendar 6.x.
        Define cores de acordo com o status operacional.
        """
        status_colors = {
            'SCHEDULED': {'bg': '#0d6efd', 'border': '#0a58ca', 'text': '#ffffff'},   # Azul Primário
            'IN_PROGRESS': {'bg': '#ffc107', 'border': '#ffca2c', 'text': '#000000'}, # Amarelo Alerta
            'COMPLETED': {'bg': '#198754', 'border': '#157347', 'text': '#ffffff'},   # Verde Sucesso
            'CANCELLED': {'bg': '#6c757d', 'border': '#5c636a', 'text': '#ffffff'},   # Cinza Secundário
        }
        color_info = status_colors.get(self.status, status_colors['SCHEDULED'])

        driver_name = self.driver.name if self.driver else "Sem Motorista"
        vehicle_info = f"{self.vehicle.model} ({self.vehicle.formatted_license_plate()})" if self.vehicle else "Sem Veículo"

        return {
            'id': str(self.id),
            'title': f"{self.client_name} - {driver_name}",
            'start': self.schedule_date.strftime('%Y-%m-%d') if self.schedule_date else None,
            'allDay': True,
            'backgroundColor': color_info['bg'],
            'borderColor': color_info['border'],
            'textColor': color_info['text'],
            'extendedProps': {
                'schedule_id': self.id,
                'client_name': self.client_name,
                'delivery_address': self.delivery_address,
                'order_number': self.order_number or '',
                'notes': self.notes or '',
                'status': self.status,
                'driver_id': self.driver_id,
                'driver_name': driver_name,
                'vehicle_id': self.vehicle_id,
                'vehicle_info': vehicle_info,
                'schedule_date': self.schedule_date.strftime('%Y-%m-%d') if self.schedule_date else '',
            }
        }

    def __repr__(self) -> str:
        return f"<ServiceSchedule id={self.id} date='{self.schedule_date}' client='{self.client_name}' status='{self.status}'>"
