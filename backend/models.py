from flask_sqlalchemy import SQLAlchemy
import uuid
from sqlalchemy.dialects.postgresql import UUID, ENUM
import datetime

db = SQLAlchemy()

# roles: user join table from the schema
class UserRole(db.Model):
    __tablename__ = 'user_roles'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), primary_key=True)
    role = db.Column(ENUM('student', 'teacher', 'administrator', name='role_name'), primary_key=True)
    granted_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.utcnow)

# user model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # define relationships
    roles = db.relationship('UserRole', backref='user', lazy=True, cascade="all, delete-orphan")
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade="all, delete-orphan")
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.username}>'

# studnet Model
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}>'

# Teacher model
class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100)) # e.g., "Professor", "Instructor"
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<Teacher {self.first_name} {self.last_name}>'
# new model down here as course, ai system etc