from flask import Flask, render_template, jsonify, redirect, url_for, request, flash, session, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
from datetime import datetime, timedelta
import pandas as pd
import mysql.connector
import bcrypt
import logging
from typing import List, Optional, Dict, Any
import os
import tempfile
from pytz import timezone

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определяем базовую директорию проекта
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
            static_folder=os.path.join(basedir, 'static'),
            template_folder=os.path.join(basedir, 'templates'))
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TIMEOUT'] = timedelta(hours=1)

# Security settings for brute-force protection
app.config['MAX_LOGIN_ATTEMPTS'] = 3  # Максимум неудачных попыток
app.config['BLOCK_DURATION'] = timedelta(minutes=15)  # Блокировка на 15 минут

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

MYSQL_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'tourism', 'password': 'tourism123',
    'database': 'daily_tourism', 'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci', 'use_unicode': True,
}

# Часовой пояс сервера (Москва, UTC+3)
SERVER_TIMEZONE = timezone('Europe/Moscow')

def format_datetime_to_server(dt):
    """Форматирование datetime в строку (MySQL NOW() возвращает время в часовом поясе сервера БД)"""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    # MySQL NOW() возвращает время в часовом поясе сервера БД
    # Поэтому просто форматируем naive datetime как есть
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# Конфигурация прав по умолчанию
DEFAULT_PERMISSIONS = {
    'admin': {
        'users': ['view', 'create', 'update', 'delete'],
        'roles': ['view', 'create', 'update', 'delete'],
        'permissions': ['view', 'create', 'update', 'delete'],
        'data': ['view', 'export'],
        'audit_log': ['view'],
        'settings': ['view', 'update'],
        'profile': ['update'],
        '_can_view_all': True  # Админ видит всё по умолчанию
    },
    'manager': {
        'users': ['view'],
        'roles': ['view'],
        'permissions': ['view'],
        'data': ['view', 'export'],
        'audit_log': [],
        'settings': [],
        'profile': ['update'],
        '_can_view_all': False  # Менеджер видит только назначенное
    },
    'user': {
        'users': [],
        'roles': [],
        'permissions': [],
        'data': ['view'],
        'audit_log': [],
        'settings': [],
        'profile': ['update'],
        '_can_view_all': False  # Пользователь видит только назначенное
    }
}

class User(UserMixin):
    def __init__(self, id: int, username: str, full_name: str, role: str, is_active: bool = True):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.role = role
        self._is_active = is_active  # Используем приватное свойство
        self.permissions: Dict[str, List[str]] = {}
        self.last_login: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self._is_active
    
    @property
    def is_anonymous(self) -> bool:
        return False
    
    @property
    def is_authenticated(self) -> bool:
        return True
    
    def get_id(self) -> str:
        return str(self.id)
    
    def has_permission(self, resource: str, action: str) -> bool:
        """Проверка права доступа к ресурсу"""
        return action in self.permissions.get(resource, [])
    
    def has_any_permission(self, resource: str, actions: List[str]) -> bool:
        """Проверка наличия любого из указанных прав"""
        return any(action in self.permissions.get(resource, []) for action in actions)

@login_manager.user_loader
def load_user(user_id: str):
    """Загрузка пользователя по ID"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT id, username, full_name, role, is_active FROM users WHERE id = %s AND is_active = TRUE',
            (user_id,)
        )
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                full_name=user_data['full_name'],
                role=user_data['role'],
                is_active=user_data['is_active']
            )
            # Загружаем права пользователя
            user.permissions = get_user_permissions_dict(user.id)
            return user
    except Exception as e:
        logger.error(f'Error loading user {user_id}: {e}')
    return None

def get_user_permissions_dict(user_id: int) -> Dict[str, List[str]]:
    """Получение прав пользователя из БД"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        
        # Получаем роль пользователя
        cursor1 = conn.cursor(dictionary=True, buffered=True)
        cursor1.execute('SELECT role FROM users WHERE id = %s', (user_id,))
        user = cursor1.fetchone()
        cursor1.close()
        
        if not user:
            conn.close()
            return {}
    
        role = user['role']
        permissions = DEFAULT_PERMISSIONS.get(role, {}).copy()
        
        # Получаем кастомные права из БД
        cursor2 = conn.cursor(dictionary=True, buffered=True)
        cursor2.execute('SELECT can_view_all, can_export FROM permissions WHERE user_id = %s', (user_id,))
        perm = cursor2.fetchone()
        cursor2.close()
        
        # Если в БД нет записи, используем значения по умолчанию
        if not perm:
            can_view_all = permissions.pop('_can_view_all', False)
            can_export = 'export' in permissions.get('data', [])
        else:
            can_view_all = bool(perm.get('can_view_all', 0))
            can_export = bool(perm.get('can_export', 0))
        
        # Обновляем права на данные
        if can_view_all:
            permissions['data'] = ['view', 'export']
        if can_export and 'export' not in permissions.get('data', []):
            if 'view' in permissions.get('data', []):
                permissions['data'].append('export')
            else:
                permissions['data'] = ['view', 'export']
        
        # Получаем разрешённые подразделения
        cursor3 = conn.cursor(dictionary=True, buffered=True)
        cursor3.execute('SELECT DISTINCT subdivision FROM permissions_subdivisions WHERE user_id = %s', (user_id,))
        allowed_subs = [row['subdivision'] for row in cursor3.fetchall()]
        cursor3.close()
        
        # Получаем разрешённые отделы
        cursor4 = conn.cursor(dictionary=True, buffered=True)
        cursor4.execute('SELECT DISTINCT otdel FROM permissions_otdels WHERE user_id = %s', (user_id,))
        allowed_otdels = [row['otdel'] for row in cursor4.fetchall()]
        cursor4.close()
        
        conn.close()

        # Сохраняем ограничения по ресурсам
        if can_view_all:
            permissions['_allowed_subdivisions'] = None
            permissions['_allowed_otdels'] = None
        else:
            if not allowed_subs and not allowed_otdels:
                permissions['_allowed_subdivisions'] = None
                permissions['_allowed_otdels'] = None
            else:
                permissions['_allowed_subdivisions'] = allowed_subs if allowed_subs else []
                permissions['_allowed_otdels'] = allowed_otdels if allowed_otdels else []
        
        return permissions
    except Exception as e:
        logger.error(f'Error getting permissions for user {user_id}: {e}')
        import traceback
        traceback.print_exc()
        return {}

def log_action(user_id: int, action: str, resource: str, details: Optional[Dict] = None):
    """Логирование действия пользователя"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO audit_log (user_id, action, resource, details, created_at) 
               VALUES (%s, %s, %s, %s, NOW())''',
            (user_id, action, resource, str(details) if details else None)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f'Error logging action: {e}')

def check_user_lockout(user_id: int) -> tuple[bool, Optional[datetime], int]:
    """
    Проверка блокировки пользователя
    Возвращает: (заблокирован, время разблокировки, оставшиеся попытки)
    """
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT failed_login_attempts, locked_until FROM users WHERE id = %s',
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            return False, None, 0
        
        failed_attempts = user['failed_login_attempts'] or 0
        locked_until = user['locked_until']
        
        # Проверяем, истёк ли срок блокировки
        if locked_until and datetime.now() < locked_until:
            return True, locked_until, 0
        
        # Если блокировка истекла, сбрасываем счётчик
        if locked_until and datetime.now() >= locked_until:
            return False, None, max(0, app.config['MAX_LOGIN_ATTEMPTS'] - failed_attempts)
        
        return False, None, max(0, app.config['MAX_LOGIN_ATTEMPTS'] - failed_attempts)
    except Exception as e:
        logger.error(f'Error checking user lockout: {e}')
        return False, None, 0

def record_failed_login(conn, user_id: int) -> Optional[datetime]:
    """
    Запись неудачной попытки входа (использует существующее подключение)
    Возвращает время блокировки, если пользователь заблокирован
    """
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT failed_login_attempts, locked_until FROM users WHERE id = %s',
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            return None
        
        failed_attempts = (user['failed_login_attempts'] or 0) + 1
        
        locked_until = None
        if failed_attempts >= app.config['MAX_LOGIN_ATTEMPTS']:
            # Блокируем пользователя
            locked_until = datetime.now() + app.config['BLOCK_DURATION']
            cursor.execute(
                'UPDATE users SET failed_login_attempts = %s, locked_until = %s WHERE id = %s',
                (failed_attempts, locked_until, user_id)
            )
            conn.commit()
            cursor.close()
            log_action(user_id, 'login_blocked', 'auth', {
                'failed_attempts': failed_attempts,
                'locked_until': str(locked_until)
            })
        else:
            cursor.execute(
                'UPDATE users SET failed_login_attempts = %s WHERE id = %s',
                (failed_attempts, user_id)
            )
            conn.commit()
            cursor.close()
        
        return locked_until
    except Exception as e:
        logger.error(f'Error recording failed login: {e}')
        return None

def reset_login_attempts(conn, user_id: int):
    """Сброс счётчика неудачных попыток после успешного входа (использует существующее подключение)"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = %s',
            (user_id,)
        )
        conn.commit()
        cursor.close()
    except Exception as e:
        logger.error(f'Error resetting login attempts: {e}')

def check_permission(resource: str, actions: List[str]):
    """Декоратор для проверки прав доступа"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            # Админ имеет все права
            if current_user.role == 'admin':
                return f(*args, **kwargs)
            
            # Проверяем права
            if not current_user.has_any_permission(resource, actions):
                logger.warning(f'User {current_user.username} denied access to {resource}:{actions}')
                flash('У вас нет прав для выполнения этого действия', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.before_request
def before_request():
    """Middleware перед каждым запросом"""
    # Пропускаем проверку для страницы входа и API здоровья
    if request.path in ['/login', '/health']:
        return
    
    if current_user.is_authenticated:
        g.user = current_user
        # Проверка таймаута сессии
        if session.get('last_activity'):
            try:
                last_activity = datetime.fromisoformat(session['last_activity'])
                if datetime.now() - last_activity > app.config['SESSION_TIMEOUT']:
                    logout_user()
                    session.clear()
                    flash('Сессия истекла. Пожалуйста, войдите снова.', 'info')
                    return redirect(url_for('login'))
            except (ValueError, TypeError):
                # Если дата некорректна, считаем сессию устаревшей
                logout_user()
                session.clear()
                return redirect(url_for('login'))
        session['last_activity'] = datetime.now().isoformat()

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    error = None
    lockout_info = None
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        logger.info(f'Login attempt for user: {username}')
        
        if not username or not password:
            error = 'Введите логин и пароль'
        else:
            conn = None
            try:
                conn = mysql.connector.connect(**MYSQL_CONFIG)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    'SELECT id, username, password_hash, full_name, role, is_active, last_login, failed_login_attempts, locked_until FROM users WHERE username = %s',
                    (username,)
                )
                user = cursor.fetchone()
                cursor.close()
                
                if not user:
                    error = 'Пользователь не найден'
                    logger.warning(f'Login failed: user {username} not found')
                elif not user.get('is_active'):
                    error = 'Пользователь заблокирован'
                    logger.warning(f'Login failed: user {username} is inactive')
                elif user.get('locked_until'):
                    # Проверка, истёк ли срок блокировки
                    locked_until = user['locked_until']
                    if isinstance(locked_until, str):
                        locked_until = datetime.fromisoformat(locked_until)
                    
                    if datetime.now() < locked_until:
                        # Пользователь всё ещё заблокирован
                        remaining = locked_until - datetime.now()
                        minutes = int(remaining.total_seconds() // 60)
                        seconds = int(remaining.total_seconds() % 60)
                        error = f'Слишком много неудачных попыток. Попробуйте через {minutes} мин. {seconds} сек.'
                        lockout_info = {'locked_until': locked_until, 'remaining_seconds': remaining.total_seconds()}
                        logger.warning(f'Login failed: user {username} is locked until {locked_until}')
                    else:
                        # Блокировка истекла, сбрасываем
                        cursor = conn.cursor()
                        cursor.execute(
                            'UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = %s',
                            (user['id'],)
                        )
                        conn.commit()
                        cursor.close()
                        # Продолжаем проверку пароля
                else:
                    # Проверяем пароль - password_hash может быть в разных форматах
                    password_hash = user['password_hash']
                    if isinstance(password_hash, str):
                        try:
                            password_hash_bytes = password_hash.encode('utf-8')
                        except:
                            password_hash_bytes = password_hash
                    
                    try:
                        password_valid = bcrypt.checkpw(password.encode('utf-8'), password_hash_bytes)
                        logger.info(f'Password check result for {username}: {password_valid}')
                    except Exception as bcrypt_err:
                        logger.error(f'Bcrypt error for {username}: {bcrypt_err}')
                        password_valid = False
                    
                    if not password_valid:
                        # Записываем неудачную попытку (используем существующее подключение)
                        locked_until = record_failed_login(conn, user['id'])
                        error = 'Неверный пароль'
                        
                        if locked_until:
                            # Пользователь заблокирован
                            remaining = locked_until - datetime.now()
                            minutes = int(remaining.total_seconds() // 60)
                            seconds = int(remaining.total_seconds() % 60)
                            error = f'Неверный пароль. Слишком много попыток. Блокировка на {minutes} мин. {seconds} сек.'
                            lockout_info = {'locked_until': locked_until, 'remaining_seconds': remaining.total_seconds()}
                        
                        logger.warning(f'Login failed: wrong password for {username}')
                    else:
                        logger.info(f'User {username} authenticated successfully')
                        # Сбрасываем счётчик неудачных попыток (используем существующее подключение)
                        reset_login_attempts(conn, user['id'])
                        
                        user_obj = User(
                            id=user['id'],
                            username=user['username'],
                            full_name=user['full_name'],
                            role=user['role'],
                            is_active=user['is_active']
                        )
                        
                        # Загружаем права пользователя
                        try:
                            user_obj.permissions = get_user_permissions_dict(user['id'])
                            logger.info(f'Permissions loaded for {username}: {user_obj.permissions}')
                        except Exception as perm_err:
                            logger.error(f'Error loading permissions for {username}: {perm_err}')
                            user_obj.permissions = {}
                        
                        login_user(user_obj)
                        session.permanent = True
                        
                        # Обновляем last_login и логируем в одном подключении
                        try:
                            update_conn = mysql.connector.connect(**MYSQL_CONFIG)
                            update_cursor = update_conn.cursor()
                            update_cursor.execute('UPDATE users SET last_login = NOW() WHERE id = %s', (user['id'],))
                            update_cursor.execute(
                                'INSERT INTO audit_log (user_id, action, resource, details, created_at) VALUES (%s, %s, %s, %s, NOW())',
                                (user['id'], 'login', 'auth', str({'username': username}))
                            )
                            update_conn.commit()
                            update_cursor.close()
                            update_conn.close()
                            logger.info(f'Login successful for {username}')
                        except Exception as log_err:
                            logger.error(f'Error during login update for {username}: {log_err}')
                        
                        return redirect('/dashboard.html')
            except mysql.connector.Error as mysql_err:
                logger.error(f'MySQL error during login for {username}: {mysql_err}')
                error = 'Внутренняя ошибка сервера'
            except Exception as e:
                logger.error(f'Login error for {username}: {e}')
                import traceback
                traceback.print_exc()
                error = 'Внутренняя ошибка сервера'
            finally:
                if conn and conn.is_connected():
                    conn.close()
    
    return render_template('login.html', error=error, lockout_info=lockout_info)

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    if current_user.is_authenticated:
        log_action(current_user.id, 'logout', 'auth', {'username': current_user.username})
    logout_user()
    return redirect(url_for('login'))

def render_dashboard():
    """Общая функция отрисовки дашборда"""
    # Проверяем права на экспорт
    can_export = current_user.has_permission('data', 'export')
    
    return render_template(
        'dashboard.html',
        user_name=current_user.full_name,
        role=current_user.role,
        can_export=can_export
    )

@app.route('/')
@login_required
def dashboard():
    """Главная панель (дашборд) по маршруту /"""
    return render_dashboard()

@app.route('/dashboard.html')
@login_required
def dashboard_html():
    """Главная панель (дашборд) по маршруту /dashboard.html"""
    return render_dashboard()

@app.route('/api/data')
@login_required
def api_data():
    """API для получения данных с учётом прав доступа"""
    logger.info(f'API: User {current_user.username} ({current_user.role}) requesting data...')
    conn = None
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        
        # Проверяем права на просмотр данных
        if not current_user.has_permission('data', 'view'):
            logger.warning(f'User {current_user.username} denied access to data view')
            return jsonify({'error': 'У вас нет прав для просмотра данных'}), 403
        
        # Получаем ограничения из прав
        permissions = current_user.permissions
        allowed_subdivisions = permissions.get('_allowed_subdivisions', None)
        allowed_otdels = permissions.get('_allowed_otdels', None)
        
        # Администраторы видят всё по умолчанию, если нет явных ограничений
        is_admin = current_user.role == 'admin'
        
        # Формируем запрос с фильтрацией
        if is_admin and allowed_subdivisions is None and allowed_otdels is None:
            # Админ без ограничений - видит всё
            query = 'SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo FROM records ORDER BY data DESC'
            df = pd.read_sql(query, conn)
        elif allowed_subdivisions is None and allowed_otdels is None:
            # Не админ без ограничений - тоже видит всё (для совместимости)
            query = 'SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo FROM records ORDER BY data DESC'
            df = pd.read_sql(query, conn)
        else:
            # Есть ограничения - фильтруем
            conditions = []
            params = []
            
            # Если есть ограничения по подразделениям И отделам - используем AND
            if allowed_subdivisions is not None and allowed_otdels is not None:
                if len(allowed_subdivisions) > 0 and len(allowed_otdels) > 0:
                    # (подразделение IN (...) AND отдел IN (...))
                    sub_placeholders = ','.join(['%s'] * len(allowed_subdivisions))
                    otdel_placeholders = ','.join(['%s'] * len(allowed_otdels))
                    query = f'''
                        SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo 
                        FROM records 
                        WHERE podrazdelenie IN ({sub_placeholders}) 
                        AND otdel IN ({otdel_placeholders})
                        ORDER BY data DESC
                    '''
                    params.extend(allowed_subdivisions)
                    params.extend(allowed_otdels)
                    df = pd.read_sql(query, conn, params=params)
                elif len(allowed_subdivisions) > 0:
                    # Только подразделения
                    placeholders = ','.join(['%s'] * len(allowed_subdivisions))
                    query = f'''
                        SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo 
                        FROM records 
                        WHERE podrazdelenie IN ({placeholders})
                        ORDER BY data DESC
                    '''
                    df = pd.read_sql(query, conn, params=allowed_subdivisions)
                elif len(allowed_otdels) > 0:
                    # Только отделы
                    placeholders = ','.join(['%s'] * len(allowed_otdels))
                    query = f'''
                        SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo 
                        FROM records 
                        WHERE otdel IN ({placeholders})
                        ORDER BY data DESC
                    '''
                    df = pd.read_sql(query, conn, params=allowed_otdels)
                else:
                    # Нет ограничений
                    query = 'SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo FROM records ORDER BY data DESC'
                    df = pd.read_sql(query, conn)
            elif allowed_subdivisions is not None and len(allowed_subdivisions) > 0:
                # Только подразделения
                placeholders = ','.join(['%s'] * len(allowed_subdivisions))
                query = f'SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo FROM records WHERE podrazdelenie IN ({placeholders}) ORDER BY data DESC'
                df = pd.read_sql(query, conn, params=allowed_subdivisions)
            elif allowed_otdels is not None and len(allowed_otdels) > 0:
                # Только отделы
                placeholders = ','.join(['%s'] * len(allowed_otdels))
                query = f'SELECT fio, snils, sp_nsp, rukovoditel, podrazdelenie, otdel, dolzhnost, stavka, status_field, data, chasy, nachisleno, itogo FROM records WHERE otdel IN ({placeholders}) ORDER BY data DESC'
                df = pd.read_sql(query, conn, params=allowed_otdels)
            else:
                # Нет разрешённых ресурсов
                df = pd.DataFrame(columns=['fio', 'snils', 'sp_nsp', 'rukovoditel', 'podrazdelenie', 'otdel', 'dolzhnost', 'stavka', 'status_field', 'data', 'chasy', 'nachisleno', 'itogo'])
       
        df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
        logger.info(f'API: Returning {len(df)} records for user {current_user.username}')
        return jsonify(df.to_dict('records'))
    
    except Exception as e:
        logger.error(f'API Error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

    finally:
        if conn and conn.is_connected():
            conn.close()

# ==================== LFL ANALYSIS API ====================

@app.route('/api/lfl')
@login_required
def api_lfl():
    """API для LFL (Like-for-Like) анализа сравнения периодов"""
    logger.info(f'LFL API: User {current_user.username} requesting LFL data...')
    
    # Получаем параметры из запроса
    mode = request.args.get('mode', 'month')  # month, week, custom
    custom_from = request.args.get('custom_from')
    custom_to = request.args.get('custom_to')
    prev_from = request.args.get('prev_from')
    prev_to = request.args.get('prev_to')
    
    # Получаем текущие фильтры (опционально)
    filter_from = request.args.get('filter_from')
    filter_to = request.args.get('filter_to')
    selected_pod = request.args.get('selected_pod')
    selected_otdels = request.args.getlist('selected_otdel')  # Множественный выбор отделов
    # Убираем пустые строки
    selected_otdels = [o for o in selected_otdels if o]
    
    logger.info(f'LFL Params: mode={mode}, custom_from={custom_from}, custom_to={custom_to}, prev_from={prev_from}, prev_to={prev_to}')
    
    conn = None
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        
        # Проверяем права на просмотр данных
        if not current_user.has_permission('data', 'view'):
            logger.warning(f'LFL API: User {current_user.username} denied access')
            return jsonify({'error': 'У вас нет прав для просмотра данных'}), 403
        
        # Определяем периоды для сравнения
        # Приоритет: если переданы custom_from/custom_to/prev_from/prev_to - используем их для любого режима
        if custom_from and custom_to and prev_from and prev_to:
            # Используем явные периоды из параметров (для всех режимов)
            period_to = (custom_from, custom_to)
            period_prev = (prev_from, prev_to)
            logger.info(f'LFL Explicit periods: {period_to} vs {period_prev}')
        elif mode == 'custom':
            # Пользовательский режим без явных периодов - ошибка
            logger.warning('LFL Custom mode without explicit periods')
            return jsonify({'error': 'Для режима custom должны быть указаны периоды'}), 400
        elif mode == 'week':
            # Неделя к неделе (последние 7 дней vs предыдущие 7 дней)
            today = datetime.now()
            period_to = ((today - timedelta(days=6)).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
            prev_end = today - timedelta(days=7)
            prev_start = prev_end - timedelta(days=6)
            period_prev = (prev_start.strftime('%Y-%m-%d'), prev_end.strftime('%Y-%m-%d'))
            logger.info(f'LFL Week mode: {period_to} vs {period_prev}')
        else:
            # Месяц к месяцу (текущий месяц vs предыдущий месяц) - по умолчанию
            today = datetime.now()
            # Текущий месяц
            current_month_start = today.replace(day=1)
            if today.month == 1:
                prev_month_start = today.replace(year=today.year-1, month=12, day=1)
            else:
                prev_month_start = today.replace(month=today.month-1, day=1)
            
            # Конец предыдущего месяца
            if today.month == 1:
                prev_month_end = prev_month_start.replace(year=today.year, month=1, day=1) - timedelta(days=1)
            else:
                prev_month_end = today.replace(month=today.month, day=1) - timedelta(days=1)
            
            period_to = (current_month_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
            period_prev = (prev_month_start.strftime('%Y-%m-%d'), prev_month_end.strftime('%Y-%m-%d'))
            logger.info(f'LFL Month mode: {period_to} vs {period_prev}')
        
        # Формируем базовый запрос
        def get_period_data(period_start, period_end, allowed_subs, allowed_otdels, period_label=''):
            """Получение данных за период с учётом прав"""
            conditions = ["data >= %s", "data <= %s"]
            params = [period_start, period_end]
            
            # Фильтры из UI
            if selected_pod:
                conditions.append("podrazdelenie = %s")
                params.append(selected_pod)
                logger.info(f'LFL {period_label}: Filter podrazdelenie={selected_pod}')
            if selected_otdels:
                placeholders = ','.join(['%s'] * len(selected_otdels))
                conditions.append(f"otdel IN ({placeholders})")
                params.extend(selected_otdels)
                logger.info(f'LFL {period_label}: Filter otdels={selected_otdels}')
            
            # Ограничения прав пользователя
            if allowed_subs is not None and len(allowed_subs) > 0:
                conditions.append("podrazdelenie IN (%s)" % ','.join(['%s'] * len(allowed_subs)))
                params.extend(allowed_subs)
                logger.info(f'LFL {period_label}: Permission filter subs={allowed_subs}')
            if allowed_otdels is not None and len(allowed_otdels) > 0:
                conditions.append("otdel IN (%s)" % ','.join(['%s'] * len(allowed_otdels)))
                params.extend(allowed_otdels)
                logger.info(f'LFL {period_label}: Permission filter otdels={allowed_otdels}')
            
            query = f'''
                SELECT 
                    fio, snils, podrazdelenie, otdel, dolzhnost, 
                    data, chasy, nachisleno, itogo
                FROM records 
                WHERE {' AND '.join(conditions)}
            '''
            
            logger.info(f'LFL {period_label}: SQL Query: {query[:200]}...')
            logger.info(f'LFL {period_label}: SQL Params: {params}')
            
            df = pd.read_sql(query, conn, params=params)
            logger.info(f'LFL {period_label}: Retrieved {len(df)} records')
            return df
        
        # Получаем ограничения прав пользователя
        permissions = current_user.permissions
        allowed_subs = permissions.get('_allowed_subdivisions', None)
        allowed_otdels = permissions.get('_allowed_otdels', None)
        
        logger.info(f'LFL: Getting data for current period {period_to[0]} to {period_to[1]}')
        logger.info(f'LFL: Getting data for previous period {period_prev[0]} to {period_prev[1]}')
        
        # Получаем данные за оба периода
        df_current = get_period_data(period_to[0], period_to[1], allowed_subs, allowed_otdels, 'CURRENT')
        df_prev = get_period_data(period_prev[0], period_prev[1], allowed_subs, allowed_otdels, 'PREVIOUS')
        
        # Рассчитываем агрегированные показатели
        def calc_metrics(df):
            if df.empty:
                logger.warning('LFL: Empty DataFrame - returning zeros')
                return {
                    'employees': 0,
                    'hours': 0,
                    'money': 0,
                    'records': 0
                }
            result = {
                'employees': int(df['fio'].nunique()),
                'hours': float(df['chasy'].sum()),
                'money': float(df['itogo'].sum()),
                'records': len(df)
            }
            logger.info(f'LFL: Metrics calculated: {result}')
            return result
        
        metrics_current = calc_metrics(df_current)
        metrics_prev = calc_metrics(df_prev)
        
        # Рассчитываем изменение в %
        def calc_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100
        
        # Формируем ответ
        result = {
            'period_current': {
                'from': period_to[0],
                'to': period_to[1],
                'metrics': metrics_current
            },
            'period_previous': {
                'from': period_prev[0],
                'to': period_prev[1],
                'metrics': metrics_prev
            },
            'change': {
                'employees': calc_change(metrics_current['employees'], metrics_prev['employees']),
                'hours': calc_change(metrics_current['hours'], metrics_prev['hours']),
                'money': calc_change(metrics_current['money'], metrics_prev['money']),
                'records': calc_change(metrics_current['records'], metrics_prev['records'])
            },
            'delta': {
                'employees': metrics_current['employees'] - metrics_prev['employees'],
                'hours': metrics_current['hours'] - metrics_prev['hours'],
                'money': metrics_current['money'] - metrics_prev['money'],
                'records': metrics_current['records'] - metrics_prev['records']
            }
        }
        
        logger.info(f'LFL API: Returning data for periods {period_to} vs {period_prev}')
        return jsonify(result)
    
    except Exception as e:
        logger.error(f'LFL API Error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/admin')
@login_required
def admin_panel():
    """Главная страница админ-панели"""
    # Проверяем: если у пользователя нет вообще никаких прав админки, перенаправляем на дашборд
    if not (current_user.has_any_permission('users', ['view']) or 
            current_user.has_any_permission('permissions', ['view']) or
            current_user.has_any_permission('roles', ['view']) or
            current_user.has_any_permission('audit_log', ['view']) or
            current_user.has_any_permission('profile', ['update'])):
        return redirect(url_for('dashboard'))
    
    log_action(current_user.id, 'view', 'admin_panel', {})
    return render_template(
        'admin.html',
        user_name=current_user.full_name,
        role=current_user.role,
        current_user_id=current_user.id
    )

# ==================== USER MANAGEMENT ====================

@app.route('/admin/users')
@login_required
@check_permission('users', ['view'])
def get_users():
    """Получение списка пользователей"""
    log_action(current_user.id, 'view', 'users', {'action': 'list'})
    
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT id, username, full_name, role, is_active, last_login, created_at 
        FROM users 
        ORDER BY id
    ''')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Преобразуем даты в строки с явным указанием формата (YYYY-MM-DD HH:MM:SS) в часовом поясе сервера
    for user in users:
        if user.get('last_login'):
            user['last_login'] = format_datetime_to_server(user['last_login'])
        if user.get('created_at'):
            user['created_at'] = format_datetime_to_server(user['created_at'])
    
    return jsonify(users)

@app.route('/admin/users', methods=['POST'])
@login_required
@check_permission('users', ['create', 'update'])
def create_or_update_user():
    """Создание или обновление пользователя"""
    data = request.get_json()
    username = data.get('username', '').strip()
    full_name = data.get('full_name', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')
    is_active = data.get('is_active', True)
    user_id = data.get('id')

    if not username:
        return jsonify({'error': 'Логин обязателен'}), 400

    # Валидация роли
    valid_roles = ['admin', 'manager', 'user']
    if role not in valid_roles:
        return jsonify({'error': f'Неверная роль. Допустимые: {", ".join(valid_roles)}'}), 400

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        if user_id:
            # Обновление существующего пользователя
            cursor.execute('SELECT id, role FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'Пользователь не найден'}), 404
            
            # Проверка: нельзя изменить роль другого админа на не-admin
            if user_id == current_user.id and role != 'admin':
                return jsonify({'error': 'Нельзя изменить свою роль на не-админ'}), 400
            
            if password:
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute('''
                    UPDATE users SET username=%s, full_name=%s, password_hash=%s, role=%s, is_active=%s 
                    WHERE id=%s
                ''', (username, full_name, password_hash, role, is_active, user_id))
                log_action(current_user.id, 'update', 'user', {
                    'user_id': user_id, 'action': 'update_with_password'
                })
            else:
                cursor.execute('''
                    UPDATE users SET username=%s, full_name=%s, role=%s, is_active=%s 
                    WHERE id=%s
                ''', (username, full_name, role, is_active, user_id))
                log_action(current_user.id, 'update', 'user', {
                    'user_id': user_id, 'action': 'update_without_password'
                })
        else:
            # Создание нового пользователя
            cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                return jsonify({'error': 'Пользователь с таким логином уже существует'}), 400

            if not password:
                return jsonify({'error': 'Пароль обязателен для нового пользователя'}), 400

            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, role, is_active) 
                VALUES (%s, %s, %s, %s, %s)
            ''', (username, password_hash, full_name, role, is_active))
            
            new_user_id = cursor.lastrowid
            
            # Создаём права по умолчанию для роли (используем INSERT IGNORE для избежания дубликатов)
            default_perms = DEFAULT_PERMISSIONS.get(role, {})
            can_view_all = 1 if default_perms.get('_can_view_all', False) else 0
            can_export = 1 if 'export' in default_perms.get('data', []) else 0
            cursor.execute('''
                INSERT IGNORE INTO permissions (user_id, can_view_all, can_export)
                VALUES (%s, %s, %s) 
            ''', (new_user_id, can_view_all, can_export))
            
            log_action(current_user.id, 'create', 'user', {'user_id': new_user_id, 'username': username, 'role': role})
        
        conn.commit()
        return jsonify({'success': True})
    
    except Exception as e:
        conn.rollback()
        logger.error(f'Error creating/updating user: {e}')
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@check_permission('users', ['delete'])
def delete_user(user_id: int):
    """Удаление пользователя"""
    if user_id == current_user.id:
        return jsonify({'error': 'Нельзя удалить самого себя'}), 400

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        log_action(current_user.id, 'delete', 'user', {'user_id': user_id})
    except Exception as e:
        conn.rollback()
        logger.error(f'Error deleting user: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({'success': True})

# ==================== SUBDIVISIONS & OTDELS ====================

@app.route('/admin/subdivisions')
@login_required
@check_permission('users', ['view'])
def get_subdivisions():
    """Получение списка подразделений и отделов"""
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT DISTINCT podrazdelenie FROM records WHERE podrazdelenie IS NOT NULL ORDER BY podrazdelenie')
        subdivisions = [row[0] for row in cursor.fetchall()]
        cursor.execute('SELECT DISTINCT otdel FROM records WHERE otdel IS NOT NULL ORDER BY otdel')
        otdels = [row[0] for row in cursor.fetchall()]
        return jsonify({'subdivisions': subdivisions, 'otdels': otdels})
    finally:
        cursor.close()
        conn.close()


def _apply_permission_filters(base_conditions: list, params: list):
    """Helper: применить ограничения пользователя (подразделения/отделы) к условию и параметрам."""
    permissions = current_user.permissions if current_user.is_authenticated else {}
    allowed_subs = permissions.get('_allowed_subdivisions', None)
    allowed_otdels = permissions.get('_allowed_otdels', None)

    if allowed_subs is not None and isinstance(allowed_subs, list) and len(allowed_subs) > 0:
        base_conditions.append("podrazdelenie IN (%s)" % ','.join(['%s'] * len(allowed_subs)))
        params.extend(allowed_subs)
    if allowed_otdels is not None and isinstance(allowed_otdels, list) and len(allowed_otdels) > 0:
        base_conditions.append("otdel IN (%s)" % ','.join(['%s'] * len(allowed_otdels)))
        params.extend(allowed_otdels)

    return base_conditions, params


@app.route('/api/fot/summary')
@login_required
def api_fot_summary():
    """Возвращает суммарные метрики ФОТ и series по периодам (day/week/month).
    Параметры: from,to,granularity=day|week|month,pod,otdel
    """
    if not current_user.has_permission('data', 'view'):
        return jsonify({'error': 'У вас нет прав для просмотра данных'}), 403

    date_from = request.args.get('from')
    date_to = request.args.get('to')
    gran = request.args.get('granularity', 'day')
    pod = request.args.get('pod')
    otdels = request.args.getlist('otdel')  # Множественный выбор отделов
    otdels = [o for o in otdels if o]  # Убираем пустые строки

    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)

        # Базовые условия
        conditions = []
        params = []
        if date_from:
            conditions.append('data >= %s')
            params.append(date_from)
        if date_to:
            conditions.append('data <= %s')
            params.append(date_to)
        if pod:
            conditions.append('podrazdelenie = %s')
            params.append(pod)
        if otdels:
            placeholders = ','.join(['%s'] * len(otdels))
            conditions.append(f'otdel IN ({placeholders})')
            params.extend(otdels)

        # Apply permission filters
        conditions, params = _apply_permission_filters(conditions, params)

        # Granularity to expression
        if gran == 'month':
            grp = "DATE_FORMAT(data, '%%Y-%%m')"
            label = 'month'
        elif gran == 'week':
            grp = "YEARWEEK(data, 1)"
            label = 'week'
        else:
            grp = 'DATE(data)'
            label = 'day'

        where_clause = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

        totals_q = f"SELECT SUM(itogo) AS total_money, SUM(chasy) AS total_hours, COUNT(DISTINCT fio) AS employees, SUM(nachisleno) AS total_nachisleno, COUNT(*) AS records FROM records {where_clause}"
        cursor = conn.cursor(dictionary=True)
        cursor.execute(totals_q, tuple(params))
        totals = cursor.fetchone() or {'total_money': 0, 'total_hours': 0, 'employees': 0, 'total_nachisleno': 0, 'records': 0}

        # Series
        series_q = f"SELECT {grp} AS period, SUM(itogo) AS total_money, SUM(chasy) AS total_hours, COUNT(DISTINCT fio) AS employees FROM records {where_clause} GROUP BY {grp} ORDER BY {grp}"
        df = pd.read_sql(series_q, conn, params=params)

        # avg_rate safe
        total_hours = float(totals.get('total_hours') or 0)
        total_nach = float(totals.get('total_nachisleno') or 0)
        avg_rate = (total_nach / total_hours) if total_hours > 0 else 0

        result = {
            'period': {'from': date_from, 'to': date_to},
            'totals': {
                'total_money': float(totals.get('total_money') or 0),
                'total_hours': total_hours,
                'employees': int(totals.get('employees') or 0),
                'avg_rate': avg_rate,
                'records': int(totals.get('records') or 0)
            },
            'series': df.to_dict('records')
        }

        cursor.close()
        return jsonify(result)

    except Exception as e:
        logger.error(f'API FOT Summary Error: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()


@app.route('/api/fot/breakdown')
@login_required
def api_fot_breakdown():
    """Возвращает разбивку ФОТ по подразделениям/отделам/должностям.
    Параметры: from,to,by=podrazdelenie|otdel|dolzhnost,limit
    """
    if not current_user.has_permission('data', 'view'):
        return jsonify({'error': 'У вас нет прав для просмотра данных'}), 403

    date_from = request.args.get('from')
    date_to = request.args.get('to')
    by = request.args.get('by', 'podrazdelenie')
    otdels = request.args.getlist('otdel')  # Множественный выбор отделов
    otdels = [o for o in otdels if o]
    limit = int(request.args.get('limit', 50))

    if by not in ('podrazdelenie', 'otdel', 'dolzhnost'):
        by = 'podrazdelenie'

    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        conditions = []
        params = []
        if date_from:
            conditions.append('data >= %s')
            params.append(date_from)
        if date_to:
            conditions.append('data <= %s')
            params.append(date_to)
        if otdels:
            placeholders = ','.join(['%s'] * len(otdels))
            conditions.append(f'otdel IN ({placeholders})')
            params.extend(otdels)

        conditions, params = _apply_permission_filters(conditions, params)

        where_clause = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

        q = f"SELECT `{by}` AS `key`, SUM(itogo) AS total_money, SUM(chasy) AS total_hours, COUNT(DISTINCT fio) AS employees, COUNT(*) AS shifts, SUM(nachisleno) AS total_nachisleno FROM records {where_clause} GROUP BY `{by}` ORDER BY total_money DESC LIMIT %s"
        params_with_limit = list(params) + [limit]

        df = pd.read_sql(q, conn, params=params_with_limit)

        overall_q = f"SELECT SUM(itogo) AS overall_money FROM records {where_clause}"
        cursor.execute(overall_q, tuple(params))
        overall = cursor.fetchone() or {'overall_money': 0}

        cursor.close()

        overall_money = float(overall.get('overall_money') or 0)
        breakdown = []
        for row in df.to_dict('records'):
            total_money = float(row.get('total_money') or 0)
            total_hours = float(row.get('total_hours') or 0)
            employees = int(row.get('employees') or 0)
            avg_rate = (float(row.get('total_nachisleno') or 0) / total_hours) if total_hours > 0 else 0
            share = (total_money / overall_money) if overall_money > 0 else 0
            breakdown.append({
                'key': row.get('key'),
                'total_money': total_money,
                'total_hours': total_hours,
                'employees': employees,
                'shifts': int(row.get('shifts') or 0),
                'avg_rate': avg_rate,
                'share': share
            })

        return jsonify({'by': by, 'overall_money': overall_money, 'breakdown': breakdown})

    except Exception as e:
        logger.error(f'API FOT Breakdown Error: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

# ==================== PERMISSIONS MANAGEMENT ====================

@app.route('/admin/permissions/<int:user_id>')
@login_required
@check_permission('permissions', ['view'])
def get_user_permissions(user_id: int):
    """Получение прав пользователя"""
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    
    try:
        # Получаем основные права
        cursor1 = conn.cursor(dictionary=True)
        cursor1.execute('SELECT can_view_all, can_export FROM permissions WHERE user_id = %s', (user_id,))
        perm = cursor1.fetchone()
        cursor1.close()
        
        if not perm:
            perm = {'can_view_all': False, 'can_export': False}
        
        # Получаем подразделения
        cursor2 = conn.cursor(dictionary=True)
        cursor2.execute('SELECT DISTINCT subdivision FROM permissions_subdivisions WHERE user_id = %s', (user_id,))
        subdivisions = [row['subdivision'] for row in cursor2.fetchall()]
        cursor2.close()
        
        # Получаем отделы
        cursor3 = conn.cursor(dictionary=True)
        cursor3.execute('SELECT DISTINCT otdel FROM permissions_otdels WHERE user_id = %s', (user_id,))
        otdels = [row['otdel'] for row in cursor3.fetchall()]
        cursor3.close()
        
        return jsonify({
            'can_view_all': bool(perm.get('can_view_all', False)),
            'can_export': bool(perm.get('can_export', False)),
            'subdivisions': subdivisions,
            'otdels': otdels
        })
    except Exception as e:
        logger.error(f'Error getting user permissions: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/admin/permissions', methods=['POST'])
@login_required
@check_permission('permissions', ['update'])
def save_permissions():
    """Сохранение прав пользователя"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        can_view_all = data.get('can_view_all', False)
        can_export = data.get('can_export', False)
        subdivisions = data.get('subdivisions', [])
        otdels = data.get('otdels', [])

        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Сохраняем основные права (используем INSERT ... ON DUPLICATE KEY UPDATE)
            cursor.execute('''
                INSERT INTO permissions (user_id, can_view_all, can_export) 
                VALUES (%s, %s, %s) 
                ON DUPLICATE KEY UPDATE can_view_all=VALUES(can_view_all), can_export=VALUES(can_export)
            ''', (user_id, int(can_view_all), int(can_export)))
            
            # Удаляем старые права на подразделения и отделы
            cursor.execute('DELETE FROM permissions_subdivisions WHERE user_id = %s', (user_id,))
            cursor.execute('DELETE FROM permissions_otdels WHERE user_id = %s', (user_id,))
            
            # Добавляем новые права на подразделения
            for sub in subdivisions:
                sub_val = sub.get('subdivision') or sub.get('value') if isinstance(sub, dict) else sub
                if sub_val:
                    cursor.execute('''
                        INSERT INTO permissions_subdivisions (user_id, subdivision) 
                        VALUES (%s, %s)
                    ''', (user_id, str(sub_val)))
            
            # Добавляем новые права на отделы
            for otd in otdels:
                otd_val = otd.get('otdel') or otd.get('value') if isinstance(otd, dict) else otd
                if otd_val:
                    cursor.execute('''
                        INSERT INTO permissions_otdels (user_id, otdel) 
                        VALUES (%s, %s)
                    ''', (user_id, str(otd_val)))
            
            conn.commit()
            log_action(current_user.id, 'update', 'permissions', {
                'user_id': user_id,
                'can_view_all': can_view_all,
                'can_export': can_export,
                'subdivisions_count': len(subdivisions),
                'otdels_count': len(otdels)
            })
            
            return jsonify({'success': True})
        
        except Exception as e:
            conn.rollback()
            logger.error(f'Error saving permissions: {e}')
            return jsonify({'error': str(e)}), 500
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        logger.error(f'Error in save_permissions: {e}')
        return jsonify({'error': str(e)}), 500

# ==================== PASSWORD CHANGE ====================

@app.route('/admin/change-password', methods=['POST'])
@login_required
def change_password():
    """Смена пароля текущего пользователя"""
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Заполните все поля'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Пароль должен быть не менее 6 символов'}), 400

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT password_hash FROM users WHERE id = %s', (current_user.id,))
        user = cursor.fetchone()
        
        if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'error': 'Неверный текущий пароль'}), 400

        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, current_user.id))
        conn.commit()
        
        log_action(current_user.id, 'update', 'password', {'user_id': current_user.id})
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f'Error changing password: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==================== AUDIT LOG ====================

@app.route('/admin/audit-log')
@login_required
@check_permission('audit_log', ['view'])
def get_audit_log():
    """Получение лога действий"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    user_id_filter = request.args.get('user_id', type=int)
    action_filter = request.args.get('action', '')
    
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Базовый запрос
        query = '''
            SELECT al.*, u.username, u.full_name 
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE 1=1
        '''
        params = []
        
        if user_id_filter:
            query += ' AND al.user_id = %s'
            params.append(user_id_filter)
        
        if action_filter:
            query += ' AND al.action = %s'
            params.append(action_filter)
        
        query += ' ORDER BY al.created_at DESC LIMIT %s OFFSET %s'
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # Получаем общее количество записей
        count_query = '''
            SELECT COUNT(*) as total FROM audit_log al
            WHERE 1=1
        '''
        count_params = []
        
        if user_id_filter:
            count_query += ' AND al.user_id = %s'
            count_params.append(user_id_filter)
        
        if action_filter:
            count_query += ' AND al.action = %s'
            count_params.append(action_filter)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']
        
        return jsonify({
            'logs': logs,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
    
    except Exception as e:
        logger.error(f'Error getting audit log: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==================== ROLES MANAGEMENT ====================

@app.route('/admin/roles')
@login_required
@check_permission('roles', ['view'])
def get_roles():
    """Получение списка ролей"""
    roles = []
    for role_name, permissions in DEFAULT_PERMISSIONS.items():
        roles.append({
            'name': role_name,
            'permissions': permissions
        })
    return jsonify(roles)

@app.route('/admin/stats')
@login_required
@check_permission('users', ['view'])
def get_stats():
    """Получение статистики"""
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Количество пользователей по ролям
        cursor.execute('''
            SELECT role, COUNT(*) as count 
            FROM users 
            GROUP BY role
        ''')
        users_by_role = cursor.fetchall()
        
        # Количество записей в базе
        cursor.execute('SELECT COUNT(*) as total FROM records')
        records_count = cursor.fetchone()['total']
        
        # Последние логины
        cursor.execute('''
            SELECT username, full_name, last_login 
            FROM users 
            WHERE last_login IS NOT NULL 
            ORDER BY last_login DESC 
            LIMIT 10
        ''')
        recent_logins = cursor.fetchall()
        
        # Преобразуем last_login в строку с форматом в часовом поясе сервера
        for login in recent_logins:
            if login.get('last_login'):
                login['last_login'] = format_datetime_to_server(login['last_login'])
        
        return jsonify({
            'users_by_role': users_by_role,
            'records_count': records_count,
            'recent_logins': recent_logins
        })
    
    except Exception as e:
        logger.error(f'Error getting stats: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==================== EXCEL IMPORT ====================

# ==================== EXCEL IMPORT ====================

def _import_records(df, file, sheet_name):
    """Вспомогательная функция импорта данных туризма (records)"""
    if df.empty:
        return jsonify({'error': 'Файл пустой'}), 400
    
    # Маппинг колонок (структура идентична для "Архив" и "Реестр")
    df_mapped = pd.DataFrame()
    df_mapped['snils'] = df.iloc[:, 0].astype(str).str.strip()
    df_mapped['podrazdelenie'] = df.iloc[:, 1].astype(str).str.strip()
    df_mapped['sp_nsp'] = df.iloc[:, 2].astype(str).str.strip()
    df_mapped['fio'] = df.iloc[:, 3].astype(str).str.strip()
    df_mapped['otdel'] = df.iloc[:, 4].astype(str).str.strip()
    df_mapped['dolzhnost'] = df.iloc[:, 5].astype(str).str.strip()
    df_mapped['rukovoditel'] = df.iloc[:, 6].astype(str).str.strip()
    df_mapped['status_field'] = df.iloc[:, 7].astype(str).str.strip()
    df_mapped['data'] = pd.to_datetime(df.iloc[:, 8], errors='coerce')
    df_mapped['chasy'] = pd.to_numeric(df.iloc[:, 9], errors='coerce').fillna(0)
    df_mapped['stavka_oklad'] = df.iloc[:, 10].astype(str).str.strip()
    df_mapped['stavka'] = df.iloc[:, 11].astype(str).str.strip()
    df_mapped['itogo'] = pd.to_numeric(df.iloc[:, 12], errors='coerce').fillna(0)
    df_mapped['nachisleno'] = df_mapped['itogo']
    
    if df_mapped.empty or 'fio' not in df_mapped.columns:
        return jsonify({'error': 'Неверный формат файла или отсутствуют обязательные колонки'}), 400
    
    df_mapped = df_mapped.dropna(subset=['fio'])
    df_mapped['fio'] = df_mapped['fio'].str.strip()
    df_mapped = df_mapped[df_mapped['fio'] != 'nan']
    df_mapped = df_mapped[df_mapped['fio'] != '']
    
    if df_mapped.empty:
        return jsonify({'error': 'Нет валидных данных для импорта'}), 400
    
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    
    for idx, row in df_mapped.iterrows():
        try:
            data = row.get('data')
            if pd.isna(data):
                skipped += 1
                continue
            
            if isinstance(data, datetime):
                data_str = data.strftime('%Y-%m-%d')
            else:
                data_str = str(data)
            
            fio = str(row.get('fio', '')).strip()
            snils = str(row.get('snils', '')).strip() if pd.notna(row.get('snils')) else None
            sp_nsp = str(row.get('sp_nsp', '')).strip() if pd.notna(row.get('sp_nsp')) else None
            podrazdelenie = str(row.get('podrazdelenie', '')).strip() if pd.notna(row.get('podrazdelenie')) else None
            otdel = str(row.get('otdel', '')).strip() if pd.notna(row.get('otdel')) else None
            dolzhnost = str(row.get('dolzhnost', '')).strip() if pd.notna(row.get('dolzhnost')) else None
            rukovoditel = str(row.get('rukovoditel', '')).strip() if pd.notna(row.get('rukovoditel')) else None
            status_field = str(row.get('status_field', '')).strip() if pd.notna(row.get('status_field')) else None
            chasy = float(row.get('chasy', 0)) if pd.notna(row.get('chasy')) else 0.0
            stavka_oklad = str(row.get('stavka_oklad', '')).strip() if pd.notna(row.get('stavka_oklad')) else None
            stavka = str(row.get('stavka', '')).strip() if pd.notna(row.get('stavka')) else None
            nachisleno = float(row.get('nachisleno', 0)) if pd.notna(row.get('nachisleno')) else 0.0
            itogo = float(row.get('itogo', 0)) if pd.notna(row.get('itogo')) else 0.0
            
            if not fio or fio == 'nan':
                skipped += 1
                continue
            
            query = """
                INSERT INTO records 
                (fio, snils, sp_nsp, podrazdelenie, otdel, dolzhnost, rukovoditel, status_field, data, chasy, stavka_oklad, stavka, nachisleno, itogo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                chasy = VALUES(chasy),
                nachisleno = VALUES(nachisleno),
                itogo = VALUES(itogo),
                sp_nsp = VALUES(sp_nsp),
                rukovoditel = VALUES(rukovoditel),
                status_field = VALUES(status_field),
                stavka_oklad = VALUES(stavka_oklad),
                stavka = VALUES(stavka)
            """
            
            cursor.execute(query, (
                fio, snils, sp_nsp, podrazdelenie, otdel, dolzhnost, rukovoditel, status_field, 
                data_str, chasy, stavka_oklad, stavka, nachisleno, itogo
            ))
            inserted += 1
            
        except Exception as row_error:
            skipped += 1
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log_action(current_user.id, 'import', 'excel', {
        'filename': file.filename,
        'sheet': 'records',
        'inserted': inserted,
        'skipped': skipped
    })
    
    return jsonify({
        'success': True,
        'inserted': inserted,
        'skipped': skipped,
        'message': f'Импортировано {inserted} записей, пропущено {skipped}'
    })


def _import_headcount_limits(tmp_path, file, sheet_name):
    """Импорт штатного расписания (лимиты по должности)"""
    try:
        df = pd.read_excel(tmp_path, sheet_name=sheet_name)
        
        if df.empty:
            return jsonify({'error': 'Лист "Штатное_расписание" пустой'}), 400
        
        # Ожидаемые колонки: Подразделение | Отдел | Должность | Месяц | Год | Лимит | (опц. Загрузка)
        # Пробуем найти колонки по нескольким вариантам названий
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if 'подраз' in col_lower:
                col_map['podrazdelenie'] = col
            elif 'отдел' in col_lower and 'служба' not in col_lower:
                # пропускаем отдел — он не нужен
                pass
            elif 'должность' in col_lower:
                col_map['dolzhnost'] = col
            elif col_lower in ('месяц', 'мес', 'month'):
                col_map['month'] = col
            elif col_lower in ('год', 'year'):
                col_map['year'] = col
            elif col_lower in ('лимит', 'макс', 'max_count', 'кол-во'):
                col_map['max_count'] = col
            elif 'загр' in col_lower:
                col_map['occupancy'] = col
        
        required = ['podrazdelenie', 'dolzhnost', 'month', 'year', 'max_count']
        missing = [r for r in required if r not in col_map]
        if missing:
            return jsonify({'error': f'Не найдены колонки: {", ".join(missing)}'}), 400
        
        # Очищаем старые лимиты
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM headcount_limits')
        
        inserted = 0
        skipped = 0
        
        for idx, row in df.iterrows():
            try:
                podrazdelenie = str(row[col_map['podrazdelenie']]).strip()
                dolzhnost = str(row[col_map['dolzhnost']]).strip()
                
                if not podrazdelenie or podrazdelenie == 'nan' or not dolzhnost or dolzhnost == 'nan':
                    skipped += 1
                    continue
                
                month = int(float(row[col_map['month']]))
                year = int(float(row[col_map['year']]))
                max_count = int(float(row[col_map['max_count']]))
                occupancy = str(row[col_map.get('occupancy', '')]).strip() if col_map.get('occupancy') and pd.notna(row.get(col_map['occupancy'])) else None
                
                cursor.execute('''
                    INSERT INTO headcount_limits (podrazdelenie, dolzhnost, year, month, max_count, occupancy_hint)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE max_count=VALUES(max_count), occupancy_hint=VALUES(occupancy_hint)
                ''', (podrazdelenie, dolzhnost, year, month, max_count, occupancy))
                inserted += 1
                
            except Exception:
                skipped += 1
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        log_action(current_user.id, 'import', 'headcount_limits', {
            'filename': file.filename,
            'inserted': inserted,
            'skipped': skipped
        })
        
        return jsonify({
            'success': True,
            'inserted': inserted,
            'skipped': skipped,
            'message': f'Штатное расписание: загружено {inserted} лимитов, пропущено {skipped}'
        })
    
    except Exception as e:
        logger.error(f'Error importing headcount_limits: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/admin/import-excel', methods=['POST'])
@login_required
def import_excel():
    """Загрузка и импорт Excel файла с данными туризма (только администраторы)"""
    # Проверяем, что пользователь администратор
    if current_user.role != 'admin':
        logger.warning(f'User {current_user.username} tried to access import-excel without admin role')
        return jsonify({'error': 'Доступ запрещён. Требуется роль администратора'}), 403
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Неверный формат файла. Используйте .xlsx или .xls'}), 400
        
        sheet_name = request.form.get('sheet', 'Архив')
        
        logger.info(f'User {current_user.username} importing Excel file: {file.filename}, sheet: {sheet_name}')
        
        # Сохраняем файл во временную директорию
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Читаем Excel файл
            if sheet_name == 'Штатное_расписание':
                # Импорт штатного расписания — отдельная логика
                result = _import_headcount_limits(tmp_path, file, sheet_name)
            elif sheet_name == 'Реестр':
                df = pd.read_excel(tmp_path, sheet_name=sheet_name, header=1)
                result = _import_records(df, file, sheet_name)
            else:
                df = pd.read_excel(tmp_path, sheet_name=sheet_name)
                result = _import_records(df, file, sheet_name)
        
        finally:
            # Удаляем временный файл
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        return result
    
    except Exception as e:
        logger.error(f'Error importing Excel: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== HEADCOUNT VIOLATIONS ====================

@app.route('/api/headcount/violations')
@login_required
def api_headcount_violations():
    """Возвращает нарушения штатного расписания за период."""
    if not current_user.has_permission('data', 'view'):
        return jsonify({'error': 'У вас нет прав для просмотра данных'}), 403
    
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    group_by = request.args.get('group_by', 'dolzhnost')  # 'none', 'otdel', 'dolzhnost'
    pod = request.args.get('pod')
    otdels = request.args.getlist('otdel')
    otdels = [o for o in otdels if o]
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 1. Получаем фактические данные за период
        conditions = ["data >= %s", "data <= %s"]
        params = [date_from, date_to]
        
        if pod:
            conditions.append("podrazdelenie = %s")
            params.append(pod)
        if otdels:
            placeholders = ','.join(['%s'] * len(otdels))
            conditions.append(f"otdel IN ({placeholders})")
            params.extend(otdels)
        
        # Применяем ограничения прав пользователя
        conditions, params = _apply_permission_filters(conditions, params)
        
        where_clause = 'WHERE ' + ' AND '.join(conditions)
        
        fact_q = f"""
            SELECT podrazdelenie, dolzhnost, DATE(data) AS fact_date,
                   COUNT(DISTINCT fio) AS fact_count,
                   GROUP_CONCAT(DISTINCT otdel SEPARATOR ', ') AS otdels
            FROM records
            {where_clause}
            GROUP BY podrazdelenie, dolzhnost, DATE(data)
        """
        
        df_fact = pd.read_sql(fact_q, conn, params=params)
        
        if df_fact.empty:
            cursor.close()
            conn.close()
            return jsonify({'violations': [], 'total_violations': 0, 'total_excess': 0})
        
        # 2. Группируем нарушения — всегда по (podrazdelenie, dolzhnost)
        violations_map = {}
        total_excess = 0
        
        for _, row in df_fact.iterrows():
            pod_val = row['podrazdelenie']
            dolzhnost = row['dolzhnost']
            otdel_val = row.get('otdels', '') or '—'
            fact_date = row['fact_date']
            fact_count = row['fact_count']
            
            year = fact_date.year
            month = fact_date.month
            
            # Ищем лимит по должности (без учёта отдела)
            cursor.execute(
                'SELECT max_count FROM headcount_limits WHERE podrazdelenie = %s AND dolzhnost = %s AND year = %s AND month = %s',
                (pod_val, dolzhnost, year, month)
            )
            limit_row = cursor.fetchone()
            
            if not limit_row:
                continue
            
            limit_count = limit_row['max_count']
            
            if fact_count > limit_count:
                excess = fact_count - limit_count
                total_excess += excess
                
                # Ключ ВСЕГДА по (podrazdelenie, dolzhnost) — без отдела!
                # Это гарантирует одну запись на связку "подразделение + должность"
                key = (pod_val, dolzhnost)
                date_str = str(fact_date)
                
                if key not in violations_map:
                    violations_map[key] = {
                        'podrazdelenie': pod_val,
                        'dolzhnost': dolzhnost,
                        'otdels': otdel_val,  # Сохраняем для группировки по отделам
                        'limit': limit_count,
                        'max_fact': fact_count,
                        'total_excess': 0,
                        'daily': {}  # Словарь по дате — исключает дубликаты
                    }
                
                v = violations_map[key]
                v['total_excess'] += excess
                if fact_count > v['max_fact']:
                    v['max_fact'] = fact_count
                
                # Сохраняем детальную информацию по дню (перезаписываем если дата уже есть)
                v['daily'][date_str] = {
                    'date': date_str,
                    'fact': fact_count,
                    'excess': excess
                }
        
        # Преобразуем в список
        violations = []
        for key, v in violations_map.items():
            # Конвертируем словарь daily в отсортированный список
            daily_list = sorted(v['daily'].values(), key=lambda x: x['date'])
            violations.append({
                'podrazdelenie': v['podrazdelenie'],
                'otdels': v['otdels'],
                'dolzhnost': v['dolzhnost'],
                'limit': v['limit'],
                'max_fact': v['max_fact'],
                'excess': v['total_excess'],
                'date_count': len(daily_list),
                'daily': daily_list
            })
        
        # Сортируем по количеству нарушений (убывание)
        violations.sort(key=lambda x: x['date_count'], reverse=True)
        
        # Если group_by = 'otdel', группируем по отделам (двухуровневая структура)
        if group_by == 'otdel':
            grouped = {}
            for v in violations:
                # otdels может быть "Смена_1, Смена_2" — разбиваем
                otdel_list = [o.strip() for o in v['otdels'].split(',') if o.strip()]
                if not otdel_list:
                    otdel_list = ['—']
                
                for otdel_name in otdel_list:
                    # Ключ включает podrazdelenie, чтобы не смешивать подразделения
                    otdel_key = (v['podrazdelenie'], otdel_name)
                    if otdel_key not in grouped:
                        grouped[otdel_key] = {
                            'podrazdelenie': v['podrazdelenie'],
                            'otdel': otdel_name,
                            'dolzhnost': '',
                            'limit': 0,
                            'max_fact': 0,
                            'excess': 0,
                            'date_count': 0,
                            'daily': [],
                            'children': []
                        }
                    # Не добавляем дубликат, если должность уже есть в отделе
                    existing = next((c for c in grouped[otdel_key]['children'] if c['dolzhnost'] == v['dolzhnost']), None)
                    if not existing:
                        grouped[otdel_key]['children'].append(v)
                        grouped[otdel_key]['excess'] += v['excess']
                        grouped[otdel_key]['date_count'] += v['date_count']
            
            # Сортируем дочерние элементы
            for otdel_key in grouped:
                grouped[otdel_key]['children'].sort(key=lambda x: x['date_count'], reverse=True)
            
            violations = list(grouped.values())
        
        # Записываем нарушения в историю
        if violations:
            for v in violations:
                # Для двухуровневой структуры (otdel) — пишем историю по детям
                items = v.get('children', [v]) if not v['daily'] else [v]
                for item in items:
                    for d in item['daily']:
                        cursor.execute('''
                            INSERT IGNORE INTO violation_history 
                            (podrazdelenie, dolzhnost, date, year, month, limit_count, fact_count, excess)
                            SELECT %s, %s, %s, %s, %s, %s, %s, %s
                        ''', (
                            item['podrazdelenie'], item['dolzhnost'], d['date'],
                            datetime.strptime(d['date'], '%Y-%m-%d').year,
                            datetime.strptime(d['date'], '%Y-%m-%d').month,
                            item['limit'], d['fact'], d['excess']
                        ))
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'violations': violations,
            'total_violations': sum(v['date_count'] for v in violations),
            'total_excess': total_excess
        })
    
    except Exception as e:
        logger.error(f'API Headcount Violations Error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/headcount/history')
@login_required
def api_headcount_history():
    """Возвращает историю нарушений за месяц."""
    if not current_user.has_permission('data', 'view'):
        return jsonify({'error': 'У вас нет прав для просмотра данных'}), 403
    
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    pod = request.args.get('pod')
    
    if not year or not month:
        return jsonify({'error': 'Укажите год и месяц'}), 400
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        conditions = ["year = %s", "month = %s"]
        params = [year, month]
        
        if pod:
            conditions.append("podrazdelenie = %s")
            params.append(pod)
        
        where_clause = 'WHERE ' + ' AND '.join(conditions)
        
        cursor.execute(f'''
            SELECT vh.*, DATE(vh.date) AS date_formatted
            FROM violation_history vh
            {where_clause}
            ORDER BY vh.date DESC
        ''', tuple(params))
        
        history = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for h in history:
            h['date'] = str(h['date_formatted'])
        
        return jsonify({
            'year': year,
            'month': month,
            'history': history,
            'total_days': len(set(h['date'] for h in history))
        })
    
    except Exception as e:
        logger.error(f'API Headcount History Error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/headcount/employees')
@login_required
def api_headcount_employees():
    """Возвращает список сотрудников за конкретную дату по подразделению и должности."""
    if not current_user.has_permission('data', 'view'):
        return jsonify({'error': 'У вас нет прав для просмотра данных'}), 403
    
    date = request.args.get('date')
    pod = request.args.get('pod')
    dolzhnost = request.args.get('dolzhnost')
    
    if not date or not pod or not dolzhnost:
        return jsonify({'error': 'Укажите date, pod, dolzhnost'}), 400
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        conditions = ['data = %s', 'podrazdelenie = %s', 'dolzhnost = %s']
        params = [date, pod, dolzhnost]
        
        conditions, params = _apply_permission_filters(conditions, params)
        
        where_clause = 'WHERE ' + ' AND '.join(conditions)
        
        cursor.execute(f'''
            SELECT DISTINCT fio, status_field, otdel
            FROM records
            {where_clause}
            ORDER BY fio
        ''', tuple(params))
        
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'employees': employees, 'count': len(employees)})
    
    except Exception as e:
        logger.error(f'API Headcount Employees Error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/headcount/limits')
@login_required
def api_headcount_limits():
    """Возвращает все загруженные лимиты штатного расписания."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM headcount_limits ORDER BY year DESC, month DESC, podrazdelenie, dolzhnost')
        limits = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for l in limits:
            if isinstance(l.get('created_at'), datetime):
                l['created_at'] = l['created_at'].isoformat()
            if isinstance(l.get('updated_at'), datetime):
                l['updated_at'] = l['updated_at'].isoformat()
        
        return jsonify({'limits': limits})
    
    except Exception as e:
        logger.error(f'API Headcount Limits Error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/admin/clear-records', methods=['POST'])
@login_required
def clear_records():
    """Очистка всех записей из таблицы records (только администраторы)"""
    # Проверяем, что пользователь администратор
    if current_user.role != 'admin':
        logger.warning(f'User {current_user.username} tried to clear records without admin role')
        return jsonify({'error': 'Доступ запрещён. Требуется роль администратора'}), 403
    
    try:
        logger.info(f'User {current_user.username} clearing records')
        
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) as count FROM records')
        count = cursor.fetchone()['count']
        cursor.close()
        
        cursor = conn.cursor()
        cursor.execute('TRUNCATE TABLE records')
        conn.commit()
        cursor.close()
        conn.close()
        
        log_action(current_user.id, 'clear', 'records', {'deleted_count': count})
        
        return jsonify({
            'success': True,
            'message': f'Удалено {count} записей'
        })
    
    except Exception as e:
        logger.error(f'Error clearing records: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('='*60)
    print('Dashboard with Advanced RBAC Permissions System')
    print('='*60)
    print('http://localhost:5000')
    print('Login: admin, Password: admin123')
    print('='*60)
    print('Features:')
    print('  - Role-Based Access Control (RBAC)')
    print('  - Granular permissions per resource')
    print('  - Audit logging for all actions')
    print('  - Session timeout protection')
    print('  - Subdivision/Department-level access control')
    print('='*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
