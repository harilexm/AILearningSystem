import os
import uuid
from functools import wraps
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from models import db, User, UserRole, Student, Teacher, Course, Module, LearningContent

# Application Setup
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found.")
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

#  Database Configuration
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise RuntimeError("FATAL ERROR: DATABASE_URL is not set.")
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT Configuration
jwt_secret = os.environ.get('JWT_SECRET_KEY')
if not jwt_secret:
    raise RuntimeError("FATAL ERROR: JWT_SECRET_KEY is not set.")
app.config["JWT_SECRET_KEY"] = jwt_secret
jwt = JWTManager(app)

# Initialize Extensions
db.init_app(app)
bcrypt = Bcrypt(app)

# CUSTOM DECORATOR: Admin-Only Routes
def admin_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user_id = get_jwt_identity()
            # Find users roles from database
            user_roles = UserRole.query.filter_by(user_id=current_user_id).all()
            roles = [role.role for role in user_roles]
            # error handling
            if 'administrator' not in roles:
                return jsonify({"error": "Admins only!"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# This decorator is more flexible for routes that teachers OR admins can access.
def roles_required(*roles):
    """Decorator to ensure user has at least one of the specified roles."""
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            user_roles = {r.role for r in user.roles}
            
            if not user_roles.intersection(roles):
                return jsonify({"error": "Access forbidden: insufficient permissions"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# API Routes
@app.route('/')
def home():
    return "AI-Powered Learning System Backend is running!"

# AUTHENTICATION ROUTES
@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.get_json()
    required_fields = ['username', 'email', 'password', 'firstName', 'lastName']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"error": "All fields are required and cannot be empty"}), 400

    try:
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(username=data['username'], email=data['email'], password_hash=hashed_password)
        db.session.add(new_user)
        db.session.flush()
        new_student = Student(user_id=new_user.id, first_name=data['firstName'], last_name=data['lastName'])
        db.session.add(new_student)
        new_role = UserRole(user_id=new_user.id, role='student')
        db.session.add(new_role)
        db.session.commit()
        return jsonify({"message": f"User '{new_user.username}' registered successfully!"}), 201
    except IntegrityError as e:
        db.session.rollback()
        if 'users_username_key' in str(e.orig): return jsonify({"error": "Username already exists"}), 409
        elif 'users_email_key' in str(e.orig): return jsonify({"error": "Email already exists"}), 409
        else: return jsonify({"error": "A database error occurred. Please try again."}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An unexpected server error occurred."}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token)
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user_id_str = get_jwt_identity()
    current_user_id = uuid.UUID(current_user_id_str)
    user = User.query.get(current_user_id)
    if not user: return jsonify({"error": "User not found"}), 404
    return jsonify({"id": str(user.id), "username": user.username, "email": user.email, "roles": [r.role for r in user.roles]}), 200

# ADMIN USER MANAGEMENT API
@app.route('/api/admin/users', methods=['GET'])
@admin_required()
def get_all_users():
    "Admin only: Returns a list of all users."
    users = User.query.all()
    output = []
    for user in users:
        user_data = {'id': str(user.id), 'username': user.username, 'email': user.email, 'roles': [r.role for r in user.roles]}
        if user.student_profile:
            user_data['first_name'] = user.student_profile.first_name
            user_data['last_name'] = user.student_profile.last_name
        elif user.teacher_profile:
            user_data['first_name'] = user.teacher_profile.first_name
            user_data['last_name'] = user.teacher_profile.last_name
        output.append(user_data)
    return jsonify(output), 200

@app.route('/api/admin/users', methods=['POST'])
@admin_required()
def create_user_by_admin():
    "Admin only: Creates a new user (teacher or admin)."
    data = request.get_json()
    required_fields = ['firstName', 'lastName', 'username', 'email', 'password', 'role']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    role = data['role']
    if role not in ['teacher', 'administrator']:
        return jsonify({"error": "Invalid role specified."}), 400
    try:
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(username=data['username'], email=data['email'], password_hash=hashed_password)
        db.session.add(new_user)
        db.session.flush()
        new_profile = Teacher(user_id=new_user.id, first_name=data['firstName'], last_name=data['lastName'], title=role.capitalize())
        db.session.add(new_profile)
        new_role = UserRole(user_id=new_user.id, role=role)
        db.session.add(new_role)
        db.session.commit()
        return jsonify({"message": f"{role.capitalize()} '{new_user.username}' created successfully."}), 201
    except IntegrityError as e:
        db.session.rollback()
        if 'users_username_key' in str(e.orig): return jsonify({"error": "Username already exists"}), 409
        if 'users_email_key' in str(e.orig): return jsonify({"error": "Email already exists"}), 409
        return jsonify({"error": "Database error"}), 500

@app.route('/api/admin/users/<uuid:user_id>', methods=['DELETE'])
@admin_required()
def delete_user(user_id):
    "Admin only. Deletes a user by their ID."
    current_user_id = get_jwt_identity()
    if str(user_id) == current_user_id:
        return jsonify({"error": "You cannot delete your own account."}), 403
    user_to_delete = User.query.get(user_id)
    if not user_to_delete:
        return jsonify({"error": "User not found."}), 404
    db.session.delete(user_to_delete)
    db.session.commit()
    return jsonify({"message": f"User '{user_to_delete.username}' has been deleted."}), 200

@app.route('/api/courses', methods=['POST'])
@roles_required('teacher', 'administrator')
def create_course():
    """Creates a new course. Accessible by teachers and admins."""
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({"error": "Title is required"}), 400
    
    current_user_id = get_jwt_identity()
    # Find the teacher profile associated with the logged-in user
    teacher = Teacher.query.filter_by(user_id=current_user_id).first()
    
    new_course = Course(
        title=data['title'],
        description=data.get('description', ''),
        created_by_teacher_id=teacher.id if teacher else None
    )
    db.session.add(new_course)
    db.session.commit()
    return jsonify({"message": "Course created successfully", "course_id": str(new_course.id)}), 201

@app.route('/api/courses', methods=['GET'])
@jwt_required()
def get_courses():
    """Returns a list of all available courses. Accessible by any logged-in user."""
    courses = Course.query.order_by(Course.title).all()
    # Include teacher's name for display purposes
    output = []
    for c in courses:
        teacher_name = "N/A"
        if c.created_by_teacher_id and c.teacher:
             teacher_name = f"{c.teacher.first_name} {c.teacher.last_name}"
        output.append({"id": str(c.id), "title": c.title, "description": c.description, "author": teacher_name})
        
    return jsonify(output)

if __name__ == '__main__':
    app.run(debug=True, port=5000)