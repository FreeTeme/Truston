from flask_sqlalchemy import SQLAlchemy
import enum
import uuid
import bcrypt

db = SQLAlchemy()

class OrderStatus(enum.Enum):
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELED = 'canceled'

class ServiceStation(db.Model):
    __tablename__ = 'service_stations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    address = db.Column(db.Text, nullable=False)
    work_hours = db.Column(db.JSON, nullable=False)  # {"monday": "9:00-18:00", ...}
    
    employees = db.relationship('Employee', backref='service_station', lazy=True)
    slots = db.relationship('Slot', backref='service_station', lazy=True)
    orders = db.relationship('Order', backref='service_station', lazy=True)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    service_station_id = db.Column(db.Integer, db.ForeignKey('service_stations.id'), nullable=False)
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class Slot(db.Model):
    __tablename__ = 'slots'
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    service_station_id = db.Column(db.Integer, db.ForeignKey('service_stations.id'), nullable=False)
    order = db.relationship('Order', backref='slot', uselist=False)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    client_phone = db.Column(db.String(20), nullable=False)
    client_full_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.NOT_STARTED)
    vin = db.Column(db.String(17), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    license_plate = db.Column(db.String(15), nullable=False)
    service_station_id = db.Column(db.Integer, db.ForeignKey('service_stations.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id'))
    report = db.relationship('Report', backref='order', uselist=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_phone': self.client_phone,
            'client_full_name': self.client_full_name,
            'status': self.status.value,
            'vin': self.vin,
            'brand': self.brand,
            'model': self.model,
            'license_plate': self.license_plate,
            'service_station_id': self.service_station_id,
            'slot_id': self.slot_id
        }

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), unique=True)
    chapters = db.relationship('ReportChapter', backref='report', lazy=True)

class ReportChapter(db.Model):
    __tablename__ = 'report_chapters'
    id = db.Column(db.Integer, primary_key=True)
    chapter_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    report_id = db.Column(db.String(36), db.ForeignKey('reports.id'), nullable=False)
    photos = db.relationship('ReportPhoto', backref='chapter', lazy=True)

class ReportPhoto(db.Model):
    __tablename__ = 'report_photos'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    chapter_id = db.Column(db.Integer, db.ForeignKey('report_chapters.id'), nullable=False)