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
from models import db, User, UserRole, Student, Teacher, Course, Module, LearningContent, StudentContentProgress, AssessmentAttempt

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

@app.route('/api/quizzes/<uuid:content_id>', methods=['GET'])
@jwt_required()
def get_quiz_questions(content_id):
    """
    Fetches a quiz for a student, returning only the questions, not the answers.
    """
    content = LearningContent.query.get_or_404(content_id)
    if content.type != 'quiz' or not content.quiz_data:
        return jsonify({"error": "This content is not a valid quiz."}), 404

    # SECURITY: Sanitize the questions, removing the correct answer index to prevent cheating.
    sanitized_questions = []
    for q in content.quiz_data.get('questions', []):
        sanitized_questions.append({
            "id": q.get("id"),
            "text": q.get("text"),
            "options": q.get("options")
        })

    return jsonify({
        "quiz_id": str(content.id),
        "title": content.title,
        "questions": sanitized_questions
    })

@app.route('/api/quizzes/<uuid:content_id>/submit', methods=['POST'])
@jwt_required()
def submit_quiz(content_id):
    """
    Receives student answers, grades them, saves the attempt, and returns results.
    """
    content = LearningContent.query.get_or_404(content_id)
    if content.type != 'quiz' or not content.quiz_data:
        return jsonify({"error": "This content is not a valid quiz."}), 404

    # Get the student profile associated with the logged-in user
    current_user_id = get_jwt_identity()
    student = Student.query.filter_by(user_id=current_user_id).first()
    if not student:
        return jsonify({"error": "A student profile is required to submit a quiz."}), 403

    student_answers = request.get_json().get('answers', {}) # e.g., {"q1": 1, "q2": 2}
    correct_answers = {q['id']: q['correct_answer_index'] for q in content.quiz_data['questions']}
    
    # Grade the submission
    score = 0
    total_questions = len(correct_answers)
    for question_id, correct_index in correct_answers.items():
        if question_id in student_answers and int(student_answers[question_id]) == correct_index:
            score += 1
    
    percentage = round((score / total_questions) * 100, 2) if total_questions > 0 else 0

    # Save the full attempt to the database for record-keeping
    new_attempt = AssessmentAttempt(
        content_id=content_id,
        student_id=student.id,
        score=percentage,
        answers=student_answers  # Store exactly what the student submitted
    )
    db.session.add(new_attempt)
    db.session.commit()

    # Return the results to the student for immediate feedback
    return jsonify({
        "message": "Quiz submitted successfully!",
        "score": percentage,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "student_answers": student_answers
    })


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

# backend/app.py
# --- REPLACE the old get_course_details function with this one ---

@app.route('/api/courses/<uuid:course_id>', methods=['GET'])
@jwt_required()
def get_course_details(course_id):
    """Returns a single course with its structure AND the current student's progress."""
    course = Course.query.get_or_404(course_id)
    current_user_id = get_jwt_identity()
    student = Student.query.filter_by(user_id=current_user_id).first()
    
    # Efficiently fetch all progress for this student in this course
    student_progress = {}
    if student:
        content_ids = [content.id for module in course.modules for content in module.learning_contents]
        progress_records = StudentContentProgress.query.filter(
            StudentContentProgress.student_id == student.id,
            StudentContentProgress.content_id.in_(content_ids)
        ).all()
        student_progress = {str(p.content_id): p.status for p in progress_records}

    # Build the response payload
    course_data = {"id": str(course.id), "title": course.title, "description": course.description, "modules": []}
    sorted_modules = sorted(course.modules, key=lambda m: m.module_order)
    
    for module in sorted_modules:
        module_data = {"id": str(module.id), "title": module.title, "learning_contents": []}
        sorted_content = sorted(module.learning_contents, key=lambda c: c.content_order)
        for content in sorted_content:
            content_data = {
                "id": str(content.id),
                "title": content.title,
                "type": content.type,
                "url": content.content_url,
                # Add the student's progress status to the response
                "progress_status": student_progress.get(str(content.id), 'not_started')
            }
            module_data["learning_contents"].append(content_data)
        course_data["modules"].append(module_data)
        
    return jsonify(course_data)

@app.route('/api/courses/<uuid:course_id>/modules', methods=['POST'])
@roles_required('teacher', 'administrator')
def create_module(course_id):
    """Creates a new module and adds it to a course."""
    course = Course.query.get_or_404(course_id)
    data = request.get_json()
    if not data or not data.get('title') or 'order' not in data:
        return jsonify({"error": "Title and order are required"}), 400
        
    new_module = Module(
        course_id=course.id,
        title=data['title'],
        description=data.get('description', ''),
        module_order=data['order']
    )
    db.session.add(new_module)
    db.session.commit()
    return jsonify({"message": "Module added successfully", "module_id": str(new_module.id)}), 201

@app.route('/api/modules/<uuid:module_id>/content', methods=['POST'])
@roles_required('teacher', 'administrator')
def create_learning_content(module_id):
    """Creates new learning content and adds it to a module."""
    module = Module.query.get_or_404(module_id)
    data = request.get_json()
    required = ['title', 'type', 'order']
    if not all(field in data for field in required):
        return jsonify({"error": "Title, type, and order are required"}), 400

    new_content = LearningContent(
        module_id=module.id,
        title=data['title'],
        type=data['type'],
        content_order=data['order'],
        content_url=data.get('url'),
        content_body=data.get('body')
    )
    db.session.add(new_content)
    db.session.commit()
    return jsonify({"message": "Learning content added successfully", "content_id": str(new_content.id)}), 201

# backend/app.py
# --- ADD THIS NEW ROUTE ---

@app.route('/api/progress/<uuid:content_id>/complete', methods=['POST'])
@jwt_required()
def mark_content_complete(content_id):
    """Marks a piece of learning content as complete for the logged-in student."""
    current_user_id = get_jwt_identity()
    student = Student.query.filter_by(user_id=current_user_id).first()
    
    if not student:
        return jsonify({"error": "Student profile not found for this user."}), 404
        
    # Find if a progress record already exists
    progress_record = StudentContentProgress.query.filter_by(
        student_id=student.id,
        content_id=content_id
    ).first()
    
    if progress_record:
        # Update existing record
        progress_record.status = 'completed'
        progress_record.completed_at = datetime.datetime.utcnow()
        progress_record.last_accessed_at = datetime.datetime.utcnow()
    else:
        # Create a new record
        progress_record = StudentContentProgress(
            student_id=student.id,
            content_id=content_id,
            status='completed',
            completed_at=datetime.datetime.utcnow()
        )
        db.session.add(progress_record)
        
    db.session.commit()
    return jsonify({"message": "Progress updated successfully", "status": "completed"})

# --- NEW TEACHER ANALYTICS API ---

@app.route('/api/courses/<uuid:course_id>/progress', methods=['GET'])
@roles_required('teacher', 'administrator')
def get_course_progress(course_id):
    """
    For a given course, calculates the progress of every student who has started it.
    Accessible by teachers and admins.
    """
    course = Course.query.get_or_404(course_id)
    
    # 1. Get all content IDs for this course to define the scope
    course_content_ids = db.session.query(LearningContent.id).join(Module).filter(Module.course_id == course.id).all()
    # Flatten the list of tuples into a simple list of IDs
    content_ids = [c_id[0] for c_id in course_content_ids]
    
    if not content_ids:
        return jsonify([]) # Return empty list if course has no content

    total_items = len(content_ids)

    # 2. Find all progress records for this course's content
    progress_records = StudentContentProgress.query.filter(
        StudentContentProgress.content_id.in_(content_ids),
        StudentContentProgress.status == 'completed'
    ).all()

    # 3. Aggregate progress by student
    student_progress = {}
    for record in progress_records:
        student_id = record.student_id
        if student_id not in student_progress:
            # Initialize student if not seen before
            student_profile = Student.query.get(student_id)
            student_progress[student_id] = {
                "student_id": str(student_id),
                "student_name": f"{student_profile.first_name} {student_profile.last_name}",
                "completed_count": 0
            }
        student_progress[student_id]["completed_count"] += 1

    # 4. Format the final output with percentages
    output = []
    for student_id, data in student_progress.items():
        data['total_items'] = total_items
        data['percentage'] = round((data['completed_count'] / total_items) * 100, 2)
        output.append(data)
        
    # Sort by student name for a consistent view
    output.sort(key=lambda x: x['student_name'])
    
    return jsonify(output)

if __name__ == '__main__':
    app.run(debug=True, port=5000)