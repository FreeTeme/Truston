from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import bcrypt
from datetime import datetime
import os
import enum
import uuid

app = Flask(__name__)

# Конфигурация SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'car_service.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'  # Замените на реальный секретный ключ

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Определение моделей
class OrderStatus(enum.Enum):
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELED = 'canceled'

class ServiceStation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    address = db.Column(db.Text, nullable=False)
    work_hours = db.Column(db.String(255), nullable=False)  # Для SQLite используем строку
    
    employees = db.relationship('Employee', backref='station', lazy=True)
    slots = db.relationship('Slot', backref='station', lazy=True)
    orders = db.relationship('Order', backref='station', lazy=True)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('service_station.id'), nullable=False)
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    station_id = db.Column(db.Integer, db.ForeignKey('service_station.id'), nullable=False)
    order = db.relationship('Order', backref='slot_ref', uselist=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_phone = db.Column(db.String(20), nullable=False)
    client_full_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.NOT_STARTED)
    vin = db.Column(db.String(17), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    license_plate = db.Column(db.String(15), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('service_station.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'))
    report = db.relationship('Report', backref='order_ref', uselist=False)
    
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
            'station_id': self.station_id,
            'slot_id': self.slot_id
        }

class Report(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), unique=True)
    chapters = db.relationship('ReportChapter', backref='report_ref', lazy=True)

class ReportChapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    report_id = db.Column(db.String(36), db.ForeignKey('report.id'), nullable=False)
    photos = db.relationship('ReportPhoto', backref='chapter_ref', lazy=True)

class ReportPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    chapter_id = db.Column(db.Integer, db.ForeignKey('report_chapter.id'), nullable=False)

# Создание таблиц перед первым запросом
@app.before_first_request
def create_tables():
    db.create_all()

# Эндпоинты для СТО
@app.route('/api/stations', methods=['POST'])
def create_station():
    data = request.get_json()
    station = ServiceStation(
        name=data['name'],
        address=data['address'],
        work_hours=data['work_hours']
    )
    db.session.add(station)
    db.session.commit()
    return jsonify({'id': station.id, 'message': 'СТО создана'}), 201

@app.route('/api/stations/<int:station_id>', methods=['DELETE'])
def delete_station(station_id):
    station = ServiceStation.query.get(station_id)
    if not station:
        return jsonify({'error': 'СТО не найдена'}), 404
    
    db.session.delete(station)
    db.session.commit()
    return jsonify({'message': 'СТО удалена'}), 200

# Эндпоинты для сотрудников
@app.route('/api/employees', methods=['POST'])
def create_employee():
    data = request.get_json()
    employee = Employee(
        full_name=data['full_name'],
        position=data['position'],
        station_id=data['station_id']
    )
    employee.set_password(data['password'])
    db.session.add(employee)
    db.session.commit()
    return jsonify({'id': employee.id, 'message': 'Сотрудник создан'}), 201

@app.route('/api/employees/<int:employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({'error': 'Сотрудник не найден'}), 404
    
    db.session.delete(employee)
    db.session.commit()
    return jsonify({'message': 'Сотрудник удален'}), 200

# Эндпоинты для заявок
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    
    # Проверка доступности слота
    slot = None
    if 'slot_id' in data:
        slot = Slot.query.get(data['slot_id'])
        if slot and not slot.is_available:
            return jsonify({'error': 'Слот занят'}), 400
    
    order = Order(
        client_phone=data['client_phone'],
        client_full_name=data['client_full_name'],
        vin=data['vin'],
        brand=data['brand'],
        model=data['model'],
        license_plate=data['license_plate'],
        station_id=data['station_id']
    )
    
    if slot:
        order.slot = slot
        slot.is_available = False
    
    db.session.add(order)
    db.session.commit()
    return jsonify({'id': order.id, 'message': 'Заявка создана'}), 201

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Заявка не найдена'}), 404
    
    # Освобождаем слот при удалении заявки
    if order.slot:
        order.slot.is_available = True
    
    db.session.delete(order)
    db.session.commit()
    return jsonify({'message': 'Заявка удалена'}), 200

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Заявка не найдена'}), 404
    
    data = request.get_json()
    try:
        new_status = OrderStatus(data['status'])
    except ValueError:
        return jsonify({'error': 'Недопустимый статус'}), 400
    
    order.status = new_status
    
    # При завершении заявки создаем отчет
    if new_status == OrderStatus.COMPLETED and not order.report:
        report = Report(order_id=order.id)
        db.session.add(report)
    
    db.session.commit()
    return jsonify(order.to_dict()), 200

# Эндпоинты для слотов
@app.route('/api/slots', methods=['POST'])
def create_slot():
    data = request.get_json()
    try:
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
    except (ValueError, KeyError):
        return jsonify({'error': 'Некорректный формат времени'}), 400
    
    slot = Slot(
        start_time=start_time,
        end_time=end_time,
        station_id=data['station_id']
    )
    db.session.add(slot)
    db.session.commit()
    return jsonify({'id': slot.id, 'message': 'Слот создан'}), 201

# Аутентификация сотрудника
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    employee = Employee.query.filter_by(full_name=data['full_name']).first()
    
    if not employee or not employee.check_password(data['password']):
        return jsonify({'error': 'Неверные учетные данные'}), 401
    
    return jsonify({
        'id': employee.id,
        'full_name': employee.full_name,
        'position': employee.position,
        'station_id': employee.station_id
    }), 200

if __name__ == '__main__':
    app.run(debug=True)