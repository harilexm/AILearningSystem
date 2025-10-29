import os
import uuid
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from models import (
    db, User, UserRole, Student, Teacher, Course, Module, LearningContent, 
    StudentContentProgress, AssessmentAttempt
)

# --- Application Setup ---
app = Flask(__name__)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path): load_dotenv(dotenv_path)

# --- Configurations ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY')

# --- Extensions Initialization ---
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# --- Custom Security Decorator ---
def roles_required(*roles):
    """Decorator to ensure user has at least one of the specified roles."""
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            user = User.query.get(get_jwt_identity())
            if not user:
                return jsonify({"error": "User not found"}), 404
            user_roles = {r.role for r in user.roles}
            if not user_roles.intersection(roles):
                return jsonify({"error": "Access forbidden: insufficient permissions"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# ==============================================================================
# --- CORE API ROUTES (Authentication, Profile) ---
# ==============================================================================

@app.route('/')
def home():
    return "AI-Powered Learning System Backend is running!"

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.get_json()
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
        else: return jsonify({"error": "A database error occurred."}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify(access_token=create_access_token(identity=str(user.id)))
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user = User.query.get(get_jwt_identity())
    if not user: return jsonify({"error": "User not found"}), 404
    return jsonify({"id": str(user.id), "username": user.username, "email": user.email, "roles": [r.role for r in user.roles]}), 200

# ==============================================================================
# --- ADMIN USER MANAGEMENT API ---
# ==============================================================================

@app.route('/api/admin/users', methods=['GET'])
@roles_required('administrator')
def get_all_users():
    users = User.query.all()
    output = []
    for user in users:
        user_data = {'id': str(user.id), 'username': user.username, 'email': user.email, 'roles': [r.role for r in user.roles]}
        profile = user.student_profile or user.teacher_profile
        if profile:
            user_data['first_name'] = profile.first_name
            user_data['last_name'] = profile.last_name
        output.append(user_data)
    return jsonify(output), 200

@app.route('/api/admin/users', methods=['POST'])
@roles_required('administrator')
def create_user_by_admin():
    data = request.get_json()
    role = data.get('role')
    if role not in ['teacher', 'administrator']: return jsonify({"error": "Invalid role specified."}), 400
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
@roles_required('administrator')
def delete_user(user_id):
    if str(user_id) == get_jwt_identity(): return jsonify({"error": "You cannot delete your own account."}), 403
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    return jsonify({"message": f"User '{user_to_delete.username}' has been deleted."}), 200

# ==============================================================================
# --- CURRICULUM & STUDENT VIEWING API ---
# ==============================================================================

@app.route('/api/courses', methods=['GET'])
@jwt_required()
def get_courses():
    courses = Course.query.order_by(Course.title).all()
    output = []
    for c in courses:
        teacher_name = "N/A"
        if c.teacher:
             teacher_name = f"{c.teacher.first_name} {c.teacher.last_name}"
        output.append({"id": str(c.id), "title": c.title, "description": c.description, "author": teacher_name})
    return jsonify(output)

@app.route('/api/courses/<uuid:course_id>', methods=['GET'])
@jwt_required()
def get_course_details(course_id):
    course = Course.query.get_or_404(course_id) # Corrected typo from get_or_4_4
    student = Student.query.filter_by(user_id=get_jwt_identity()).first()
    
    student_progress = {}
    if student: # Only fetch progress if the logged-in user is a student
        content_ids = [content.id for module in course.modules for content in module.learning_contents]
        if content_ids:
            progress_records = StudentContentProgress.query.filter(
                StudentContentProgress.student_id == student.id,
                StudentContentProgress.content_id.in_(content_ids)
            ).all()
            student_progress = {str(p.content_id): p.status for p in progress_records}

    course_data = {"id": str(course.id), "title": course.title, "description": course.description, "modules": []}
    for module in sorted(course.modules, key=lambda m: m.module_order):
        module_data = {"id": str(module.id), "title": module.title, "learning_contents": []}
        for content in sorted(module.learning_contents, key=lambda c: c.content_order):
            module_data["learning_contents"].append({
                "id": str(content.id), "title": content.title, "type": content.type,
                "url": content.content_url, "progress_status": student_progress.get(str(content.id), 'not_started')
            })
        course_data["modules"].append(module_data)
        
    return jsonify(course_data)

# ==============================================================================
# --- TEACHER COURSE MANAGEMENT API ---
# ==============================================================================

@app.route('/api/courses', methods=['POST'])
@roles_required('teacher', 'administrator')
def create_course():
    data = request.get_json()
    teacher = Teacher.query.filter_by(user_id=get_jwt_identity()).first()
    new_course = Course(title=data['title'], description=data.get('description', ''), created_by_teacher_id=teacher.id if teacher else None)
    db.session.add(new_course)
    db.session.commit()
    return jsonify({"message": "Course created successfully", "course_id": str(new_course.id)}), 201

@app.route('/api/courses/<uuid:course_id>/modules', methods=['POST'])
@roles_required('teacher', 'administrator')
def create_module(course_id):
    course = Course.query.get_or_404(course_id)
    data = request.get_json()
    new_module = Module(course_id=course.id, title=data['title'], description=data.get('description', ''), module_order=data['order'])
    db.session.add(new_module)
    db.session.commit()
    return jsonify({"message": "Module added successfully", "module_id": str(new_module.id)}), 201

@app.route('/api/modules/<uuid:module_id>/content', methods=['POST'])
@roles_required('teacher', 'administrator')
def create_learning_content(module_id):
    module = Module.query.get_or_404(module_id)
    data = request.get_json()
    new_content = LearningContent(
        module_id=module.id, title=data['title'], type=data['type'], content_order=data['order'],
        content_url=data.get('url'), content_body=data.get('body'), content_metadata=data.get('metadata')
    )
    db.session.add(new_content)
    db.session.commit()
    return jsonify({"message": "Content added successfully"}), 201

# ==============================================================================
# --- QUIZZES, PROGRESS, AND ANALYTICS API ---
# ==============================================================================

@app.route('/api/progress/<uuid:content_id>/complete', methods=['POST'])
@jwt_required()
def mark_content_complete(content_id):
    student = Student.query.filter_by(user_id=get_jwt_identity()).first()
    if not student: return jsonify({"error": "Student profile not found."}), 404
    
    progress = StudentContentProgress.query.filter_by(student_id=student.id, content_id=content_id).first()
    if progress:
        progress.status = 'completed'
        progress.completed_at = datetime.datetime.utcnow()
    else:
        progress = StudentContentProgress(student_id=student.id, content_id=content_id, status='completed', completed_at=datetime.datetime.utcnow())
        db.session.add(progress)
    db.session.commit()
    return jsonify({"message": "Progress updated successfully", "status": "completed"})

@app.route('/api/quizzes/<uuid:content_id>', methods=['GET'])
@jwt_required()
def get_quiz_questions(content_id):
    quiz = LearningContent.query.get_or_404(content_id)
    if quiz.type != 'quiz' or not quiz.content_metadata: return jsonify({"error": "Not a valid quiz"}), 404
    
    questions = [{"id": i, "question": q.get("question"), "options": q.get("options")} for i, q in enumerate(quiz.content_metadata.get('questions', []))]
    return jsonify({"quiz_title": quiz.title, "questions": questions})

@app.route('/api/quizzes/<uuid:content_id>/submit', methods=['POST'])
@jwt_required()
def submit_quiz(content_id):
    quiz = LearningContent.query.get_or_404(content_id)
    student = Student.query.filter_by(user_id=get_jwt_identity()).first()
    if not student: return jsonify({"error": "Student profile not found"}), 404
    
    student_answers = request.get_json().get('answers', [])
    correct_answers = quiz.content_metadata.get('questions', [])
    score = 0
    for s_ans in student_answers:
        q_id = s_ans.get('questionId')
        if 0 <= q_id < len(correct_answers) and correct_answers[q_id].get('answer') == s_ans.get('answer'):
            score += 1

    attempt = AssessmentAttempt(content_id=content_id, student_id=student.id, score=score, max_score=len(correct_answers), answers={'submitted': student_answers})
    db.session.add(attempt)
    db.session.commit()
    
    return jsonify({
        "message": "Quiz submitted!", "score": score, "max_score": len(correct_answers),
        "correct_answers": [q.get('answer') for q in correct_answers]
    })

@app.route('/api/courses/<uuid:course_id>/progress', methods=['GET'])
@roles_required('teacher', 'administrator')
def get_course_progress(course_id):
    course = Course.query.get_or_404(course_id)
    content_ids = [c.id for module in course.modules for c in module.learning_contents]
    if not content_ids: return jsonify([])

    progress_records = db.session.query(
        Student.id, Student.first_name, Student.last_name, db.func.count(StudentContentProgress.id)
    ).join(StudentContentProgress).filter(
        StudentContentProgress.content_id.in_(content_ids),
        StudentContentProgress.status == 'completed'
    ).group_by(Student.id).all()
    
    output = [{
        "student_id": str(student_id), "student_name": f"{first} {last}", "completed_count": count,
        "total_items": len(content_ids), "percentage": round((count / len(content_ids)) * 100, 2)
    } for student_id, first, last, count in progress_records]
    
    return jsonify(sorted(output, key=lambda x: x['student_name']))

# ==============================================================================
# --- Main Application Runner ---
# ==============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)