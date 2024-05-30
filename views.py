from flask import Blueprint, request, redirect, url_for, session, render_template, g, jsonify, flash, send_from_directory
views = Blueprint('views', __name__)

from app import app
from forms import *
import db_functions as db

import os
from pathlib import Path

user_views = {
    'admin': [
        {'name': 'Overview', 'link': '.dashboard_admin'},
        {'name': 'Instructors', 'link': '.instructors'},
        {'name': 'Students', 'link': '.admin_students'},
        {'name': 'Courses', 'link': '.courses'},
        # {'name': 'Message', 'link': '.message'},
        {'name': 'Manage Users', 'link': '.users'},
        {'name': 'Manage Account', 'link': '.account'},
    ],
    'instructor': [
        # {'name': 'Overview', 'link': '.dashboard_instructor'},
        {'name': 'Students', 'link': '.instructor_students'},
        # {'name': 'Message', 'link': '.message'},
        {'name': 'Manage Account', 'link': '.account'},
    ],
    'student': [
        {'name': 'Enrollment', 'link': '.enrollment'},
        {'name': 'Subjects', 'link': '.subjects'},
        # {'name': 'Message', 'link': '.message'},
        {'name': 'Manage Account', 'link': '.account'},
    ],
}

@views.before_request
def verify_permissions():
    g.user = None
    if 'user' in session:
        g.user = session['user']
    else:
        return redirect('/login')

@views.route('/home')
def index():
    views = user_views[g.user]
    return redirect(url_for(views[0]['link']))

@views.route('/admin_dashboard')
def dashboard_admin():
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    student_count = db.get_student_count()
    return render_template('dashboard-admin.html', page="Dashboard", student_count=student_count, views=views)

@views.route('/instructor_dashboard')
def dashboard_instructor():
    if g.user != 'instructor':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    return render_template('dashboard-instructor.html', page="Dashboard", views=views)

@views.route('/instructors')
def instructors():
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    instructors = db.get_instructors()
    data = { 'instructors': [] }
    for i in instructors:
        info = {
            'name': f"{i['l_name'].title()}, {i['f_name']} {i['m_name'][0]}.",
            'username': i['username'],
            'id': i['id'],
            'uid': i['user'],
        }
        data['instructors'].append(info)
    return render_template('instructors.html', page="Instructors", data=data, views=views)
        
@views.route('/admin_students')
def admin_students():
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    students = db.get_students()
    data = { 'students': [] }
    for s in students:
        info = {
            'name': f"{s['l_name'].title()}, {s['f_name']} {s['m_name'][0]}.",
            'username': s['username'],
            'id': s['id'],
            'uid': s['user'],
            'progress': s['progress'],
            'receipt': s['receipt_filepath'],
            'doc': s['document_filepath']
        }
        data['students'].append(info)
    return render_template('students-admin.html', page="Students", data=data, views=views)

@views.route('/instructor_students')
def instructor_students():
    if g.user != 'instructor':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    enrollments = db.get_instructor_enrollments(db.uid_to_pk(session.get('id'), 'instructor'))
    data = {
        'instructor_id': db.uid_to_pk(session.get('id'), 'instructor'),
        'enrollments': []
    }
    for e in enrollments:
        data['enrollments'].append({
            'student_name': f"{e['student']['l_name'].title()}, {e['student']['f_name']} {e['student']['m_name'][0]}.",
            'course': f"{e['course']['code']}: {e['course']['title']}",
            'status': e['status'],
            'enrollment_id': e['id']
        })
    return render_template('students-instructor.html', page="Students", data=data, views=views)

@views.route('/instructors/<instructor_id>/enrollments/<enrollment_id>/accept', methods=["GET", "POST"])
def accept_enrollment(instructor_id, enrollment_id):
    if g.user != 'instructor':
        return redirect(url_for('.unauthorized'))
    form = StatusConfirmationForm()
    e = db.get_instructor_enrollment(instructor_id, enrollment_id)
    data = {
        'student_name': f"{e['student']['l_name'].title()}, {e['student']['f_name']} {e['student']['m_name'][0]}.",
        'course': f"{e['course']['code']}: {e['course']['title']}",
        'instructor_id': instructor_id,
        'enrollment_id': enrollment_id
    }
    if form.validate_on_submit():
        message = db.accept_enrollment(enrollment_id)
        return f"""
        <script>
            alert("{message}");
            window.opener.location.reload();
            window.close();
        </script>
        """
    return render_template('accept-enrollment.html', data=data, form=form)

@views.route('/instructors/<instructor_id>/enrollments/<enrollment_id>/requirements', methods=["GET", "POST"])
def view_instructor_requirements(instructor_id, enrollment_id):
    if g.user != 'instructor':
        return redirect(url_for('.unauthorized'))
    data = db.get_requirements(enrollment_id)
    enrollment = db.get_enrollment(enrollment_id)
    course = db.get_course(enrollment['course'])
    course = f"{course['code']}: {course['title']}"
    return render_template('requirements-instructor.html', data=data, course=course, instructor_id=instructor_id, enrollment_id=enrollment_id)

@views.route('/instructors/<instructor_id>/enrollments/<enrollment_id>/requirements/<requirement_id>', methods=["GET", "POST"])
def view_instructor_requirement(instructor_id, enrollment_id, requirement_id):
    if g.user != 'instructor':
        return redirect(url_for('.unauthorized'))
    data = db.get_requirement(requirement_id)
    enrollment = db.get_enrollment(enrollment_id)
    course = db.get_course(enrollment['course'])
    course = f"{course['code']}: {course['title']}"
    return render_template('requirement-instructor.html', data=data, course=course, instructor_id=instructor_id, enrollment_id=enrollment_id, requirement_id=requirement_id)

@views.route('/students/<student_id>/enrollments/<enrollment_id>/requirements', methods=["GET", "POST"])
def view_student_requirements(student_id, enrollment_id):
    if g.user != 'student':
        return redirect(url_for('.unauthorized'))
    data = db.get_requirements(enrollment_id)
    enrollment = db.get_enrollment(enrollment_id)
    course = db.get_course(enrollment['course'])
    course = f"{course['code']}: {course['title']}"
    return render_template('requirements-student.html', data=data, course=course, student_id=student_id, enrollment_id=enrollment_id)

@views.route('/students/<student_id>/enrollments/<enrollment_id>/requirements/<requirement_id>', methods=["GET", "POST"])
def view_student_requirement(student_id, enrollment_id, requirement_id):
    if g.user != 'student':
        return redirect(url_for('.unauthorized'))
    form = SubmissionForm()
    data = db.get_requirement(requirement_id)
    enrollment = db.get_enrollment(enrollment_id)
    course = db.get_course(enrollment['course'])
    course = f"{course['code']}: {course['title']}"
    if form.validate_on_submit():
        try:
            message = db.add_submission(requirement_id, form)
        except Exception as e:
            return jsonify({"message": f"{e}"}), 400
    return render_template('requirement-student.html', data=data, form=form, course=course, student_id=student_id, enrollment_id=enrollment_id, requirement_id=requirement_id)

@views.route('/students/<student_id>/enrollments/<enrollment_id>/requirements/<requirement_id>/turn_in')
def turn_in_submission(student_id, enrollment_id, requirement_id):
    if g.user != 'student':
        return redirect(url_for('.unauthorized'))
    try:
        message = db.turn_in_submission(requirement_id)
        return redirect(url_for('.view_student_requirement', student_id=student_id, enrollment_id=enrollment_id, requirement_id=requirement_id))
    except Exception as e:
        return jsonify({"message": f"{e}"}), 400
    
@views.route('/instructors/<instructor_id>/enrollments/<enrollment_id>/requirements/<requirement_id>/return')
def return_submission(instructor_id, enrollment_id, requirement_id):
    if g.user != 'instructor':
        return redirect(url_for('.unauthorized'))
    try:
        message = db.return_submission(requirement_id)
        return redirect(url_for('.view_instructor_requirement', instructor_id=instructor_id, enrollment_id=enrollment_id, requirement_id=requirement_id))
    except Exception as e:
        return jsonify({"message": f"{e}"}), 400

@views.route('/instructors/<instructor_id>/enrollments/<enrollment_id>/requirements/add', methods=["GET", "POST"])
def add_requirement(instructor_id, enrollment_id):
    if g.user != 'instructor':
        return redirect(url_for('.unauthorized'))
    form = RequirementForm()
    if form.validate_on_submit():
        try:
            message = db.add_requirement(enrollment_id, form)
            return redirect(url_for('.view_instructor_requirements', instructor_id=instructor_id, enrollment_id=enrollment_id))
        except Exception as e:
            return jsonify({"message": f"{e}"}), 400
    return render_template('add_requirement.html', instructor_id=instructor_id, enrollment_id=enrollment_id, form=form)

@views.route('/courses')
def courses():
    if g.user not in ['admin']:
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    courses = db.get_courses()
    return render_template('courses.html', page="Courses", courses=courses, views=views)

@views.route('/courses/add_course', methods=["GET", "POST"])
def add_course():
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    form = CourseForm()
    if form.validate_on_submit():
        try:
            db.add_course(form.data)
            return f"""
            <script>
                window.opener.location.reload();
                window.close();
            </script>
            """
        except Exception as e:
            return jsonify({"message": f"An error occured while adding course."}), 400
    return render_template('add_course.html', form=form)

@views.route('/subjects')
def subjects():
    if g.user != 'student':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    data = db.get_student_enrollments(db.uid_to_pk(session.get('id'), 'student'))
    student_id = db.uid_to_pk(session.get('id'), 'student')
    for i in data:
        i['instructor']['name'] = f"{i['instructor']['l_name'].title()}, {i['instructor']['f_name']} {i['instructor']['m_name'][0]}."
    return render_template('subjects.html', page="Subjects", data=data, student_id=student_id, views=views)

@views.route('/message')
def message():
    views = user_views[g.user]
    return render_template('message.html', page="Message", views=views)

@views.route('/users')
def users():
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    instructors = db.get_users('instructor')
    students = db.get_users('student')
    return render_template('users.html', page="Users", instructors=instructors, students=students, views=views)

@views.route('/users/add_user/<user_type>', methods=["GET", "POST"])
def add_user(user_type):
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    form = UserForm()
    if request.method == 'POST':
        form.user_type.data = user_type
    if form.validate_on_submit():
        try:
            db.add_user(form.data)
            return f"""
            <script>
                window.opener.location.reload();
                window.close();
            </script>
            """
        except Exception as e:
            return jsonify({"message": f"Problem adding {user_type} account"}), 400
    return render_template('add_user.html', user_type=user_type, form=form)

@views.route('/enrollment')
def enrollment():
    if g.user != 'student':
        return redirect(url_for('.unauthorized'))
    views = user_views[g.user]
    student = db.get_student(session.get('id'))
    receipt_form = ReceiptForm()
    document_form = DocumentForm()
    receipt_fp = url_for('.get_receipt', user_id=session.get('id'))
    document_fp = url_for('.get_document', user_id=session.get('id'))
    return render_template('enrollment.html', page="Enrollment", student=student, receipt_form=receipt_form, receipt_fp=receipt_fp, document_fp=document_fp, document_form=document_form, views=views)
    
@views.route('/receipt', methods=['POST'])
def receipt():
    if g.user != 'student':
        return redirect(url_for('.unauthorized'))
    form = ReceiptForm()
    if form.validate_on_submit():
        try:
            db.upload_receipt(session.get("id"), form.file)
            flash('Receipt uploaded successfully.')
        except Exception as e:
            flash(f'Problem uploading document. {e}', 'error')
    else:
        flash(f"Problem uploading document. {'. '.join(form.file.errors)}", 'error')
    return redirect(url_for('.enrollment'))

@views.route('/document', methods=['POST'])
def document():
    if g.user != 'student':
        return redirect(url_for('.unauthorized'))
    form = DocumentForm()
    if form.validate_on_submit():
        try:
            db.upload_document(session.get("id"), form.file)
            flash('Document uploaded successfully.')
        except Exception as e:
            flash(f'Problem uploading document. {e}', 'error')
    else:
        flash(f"Problem uploading document. {'. '.join(form.file.errors)}", 'error')
    return redirect(url_for('.enrollment'))
    
@views.route('/uploads/receipts/<user_id>')
def get_receipt(user_id):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'receipts'), 'receipt_' + str(user_id) + '.jpg')

@views.route('/uploads/documents/<user_id>')
def get_document(user_id):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'documents'), 'document_' + str(user_id) + '.pdf')

@views.route('/uploads/<path:fp>')
def ref_fp(fp):
    path = os.path.split(fp)
    directory = '/'.join(path[:-1])
    filename = path[-1]
    return send_from_directory(directory, filename)

@views.route('/students/<student_id>/approve/<progress>', methods=['GET', 'POST'])
def approve_document(student_id, progress):
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    form = StatusConfirmationForm()
    receipt_fp = url_for('.get_receipt', user_id=db.pk_to_uid(student_id, 'student'))
    document_fp = url_for('.get_document', user_id=db.pk_to_uid(student_id, 'student'))
    if form.validate_on_submit():
        message = db.move_student_progress(student_id, progress)
        return f"""
        <script>
            alert("{message}");
            window.opener.location.reload();
            window.close();
        </script>
        """
    return render_template('approve-status.html', form=form, student_id=student_id, progress=progress, receipt_fp=receipt_fp, document_fp=document_fp)

@views.route('/students/<student_id>/courses', methods=['GET', 'POST'])
def enroll_student(student_id):
    if g.user != 'admin':
        return redirect(url_for('.unauthorized'))
    data = db.get_student_enrollment_options(student_id)
    data['student']['name'] = f"{data['student']['l_name'].title()}, {data['student']['f_name']} {data['student']['m_name'][0]}."
    form = StudentCoursesForm(data['available_courses'], data['instructors'])
    if form.validate_on_submit():
        message = db.enroll_student(student_id, form.data)
        data = db.get_student_enrollment_options(student_id)
        data['student']['name'] = f"{data['student']['l_name'].title()}, {data['student']['f_name']} {data['student']['m_name'][0]}."
        form = StudentCoursesForm(data['available_courses'], data['instructors'])
        flash(f"{message}")
    else:
        if form.courses_select.errors:
            flash(f"{form.courses_select.errors[0]}", 'error')
        if form.instructors_select.errors:
            flash(f"{form.instructors_select.errors[0]}", 'error')
    return render_template('modify-courses.html', form=form, data=data)

@views.route('/account')
def account():
    views = user_views[g.user]
    return render_template('account.html', page="Account", views=views)

@views.route('/unauthorized')
def unauthorized():
    return 'Unauthorized to access to this resource.'