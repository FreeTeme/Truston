from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import bcrypt
from datetime import datetime
import os
import enum
import uuid
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)

# Конфигурация SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'car_service.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'  # Замените на реальный секретный ключ
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads') # Папка для сохранения фото

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
    work_hours = db.Column(db.JSON, nullable=False)  # Для SQLite используем JSON
    
    employees = db.relationship('Employee', backref='station', lazy=True)
    slots = db.relationship('Slot', backref='station', lazy=True)
    orders = db.relationship('Order', backref='station', lazy=True)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    service_station_id = db.Column(db.Integer, db.ForeignKey('service_station.id'), nullable=False)
    
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
    service_station_id = db.Column(db.Integer, db.ForeignKey('service_station.id'), nullable=False)
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
            'service_station_id': self.service_station_id,
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
    extra = db.Column(db.Text) # Добавляем поле extra для хранения дополнительных данных

class ReportPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    chapter_id = db.Column(db.Integer, db.ForeignKey('report_chapter.id'), nullable=False)

# Создание таблиц (выполните вручную в консоли Python при необходимости):
# with app.app_context():
#     db.create_all()

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
        service_station_id=data['service_station_id']
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
        service_station_id=data['service_station_id']
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
        'station_id': employee.service_station_id
    }), 200

# === Роутинг для всех html-страниц ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/diagnostik')
def diagnostik():
    return render_template('diagnostik.html')

@app.route('/electric')
def electric():
    return render_template('electric.html')

@app.route('/end')
def end():
    return render_template('end.html')

@app.route('/fary')
def fary():
    return render_template('fary.html')

@app.route('/glav_pwa')
def glav_pwa():
    return render_template('glav_pwa.html')

@app.route('/glav_pwa_copy')
def glav_pwa_copy():
    return render_template('glav_pwa copy.html')

@app.route('/glav_pwa_copy2')
def glav_pwa_copy2():
    return render_template('glav_pwa copy 2.html')

@app.route('/glav_pwa_copy3')
def glav_pwa_copy3():
    return render_template('glav_pwa copy 3.html')

@app.route('/glav_pwa_copy4')
def glav_pwa_copy4():
    return render_template('glav_pwa copy 4.html')

@app.route('/glav_pwa_copy5')
def glav_pwa_copy5():
    return render_template('glav_pwa copy 5.html')

@app.route('/glav3')
def glav3():
    return render_template('glav3.html')

@app.route('/index_pwa')
def index_pwa():
    return render_template('index_pwa.html')

@app.route('/podveska')
def podveska():
    return render_template('podveska.html')

@app.route('/salon')
def salon():
    return render_template('salon.html')

@app.route('/shiny')
def shiny():
    return render_template('shiny.html')

@app.route('/tormoz')
def tormoz():
    return render_template('tormoz.html')

@app.route('/zapis')
def zapis():
    return render_template('сайт/zapis.html')

@app.route('/report/<int:order_id>')
def report_view(order_id):
    order = Order.query.get_or_404(order_id)
    report = Report.query.filter_by(order_id=order_id).first()
    chapters = []
    if report:
        chapters = ReportChapter.query.filter_by(report_id=report.id).order_by(ReportChapter.chapter_number).all()
    # Для каждой главы получаем фото
    chapters_data = []
    for chapter in chapters:
        photos = ReportPhoto.query.filter_by(chapter_id=chapter.id).all()
        chapters_data.append({
            'chapter': chapter,
            'photos': photos
        })
    return render_template('report.html', order=order, chapters_data=chapters_data)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# === Конец роутинга для html-страниц ===

# === Автоматическое создание тестовой станции и пользователя ===
@app.before_request
def create_test_user_and_order():
    # Создаём тестовую станцию, если нет
    station = ServiceStation.query.filter_by(name='Test Station').first()
    if not station:
        station = ServiceStation(name='Test Station', address='Test Address', work_hours={"monday": "9:00-18:00"})
        db.session.add(station)
        db.session.commit()
    # Создаём тестового сотрудника, если нет, или обновляем пароль
    employee = Employee.query.filter_by(full_name='Тестовый Сотрудник').first()
    if not employee:
        employee = Employee(full_name='Тестовый Сотрудник', position='менеджер', service_station_id=station.id)
        employee.set_password('1111')
        db.session.add(employee)
        db.session.commit()
    else:
        employee.set_password('1111')
        db.session.commit()
    # === Автосоздание тестовой заявки ===
    order = Order.query.get(1)
    if not order:
        order = Order(
            id=1,
            client_phone='+79998887766',
            client_full_name='Иванов Иван',
            vin='TESTVIN1234567890',
            brand='TestBrand',
            model='TestModel',
            license_plate='A123AA77',
            service_station_id=station.id
        )
        db.session.add(order)
        db.session.commit()

@app.template_filter('from_json')
def from_json_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return {}

@app.route('/api/report/chapter', methods=['POST'])
def save_report_chapter():
    # Убедиться, что папка для загрузок существует
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    order_id = request.form.get('order_id')
    chapter_number = request.form.get('chapter_number')
    title = request.form.get('title')
    content = request.form.get('content')
    extra = request.form.get('extra')
    files = request.files.getlist('photos')

    print('=== save_report_chapter ===')
    print('order_id:', order_id)
    print('chapter_number:', chapter_number)
    print('title:', title)
    print('content:', content)
    print('extra:', extra)
    print('files:', [f.filename for f in files if f])

    if not order_id or not chapter_number or not title:
        return jsonify({'error': 'Недостаточно данных'}), 400

    # Найти или создать Report для заявки
    report = Report.query.filter_by(order_id=order_id).first()
    if not report:
        report = Report(order_id=order_id)
        db.session.add(report)
        db.session.commit()

    # Найти или создать главу
    chapter = ReportChapter.query.filter_by(report_id=report.id, chapter_number=chapter_number).first()
    if not chapter:
        chapter = ReportChapter(report_id=report.id, chapter_number=chapter_number, title=title, content=content)
        db.session.add(chapter)
    else:
        chapter.title = title
        chapter.content = content
    # Сохраняем extra, если есть
    if extra:
        chapter.extra = extra
    db.session.commit()

    # Сохраняем фото
    for file in files:
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Сохраняем только имя файла, а не полный путь
            photo = ReportPhoto(path=filename, description='', chapter_id=chapter.id)
            db.session.add(photo)
    db.session.commit()

    return jsonify({'message': 'Глава отчёта и фото сохранены'}), 200

@app.route('/api/report/salon_area', methods=['POST'])
def save_salon_area():
    order_id = request.form.get('order_id')
    area = request.form.get('area')  # front/rear/trunk
    checks = request.form.get('checks')  # JSON-строка с id отмеченных пунктов
    comment = request.form.get('comment')
    file = request.files.get('photo')

    if not order_id or not area:
        return jsonify({'error': 'Недостаточно данных'}), 400

    # Найти или создать Report для заявки
    report = Report.query.filter_by(order_id=order_id).first()
    if not report:
        report = Report(order_id=order_id)
        db.session.add(report)
        db.session.commit()

    # Для каждой зоны салона chapter_number: 1-front, 2-rear, 3-trunk
    area_map = {'front': 1, 'rear': 2, 'trunk': 3}
    chapter_number = area_map.get(area)
    if not chapter_number:
        return jsonify({'error': 'Некорректная зона'}), 400

    chapter = ReportChapter.query.filter_by(report_id=report.id, chapter_number=chapter_number).first()
    if not chapter:
        chapter = ReportChapter(report_id=report.id, chapter_number=chapter_number, title=f'Салон: {area}', content=comment)
        db.session.add(chapter)
    else:
        chapter.content = comment
    db.session.commit()

    # Сохраняем отмеченные пункты (checks) как текст (можно расширить под отдельную таблицу)
    chapter.extra = checks  # Нужно добавить поле extra в модель ReportChapter, если его нет
    db.session.commit()

    # Сохраняем фото
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        photo = ReportPhoto(path=filename, description='', chapter_id=chapter.id)
        db.session.add(photo)
        db.session.commit()

    return jsonify({'message': 'Данные зоны салона сохранены'}), 200

@app.route('/api/report/completed_sections/<int:order_id>', methods=['GET'])
def get_completed_sections(order_id):
    """
    Возвращает список завершённых разделов по заявке (order_id).
    Раздел считается завершённым, если по нему есть глава отчёта (ReportChapter).
    Названия разделов: salon, shiny, fary, podveska, electric, tormoz
    """
    # Карта соответствия chapter_number -> section_name
    section_map = {
        1: 'salon',
        2: 'shiny',
        3: 'fary',
        4: 'podveska',
        5: 'electric',
        6: 'tormoz',
    }
    report = Report.query.filter_by(order_id=order_id).first()
    if not report:
        return jsonify({'completed_sections': []})
    chapters = ReportChapter.query.filter_by(report_id=report.id).all()
    completed = set()
    for chapter in chapters:
        section = section_map.get(chapter.chapter_number)
        if section:
            completed.add(section)
    return jsonify({'completed_sections': list(completed)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5010)