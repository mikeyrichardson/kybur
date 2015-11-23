from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request
from flask.ext.login import UserMixin, AnonymousUserMixin
from . import db, login_manager


class Permission:
    CREATE_LESSONS = 0x01
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': 0x0,
            'Teacher': Permission.CREATE_LESSONS,
            'Administrator': 0xff
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class Problem(db.Model):
    __tablename__ = 'problems'
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    number = db.Column(db.Integer)
    text = db.Column(db.String(128))
    left_coefficient = db.Column(db.Integer)
    left_constant = db.Column(db.Integer)
    right_coefficient = db.Column(db.Integer)
    right_constant = db.Column(db.Integer)
    solution_numerator = db.Column(db.Integer)
    solution_denominator = db.Column(db.Integer)
    left_side_numerator = db.Column(db.Integer)
    left_side_denominator = db.Column(db.Integer)


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(128), default='')
    number = db.Column(db.Integer)
    problems = db.relationship('Problem', foreign_keys=[Problem.lesson_id],
                               backref='lesson', lazy='dynamic')


class AnswerSubmission(db.Model):
    __tablename__ = 'answer_submissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), index=True)
    variable_value = db.Column(db.String(32), default='')
    left_side_value = db.Column(db.String(32), default='')
    right_side_value = db.Column(db.String(32), default='')
    is_correct = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class TeachingRelationship(db.Model):
    __tablename__ = 'teaching_relationships'
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    last_name = db.Column(db.String(64))
    first_name = db.Column(db.String(64))
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    students = db.relationship('TeachingRelationship',
                               foreign_keys=[TeachingRelationship.teacher_id],
                               backref=db.backref('teacher', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    teachers = db.relationship('TeachingRelationship',
                                foreign_keys=[TeachingRelationship.student_id],
                                backref=db.backref('student', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    answer_submissions = db.relationship('AnswerSubmission',
                                         foreign_keys=[AnswerSubmission.user_id],
                                         backref=db.backref('student', lazy='joined'),
                                         lazy='dynamic',
                                         cascade='all')
    lessons = db.relationship('Lesson',
                              foreign_keys=[Lesson.author_id],
                              backref=db.backref('author', lazy='joined'),
                              lazy='dynamic',
                              cascade='all, delete-orphan')

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     last_name=forgery_py.name.last_name(),
                     first_name=forgery_py.name.first_name(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()


    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            self.role = Role.query.filter_by(name='User').first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    @property
    def full_name(self):
        return '{first} {last}'.format(first=self.first_name, last=self.last_name)

    @full_name.setter
    def full_name(self, full_name):
        raise AttributeError('full_name is a read-only attribute')


    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def add_student(self, user):
        if not self.is_teacher_of(user):
            t = TeachingRelationship(teacher=self, student=user)
            db.session.add(t)

    def add_teacher(self, user):
        if not self.is_student_of(user):
            t = TeachingRelationship(teacher=user, student=self)
            db.session.add(t)

    def remove_teacher(self, user):
        t = self.teachers.filter_by(teacher_id=user.id).first()
        if t:
            db.session.delete(t)

    def remove_student(self, user):
        t = self.students.filter_by(student_id=user.id).first()
        if t:
            db.session.delete(t)

    def is_student_of(self, user):
        return self.teachers.filter_by(
            teacher_id=user.id).first() is not None

    def is_teacher_of(self, user):
        return self.students.filter_by(
            student_id=user.id).first() is not None

    def __repr__(self):
        return '<User %r>' % self.full_name


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
