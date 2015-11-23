from flask import render_template, redirect, url_for, flash
from flask.ext.login import current_user
from . import teacher
from .. import db
from ..models import Permission, Lesson, Problem
from .forms import AddLessonForm, AddProblemForm
from ..decorators import permission_required
import parse

@teacher.route('/lessons', methods=['GET', 'POST'])
@permission_required(Permission.CREATE_LESSONS)
def lessons():
    form = AddLessonForm()
    if form.validate_on_submit():
        num_lessons = Lesson.query.filter_by(author_id=current_user.id).count()
        lesson = Lesson(number=num_lessons + 1,
                        name=form.name.data,
                        author_id=current_user.id)
        db.session.add(lesson)
        db.session.commit()
        return redirect(url_for('teacher.lessons'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error)
    return render_template('teacher/lessons.html', form=form, user=current_user)


@teacher.route('/edit_lesson/<int:lesson_id>', methods=['GET', 'POST'])
@permission_required(Permission.CREATE_LESSONS)
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    form = AddProblemForm()
    if form.validate_on_submit():
        num_problems = Problem.query.filter_by(lesson_id=lesson.id).count()
        parsed_equation = parse.parse_equation(form.text.data)
        parsed_equation['number'] = num_problems + 1
        parsed_equation['lesson_id'] = lesson.id
        equation = Problem(**parsed_equation)
        db.session.add(equation)
        db.session.commit()
        return redirect(url_for('teacher.edit_lesson', lesson_id=lesson_id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error)
    return render_template('teacher/edit_lesson.html', lesson=lesson, form=form)
