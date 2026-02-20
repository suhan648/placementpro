"""
PlacementPro – Integrated Campus Career Suite
Flask + MongoDB (PyMongo) + Bootstrap 5
"""
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, make_response)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import io, os
from bson import ObjectId
from pymongo import MongoClient, DESCENDING

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                HRFlowable, Table, TableStyle)
from reportlab.lib.enums import TA_CENTER

from config import Config

# ── App ──────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)

_mongo = MongoClient(app.config['MONGO_URI'])
db = _mongo.get_default_database()

# ── Helpers ──────────────────────────────────────────────────
def oid(s):
    try:
        return ObjectId(str(s))
    except Exception:
        return None

def sid(doc):
    return str(doc['_id']) if doc else None

def parse_date(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d') if s else None
    except Exception:
        return None

def parse_dt(s):
    try:
        return datetime.strptime(s, '%Y-%m-%dT%H:%M') if s else None
    except Exception:
        return None

def branches_list():
    return ['CSE', 'IT', 'ECE', 'EEE', 'ME', 'CE', 'MCA', 'MBA', 'Other']

def get_student():
    return db.students.find_one({'user_id': session.get('user_id')})

def get_alumni_profile():
    return db.alumni.find_one({'user_id': session.get('user_id')})

def fmt_drive(d, applicant_count=None):
    """Convert MongoDB drive doc to template-friendly dict."""
    return {
        'id':               sid(d),
        'company_name':     d.get('company_name', ''),
        'job_role':         d.get('job_role', ''),
        'package_lpa':      d.get('package_lpa'),
        'min_cgpa':         d.get('min_cgpa', 0),
        'allowed_branches': d.get('allowed_branches', []),
        'max_backlogs':     d.get('max_backlogs', 0),
        'drive_date':       d.get('drive_date'),
        'venue':            d.get('venue', ''),
        'description':      d.get('description', ''),
        'status':           d.get('status', 'upcoming'),
        'applicants':       applicant_count or 0,
    }

# ── Seed default data ─────────────────────────────────────────
def seed_db():
    if db.faqs.count_documents({}) == 0:
        db.faqs.insert_many([
            {'question': 'What is the minimum CGPA required?',
             'answer': 'The minimum CGPA varies by company. Most companies require at least 6.0 CGPA. Check each drive for exact requirements.',
             'keywords': 'cgpa,minimum,cutoff,criteria', 'created_at': datetime.utcnow()},
            {'question': 'When is the next placement drive?',
             'answer': 'Please check the Live Drives Feed on your dashboard for upcoming placement drives and their dates.',
             'keywords': 'drive,next,when,schedule,date', 'created_at': datetime.utcnow()},
            {'question': 'Where is the interview venue?',
             'answer': 'Interview venues are updated drive-wise. Check your Interview Schedule on the dashboard.',
             'keywords': 'venue,where,interview,location,place', 'created_at': datetime.utcnow()},
            {'question': 'How do I apply for a placement drive?',
             'answer': 'Go to Student Dashboard → Live Drives → Click Apply on an eligible drive.',
             'keywords': 'apply,how,application,register', 'created_at': datetime.utcnow()},
            {'question': 'What is the selection process?',
             'answer': 'Typically: Aptitude Test → Technical Interview → HR Interview. Details vary by company.',
             'keywords': 'process,selection,round,test,interview', 'created_at': datetime.utcnow()},
            {'question': 'How do I download my resume?',
             'answer': 'Go to Student Dashboard → Resume Wizard → Click Download PDF.',
             'keywords': 'resume,download,pdf,cv', 'created_at': datetime.utcnow()},
            {'question': 'Can I contact alumni for referrals?',
             'answer': 'Yes! Visit the Alumni Portal to see job referrals and book mentorship slots.',
             'keywords': 'alumni,referral,contact,mentor', 'created_at': datetime.utcnow()},
            {'question': 'What documents are needed for placement?',
             'answer': 'Mark sheets, ID proof, passport photos, and certificates. Check drive-specific requirements.',
             'keywords': 'document,certificate,marksheet,needed', 'created_at': datetime.utcnow()},
        ])

    if db.market_skills.count_documents({}) == 0:
        db.market_skills.insert_many([
            {'job_role': 'Data Analyst',
             'required_skills': ['Python','SQL','Excel','PowerBI','Tableau','Statistics','Data Visualization','Pandas','NumPy'],
             'insight': '80% of selected Data Analysts had PowerBI skills. Strong SQL is the most common requirement.'},
            {'job_role': 'Software Engineer',
             'required_skills': ['Java','Python','C++','Data Structures','Algorithms','Git','REST APIs','SQL','System Design'],
             'insight': 'Problem-solving (DSA) is tested in 95% of SWE roles. Git is mandatory.'},
            {'job_role': 'Web Developer',
             'required_skills': ['HTML','CSS','JavaScript','React','Node.js','SQL','REST APIs','Bootstrap','Git'],
             'insight': 'React.js appears in 70% of web dev postings. Full-stack knowledge preferred.'},
            {'job_role': 'Data Scientist',
             'required_skills': ['Python','Machine Learning','Deep Learning','TensorFlow','SQL','Statistics','NLP','Pandas','Scikit-learn'],
             'insight': 'ML/DL experience required in 90% of DS roles. Kaggle portfolio adds significant value.'},
            {'job_role': 'DevOps Engineer',
             'required_skills': ['Linux','Docker','Kubernetes','CI/CD','Jenkins','AWS','Git','Bash','Terraform'],
             'insight': 'Cloud platform knowledge is required in 85% of DevOps positions.'},
            {'job_role': 'Business Analyst',
             'required_skills': ['Excel','SQL','PowerBI','Communication','Problem Solving','Agile','JIRA','Data Analysis'],
             'insight': 'Communication skills rated critically important by 80% of BA hiring managers.'},
            {'job_role': 'Cybersecurity Analyst',
             'required_skills': ['Networking','Linux','Python','Cryptography','SIEM','Ethical Hacking','Firewalls','CompTIA'],
             'insight': 'CompTIA Security+ increases selection chances by 60%.'},
            {'job_role': 'Mobile Developer',
             'required_skills': ['Android','Kotlin','Java','iOS','Swift','Flutter','React Native','REST APIs','Git'],
             'insight': 'Flutter and React Native cross-platform skills are trending upward in 2024.'},
        ])

seed_db()

# ── Auth Decorators ───────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard_redirect'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def dashboard_redirect_url():
    r = session.get('role')
    if r == 'admin':   return url_for('admin_dashboard')
    if r == 'student': return url_for('student_dashboard')
    if r == 'alumni':  return url_for('alumni_dashboard')
    return url_for('login')

@app.route('/dashboard')
@login_required
def dashboard_redirect():
    return redirect(dashboard_redirect_url())

# ── AUTH ─────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(dashboard_redirect_url())
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(dashboard_redirect_url())
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = db.users.find_one({'email': email})
        if user and check_password_hash(user['password_hash'], password):
            session['user_id']   = sid(user)
            session['user_name'] = user['name']
            session['email']     = user['email']
            session['role']      = user['role']
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(dashboard_redirect_url())
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(dashboard_redirect_url())
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip().lower()
        password= request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role    = request.form.get('role', 'student')
        if not all([name, email, password]):
            flash('All fields are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif role not in ('admin', 'student', 'alumni'):
            flash('Invalid role.', 'danger')
        elif db.users.find_one({'email': email}):
            flash('Email already registered.', 'danger')
        else:
            uid = db.users.insert_one({
                'name': name, 'email': email,
                'password_hash': generate_password_hash(password),
                'role': role, 'created_at': datetime.utcnow()
            }).inserted_id
            if role == 'student':
                db.students.insert_one({'user_id': str(uid), 'profile_complete': False})
            elif role == 'alumni':
                db.alumni.insert_one({'user_id': str(uid)})
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ── ADMIN ─────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    total_students    = db.users.count_documents({'role': 'student'})
    total_drives      = db.drives.count_documents({})
    placed            = db.applications.count_documents({'status': 'selected'})
    total_applications= db.applications.count_documents({})

    recent_raw = list(db.drives.find().sort('created_at', DESCENDING).limit(5))
    recent_drives = []
    for d in recent_raw:
        cnt = db.applications.count_documents({'drive_id': sid(d)})
        recent_drives.append({
            'id': sid(d), 'company_name': d.get('company_name'),
            'job_role': d.get('job_role'), 'drive_date': d.get('drive_date'),
            'status': d.get('status', 'upcoming'), 'applicants': cnt
        })
    return render_template('admin/dashboard.html',
        total_students=total_students, total_drives=total_drives,
        placed=placed, total_applications=total_applications,
        recent_drives=recent_drives)

@app.route('/admin/drives', methods=['GET', 'POST'])
@role_required('admin')
def admin_drives():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            company  = request.form.get('company_name', '').strip()
            job_role = request.form.get('job_role', '').strip()
            branches = request.form.getlist('allowed_branches')
            if not (company and job_role and branches):
                flash('Company, Job Role, and Branches are required.', 'danger')
            else:
                db.drives.insert_one({
                    'company_name':    company,
                    'job_role':        job_role,
                    'package_lpa':     request.form.get('package_lpa') or None,
                    'min_cgpa':        float(request.form.get('min_cgpa') or 6.0),
                    'allowed_branches':branches,
                    'max_backlogs':    int(request.form.get('max_backlogs') or 0),
                    'drive_date':      parse_date(request.form.get('drive_date')),
                    'venue':           request.form.get('venue', '').strip(),
                    'description':     request.form.get('description', '').strip(),
                    'status':          'upcoming',
                    'created_at':      datetime.utcnow(),
                })
                flash(f'Drive for {company} created!', 'success')
        elif action == 'delete':
            db.drives.delete_one({'_id': oid(request.form.get('drive_id'))})
            flash('Drive deleted.', 'info')
        elif action == 'update_status':
            db.drives.update_one({'_id': oid(request.form.get('drive_id'))},
                                 {'$set': {'status': request.form.get('status')}})
            flash('Status updated.', 'success')

    drives = []
    for d in db.drives.find().sort('created_at', DESCENDING):
        cnt = db.applications.count_documents({'drive_id': sid(d)})
        drives.append({**fmt_drive(d), 'applicants': cnt})
    return render_template('admin/drives.html', drives=drives, branches=branches_list())

@app.route('/admin/criteria', methods=['GET', 'POST'])
@role_required('admin')
def admin_criteria():
    drives_raw   = list(db.drives.find({}, {'company_name':1,'job_role':1}).sort('created_at', DESCENDING))
    drives       = [{'id': sid(d), 'company_name': d['company_name'], 'job_role': d['job_role']} for d in drives_raw]
    eligible     = []
    selected_drive = None
    total_eligible = 0
    notified     = False

    if request.method == 'POST':
        action   = request.form.get('action', 'filter')
        drive_id = request.form.get('drive_id')
        drive_doc= db.drives.find_one({'_id': oid(drive_id)}) if drive_id else None
        if drive_doc:
            selected_drive = fmt_drive(drive_doc)
            allowed = drive_doc.get('allowed_branches', [])
            min_cgpa = float(drive_doc.get('min_cgpa') or 0)
            max_bl   = int(drive_doc.get('max_backlogs') or 0)

            matched_students = list(db.students.find({
                'branch': {'$in': allowed},
                'cgpa':   {'$gte': min_cgpa},
                'backlogs': {'$lte': max_bl}
            }))

            for s in matched_students:
                u = db.users.find_one({'_id': oid(s['user_id'])})
                if u:
                    eligible.append({
                        'name': u['name'], 'email': u['email'],
                        'roll_number': s.get('roll_number',''), 'branch': s.get('branch',''),
                        'cgpa': s.get('cgpa',0), 'backlogs': s.get('backlogs',0),
                        'skills': s.get('skills','')
                    })
            total_eligible = len(eligible)

            if action == 'notify':
                sent = 0
                for e in eligible:
                    try:
                        msg = Message(
                            subject=f"Placement Drive: {drive_doc['job_role']} at {drive_doc['company_name']}",
                            recipients=[e['email']],
                            body=f"Dear {e['name']},\n\nYou are eligible for the upcoming placement drive:\n\nCompany : {drive_doc['company_name']}\nRole    : {drive_doc['job_role']}\nMin CGPA: {drive_doc['min_cgpa']}\n\nLog in to PlacementPro to apply.\n\nTPO Office"
                        )
                        mail.send(msg)
                        sent += 1
                    except Exception:
                        pass
                flash(f'Notifications sent to {sent} eligible students.', 'success')
                notified = True

    return render_template('admin/criteria.html',
        drives=drives, eligible=eligible, selected_drive=selected_drive,
        total_eligible=total_eligible, notified=notified)

@app.route('/admin/scheduler', methods=['GET', 'POST'])
@role_required('admin')
def admin_scheduler():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'schedule':
            drive_id   = request.form.get('drive_id')
            student_id = request.form.get('student_id')
            time_slot  = parse_dt(request.form.get('time_slot'))
            venue      = request.form.get('venue', '').strip()
            notes      = request.form.get('notes', '').strip()
            if time_slot:
                # overlap check: same student at same time
                if db.interviews.find_one({'student_id': student_id, 'time_slot': time_slot}):
                    flash('This student already has an interview at that time.', 'danger')
                else:
                    db.interviews.update_one(
                        {'drive_id': drive_id, 'student_id': student_id},
                        {'$set': {'time_slot': time_slot, 'venue': venue, 'notes': notes,
                                  'drive_id': drive_id, 'student_id': student_id}},
                        upsert=True
                    )
                    db.applications.update_one(
                        {'student_id': student_id, 'drive_id': drive_id},
                        {'$set': {'status': 'interview_scheduled'}}
                    )
                    flash('Interview scheduled!', 'success')
        elif action == 'delete':
            db.interviews.delete_one({'_id': oid(request.form.get('interview_id'))})
            flash('Interview removed.', 'info')

    drives_raw   = list(db.drives.find({}, {'company_name':1,'job_role':1}).sort('drive_date', 1))
    drives       = [{'id': sid(d), 'company_name': d['company_name'], 'job_role': d['job_role']} for d in drives_raw]
    students_raw = list(db.students.find())
    students     = []
    for s in students_raw:
        u = db.users.find_one({'_id': oid(s['user_id'])}, {'name':1})
        if u:
            students.append({'id': sid(s), 'name': u['name'],
                             'branch': s.get('branch',''), 'cgpa': s.get('cgpa',0)})

    interviews_raw = list(db.interviews.find().sort('time_slot', 1))
    interviews = []
    for iv in interviews_raw:
        s = db.students.find_one({'_id': oid(iv['student_id'])})
        u = db.users.find_one({'_id': oid(s['user_id'])}) if s else None
        d = db.drives.find_one({'_id': oid(iv['drive_id'])})
        interviews.append({
            'id': sid(iv),
            'student_name': u['name'] if u else '?',
            'company_name': d['company_name'] if d else '?',
            'job_role':     d['job_role'] if d else '?',
            'time_slot':    iv.get('time_slot'),
            'venue':        iv.get('venue',''),
            'notes':        iv.get('notes',''),
        })
    return render_template('admin/scheduler.html',
        drives=drives, students=students, interviews=interviews)

@app.route('/admin/analytics')
@role_required('admin')
def admin_analytics():
    # Branch-wise placed
    selected_apps = list(db.applications.find({'status': 'selected'}))
    branch_count  = {}
    for a in selected_apps:
        s = db.students.find_one({'_id': oid(a['student_id'])})
        if s and s.get('branch'):
            b = s['branch']
            branch_count[b] = branch_count.get(b, 0) + 1
    branch_data = [{'branch': k, 'count': v} for k, v in branch_count.items()]

    # Status breakdown
    status_counts = {}
    for a in db.applications.find():
        st = a.get('status', 'applied')
        status_counts[st] = status_counts.get(st, 0) + 1
    status_data = [{'status': k, 'count': v} for k, v in status_counts.items()]

    # Drive stats
    drive_stats = []
    for d in db.drives.find().sort('created_at', DESCENDING).limit(10):
        did   = sid(d)
        total = db.applications.count_documents({'drive_id': did})
        sel   = db.applications.count_documents({'drive_id': did, 'status': 'selected'})
        drive_stats.append({'company_name': d['company_name'], 'applicants': total, 'selected': sel})

    # Top skills
    skill_count = {}
    for row in db.market_skills.find():
        for sk in row.get('required_skills', []):
            skill_count[sk] = skill_count.get(sk, 0) + 1
    top_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:10]
    top_skills = [{'skill': k, 'count': v} for k, v in top_skills]

    total_students = db.users.count_documents({'role': 'student'})
    total_placed   = db.applications.count_documents({'status': 'selected'})

    return render_template('admin/analytics.html',
        branch_data=branch_data, drive_stats=drive_stats,
        status_data=status_data, top_skills=top_skills,
        total_students=total_students, total_placed=total_placed)

@app.route('/admin/faqs', methods=['GET', 'POST'])
@role_required('admin')
def admin_faqs():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            q = request.form.get('question', '').strip()
            a = request.form.get('answer', '').strip()
            k = request.form.get('keywords', '').strip()
            if q and a:
                db.faqs.insert_one({'question': q, 'answer': a, 'keywords': k,
                                    'created_at': datetime.utcnow()})
                flash('FAQ added.', 'success')
        elif action == 'delete':
            db.faqs.delete_one({'_id': oid(request.form.get('faq_id'))})
            flash('FAQ deleted.', 'info')
        elif action == 'update':
            db.faqs.update_one({'_id': oid(request.form.get('faq_id'))},
                               {'$set': {'answer': request.form.get('answer', '').strip()}})
            flash('FAQ updated.', 'success')

    faqs_raw = list(db.faqs.find().sort('created_at', 1))
    faqs = [{'id': sid(f), 'question': f['question'], 'answer': f['answer'],
              'keywords': f.get('keywords',''), 'created_at': f.get('created_at')} for f in faqs_raw]
    return render_template('admin/faqs.html', faqs=faqs)

@app.route('/admin/applications')
@role_required('admin')
def admin_applications():
    apps_raw = list(db.applications.find().sort('applied_at', DESCENDING))
    apps = []
    for a in apps_raw:
        s = db.students.find_one({'_id': oid(a['student_id'])})
        u = db.users.find_one({'_id': oid(s['user_id'])}) if s else None
        d = db.drives.find_one({'_id': oid(a['drive_id'])})
        apps.append({
            'id': sid(a),
            'student_name': u['name'] if u else '?',
            'branch': s.get('branch','') if s else '',
            'cgpa':   s.get('cgpa', 0) if s else 0,
            'company_name': d['company_name'] if d else '?',
            'job_role':     d['job_role'] if d else '?',
            'status':       a.get('status','applied'),
            'applied_at':   a.get('applied_at'),
        })
    return render_template('admin/applications.html', applications=apps)

@app.route('/admin/update-status', methods=['POST'])
@role_required('admin')
def admin_update_status():
    valid = ('applied','aptitude_cleared','interview_scheduled','selected','rejected')
    status = request.form.get('status')
    if status in valid:
        db.applications.update_one({'_id': oid(request.form.get('app_id'))},
                                   {'$set': {'status': status}})
        flash('Status updated.', 'success')
    return redirect(url_for('admin_applications'))

# ── STUDENT ───────────────────────────────────────────────────
@app.route('/student/dashboard')
@role_required('student')
def student_dashboard():
    s = get_student()
    student = None
    eligible_drives = []
    apps = []

    if s:
        student = {
            'id': sid(s), 'branch': s.get('branch',''), 'cgpa': s.get('cgpa',0),
            'backlogs': s.get('backlogs',0), 'skills': s.get('skills',''),
            'profile_complete': s.get('profile_complete', False)
        }
        for d in db.drives.find({'status': {'$ne': 'completed'}}):
            allowed = d.get('allowed_branches', [])
            if (s.get('branch') in allowed and
                float(s.get('cgpa') or 0) >= float(d.get('min_cgpa') or 0) and
                int(s.get('backlogs') or 0) <= int(d.get('max_backlogs') or 0)):
                app_doc = db.applications.find_one({'student_id': sid(s), 'drive_id': sid(d)})
                entry   = fmt_drive(d)
                entry['application'] = {'id': sid(app_doc), 'status': app_doc['status']} if app_doc else None
                eligible_drives.append(entry)

        for a in db.applications.find({'student_id': sid(s)}).sort('applied_at', DESCENDING).limit(5):
            d = db.drives.find_one({'_id': oid(a['drive_id'])})
            apps.append({'company_name': d['company_name'] if d else '?',
                         'job_role':     d['job_role'] if d else '?',
                         'status':       a.get('status','applied'),
                         'applied_at':   a.get('applied_at')})

    return render_template('student/dashboard.html',
        student=student, eligible_drives=eligible_drives, apps=apps)

@app.route('/student/profile', methods=['GET', 'POST'])
@role_required('student')
def student_profile():
    u = db.users.find_one({'_id': oid(session['user_id'])})
    if request.method == 'POST':
        name   = request.form.get('name', '').strip()
        fields = {
            'roll_number':    request.form.get('roll_number','').strip(),
            'branch':         request.form.get('branch','').strip(),
            'cgpa':           float(request.form.get('cgpa') or 0),
            'backlogs':       int(request.form.get('backlogs') or 0),
            'phone':          request.form.get('phone','').strip(),
            'address':        request.form.get('address','').strip(),
            'skills':         request.form.get('skills','').strip(),
            'certifications': request.form.get('certifications','').strip(),
            'internships':    request.form.get('internships','').strip(),
            'projects':       request.form.get('projects','').strip(),
            'linkedin':       request.form.get('linkedin','').strip(),
            'github':         request.form.get('github','').strip(),
        }
        fields['profile_complete'] = bool(
            fields['roll_number'] and fields['branch'] and fields['cgpa'] and fields['phone'] and fields['skills'])
        db.students.update_one({'user_id': session['user_id']}, {'$set': fields})
        if name:
            db.users.update_one({'_id': oid(session['user_id'])}, {'$set': {'name': name}})
            session['user_name'] = name
        flash('Profile saved!', 'success')

    s = get_student() or {}
    profile = {
        'name': u['name'] if u else '', 'email': u['email'] if u else '',
        'roll_number': s.get('roll_number',''), 'branch': s.get('branch',''),
        'cgpa': s.get('cgpa',''), 'backlogs': s.get('backlogs', 0),
        'phone': s.get('phone',''), 'address': s.get('address',''),
        'skills': s.get('skills',''), 'certifications': s.get('certifications',''),
        'internships': s.get('internships',''), 'projects': s.get('projects',''),
        'linkedin': s.get('linkedin',''), 'github': s.get('github',''),
        'profile_complete': s.get('profile_complete', False),
    }
    return render_template('student/profile.html', profile=profile, branches=branches_list())

@app.route('/student/resume-wizard')
@role_required('student')
def resume_wizard():
    u = db.users.find_one({'_id': oid(session['user_id'])})
    s = get_student() or {}
    profile = {
        'name': u['name'] if u else '', 'email': u['email'] if u else '',
        'phone': s.get('phone',''), 'linkedin': s.get('linkedin',''), 'github': s.get('github',''),
        'roll_number': s.get('roll_number',''), 'branch': s.get('branch',''),
        'cgpa': s.get('cgpa',''), 'backlogs': s.get('backlogs',0),
        'skills': s.get('skills',''), 'internships': s.get('internships',''),
        'projects': s.get('projects',''), 'certifications': s.get('certifications',''),
    }
    return render_template('student/resume_wizard.html', profile=profile)

@app.route('/student/download-resume')
@role_required('student')
def download_resume():
    u = db.users.find_one({'_id': oid(session['user_id'])})
    s = get_student() or {}
    if not u:
        flash('Profile not found.', 'danger')
        return redirect(url_for('student_profile'))

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('T', parent=styles['Title'], fontSize=20,
                              textColor=colors.HexColor('#3730a3'), spaceAfter=2, alignment=TA_CENTER)
    sub_s   = ParagraphStyle('S', parent=styles['Normal'], fontSize=10,
                              textColor=colors.HexColor('#6b7280'), spaceAfter=2, alignment=TA_CENTER)
    sec_s   = ParagraphStyle('H', parent=styles['Heading2'], fontSize=12,
                              textColor=colors.HexColor('#3730a3'), spaceBefore=10, spaceAfter=4)
    body_s  = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, spaceAfter=3, leading=14)
    bull_s  = ParagraphStyle('L', parent=styles['Normal'], fontSize=10, spaceAfter=2, leftIndent=15, leading=13)

    story = []
    name  = u.get('name', 'Name')
    email = u.get('email', '')

    story.append(Paragraph(name, title_s))
    cp = []
    if email:                cp.append(email)
    if s.get('phone'):       cp.append(s['phone'])
    if s.get('linkedin'):    cp.append(s['linkedin'])
    if s.get('github'):      cp.append(s['github'])
    story.append(Paragraph(' | '.join(cp), sub_s))
    story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#3730a3'), spaceAfter=6))

    # Education
    story.append(Paragraph('Education', sec_s))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e5e7eb'), spaceAfter=4))
    edu = Table([
        [Paragraph(f"<b>Branch:</b> {s.get('branch','—')}", body_s),
         Paragraph(f"<b>CGPA:</b> {s.get('cgpa','—')}", body_s)],
        [Paragraph(f"<b>Roll No:</b> {s.get('roll_number','—')}", body_s),
         Paragraph(f"<b>Backlogs:</b> {s.get('backlogs',0)}", body_s)],
    ], colWidths=['50%','50%'])
    edu.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(edu)
    story.append(Spacer(1, 6))

    def section(title, text):
        if not text: return
        story.append(Paragraph(title, sec_s))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e5e7eb'), spaceAfter=4))
        for line in text.split('\n'):
            line = line.strip()
            if line: story.append(Paragraph(f'• {line}', bull_s))
        story.append(Spacer(1, 4))

    section('Technical Skills',  s.get('skills',''))
    section('Projects',          s.get('projects',''))
    section('Internships',       s.get('internships',''))
    section('Certifications',    s.get('certifications',''))

    doc.build(story)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    fname = f"{name.replace(' ','_')}_Resume.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response

@app.route('/student/drives')
@role_required('student')
def student_drives():
    s = get_student()
    eligible_drives = []
    if s:
        for d in db.drives.find().sort('drive_date', 1):
            allowed    = d.get('allowed_branches', [])
            is_eligible= (s.get('branch') in allowed and
                          float(s.get('cgpa') or 0) >= float(d.get('min_cgpa') or 0) and
                          int(s.get('backlogs') or 0) <= int(d.get('max_backlogs') or 0))
            app_doc = db.applications.find_one({'student_id': sid(s), 'drive_id': sid(d)})
            entry   = fmt_drive(d)
            entry['is_eligible']  = is_eligible
            entry['application']  = {'id': sid(app_doc), 'status': app_doc['status']} if app_doc else None
            eligible_drives.append(entry)
    student = {'id': sid(s), 'branch': s.get('branch'), 'cgpa': s.get('cgpa'), 'backlogs': s.get('backlogs')} if s else None
    return render_template('student/drives.html', eligible_drives=eligible_drives, student=student)

@app.route('/student/apply/<drive_id>', methods=['POST'])
@role_required('student')
def student_apply(drive_id):
    s = get_student()
    if not s:
        flash('Complete your profile first.', 'warning')
        return redirect(url_for('student_drives'))
    existing = db.applications.find_one({'student_id': sid(s), 'drive_id': drive_id})
    if existing:
        flash('You already applied to this drive.', 'info')
    else:
        db.applications.insert_one({
            'student_id': sid(s), 'drive_id': drive_id,
            'status': 'applied', 'applied_at': datetime.utcnow()
        })
        flash('Applied successfully!', 'success')
    return redirect(url_for('student_drives'))

@app.route('/student/applications')
@role_required('student')
def student_applications():
    s = get_student()
    apps = []
    if s:
        for a in db.applications.find({'student_id': sid(s)}).sort('applied_at', DESCENDING):
            d = db.drives.find_one({'_id': oid(a['drive_id'])})
            iv = db.interviews.find_one({'student_id': sid(s), 'drive_id': a['drive_id']})
            apps.append({
                'company_name':    d['company_name'] if d else '?',
                'job_role':        d['job_role'] if d else '?',
                'package_lpa':     d.get('package_lpa') if d else None,
                'drive_date':      d.get('drive_date') if d else None,
                'venue':           d.get('venue') if d else '',
                'status':          a.get('status','applied'),
                'applied_at':      a.get('applied_at'),
                'interview_time':  iv.get('time_slot') if iv else None,
                'interview_venue': iv.get('venue') if iv else '',
            })
    return render_template('student/applications.html', apps=apps)

# ── ALUMNI ────────────────────────────────────────────────────
@app.route('/alumni/dashboard')
@role_required('alumni')
def alumni_dashboard():
    al = get_alumni_profile()
    stats = {'referrals': 0, 'slots': 0, 'booked': 0}
    recent_referrals = []
    if al:
        aid = sid(al)
        stats['referrals'] = db.referrals.count_documents({'alumni_id': aid})
        stats['slots']     = db.mentorship_slots.count_documents({'alumni_id': aid})
        stats['booked']    = db.mentorship_slots.count_documents({'alumni_id': aid, 'booked_by': {'$ne': None}})
    for r in db.referrals.find().sort('posted_at', DESCENDING).limit(5):
        al2 = db.alumni.find_one({'_id': oid(r['alumni_id'])})
        u2  = db.users.find_one({'_id': oid(al2['user_id'])}) if al2 else None
        recent_referrals.append({
            'company': r['company'], 'job_role': r['job_role'],
            'description': r.get('description',''), 'posted_by': u2['name'] if u2 else '?',
            'deadline': r.get('deadline')
        })
    return render_template('alumni/dashboard.html', stats=stats, recent_referrals=recent_referrals)

@app.route('/alumni/referrals', methods=['GET', 'POST'])
@role_required('alumni')
def alumni_referrals():
    al = get_alumni_profile()
    if request.method == 'POST' and al:
        action = request.form.get('action')
        if action == 'post':
            company  = request.form.get('company', '').strip()
            job_role = request.form.get('job_role', '').strip()
            if company and job_role:
                db.referrals.insert_one({
                    'alumni_id':   sid(al), 'company': company, 'job_role': job_role,
                    'description': request.form.get('description','').strip(),
                    'apply_link':  request.form.get('apply_link','').strip(),
                    'deadline':    parse_date(request.form.get('deadline')),
                    'posted_at':   datetime.utcnow(),
                })
                flash('Referral posted!', 'success')
        elif action == 'delete':
            db.referrals.delete_one({'_id': oid(request.form.get('ref_id')), 'alumni_id': sid(al)})
            flash('Referral deleted.', 'info')

    referrals = []
    for r in db.referrals.find().sort('posted_at', DESCENDING):
        al2 = db.alumni.find_one({'_id': oid(r['alumni_id'])})
        u2  = db.users.find_one({'_id': oid(al2['user_id'])}) if al2 else None
        referrals.append({
            'id': sid(r), 'company': r['company'], 'job_role': r['job_role'],
            'description': r.get('description',''), 'apply_link': r.get('apply_link',''),
            'deadline': r.get('deadline'), 'posted_by': u2['name'] if u2 else '?',
            'posted_at': r.get('posted_at'),
            'is_mine': al and r['alumni_id'] == sid(al)
        })
    return render_template('alumni/referrals.html', referrals=referrals)

@app.route('/alumni/mentorship', methods=['GET', 'POST'])
@role_required('alumni')
def alumni_mentorship():
    al = get_alumni_profile()
    if request.method == 'POST' and al:
        action = request.form.get('action')
        if action == 'add_slot':
            t = parse_dt(request.form.get('available_time'))
            if t:
                db.mentorship_slots.insert_one({
                    'alumni_id': sid(al), 'available_time': t,
                    'meeting_link': request.form.get('meeting_link','').strip(),
                    'booked_by': None
                })
                flash('Slot added!', 'success')
        elif action == 'delete_slot':
            db.mentorship_slots.delete_one({'_id': oid(request.form.get('slot_id')), 'alumni_id': sid(al)})
            flash('Slot removed.', 'info')

    my_slots = []
    if al:
        for ms in db.mentorship_slots.find({'alumni_id': sid(al)}).sort('available_time', 1):
            booker_name = None
            if ms.get('booked_by'):
                s = db.students.find_one({'_id': oid(ms['booked_by'])})
                u = db.users.find_one({'_id': oid(s['user_id'])}) if s else None
                booker_name = u['name'] if u else None
            my_slots.append({'id': sid(ms), 'available_time': ms.get('available_time'),
                             'meeting_link': ms.get('meeting_link',''), 'booked_by_name': booker_name})

    available_slots = []
    for ms in db.mentorship_slots.find({'booked_by': None}).sort('available_time', 1):
        al2 = db.alumni.find_one({'_id': oid(ms['alumni_id'])})
        u2  = db.users.find_one({'_id': oid(al2['user_id'])}) if al2 else None
        available_slots.append({
            'id': sid(ms), 'alumni_name': u2['name'] if u2 else '?',
            'company': al2.get('company','') if al2 else '',
            'designation': al2.get('designation','') if al2 else '',
            'available_time': ms.get('available_time'),
            'meeting_link':   ms.get('meeting_link',''),
        })
    return render_template('alumni/mentorship.html', my_slots=my_slots, available_slots=available_slots)

@app.route('/alumni/book-slot/<slot_id>', methods=['POST'])
@role_required('student')
def book_mentorship_slot(slot_id):
    s = get_student()
    if s:
        result = db.mentorship_slots.update_one(
            {'_id': oid(slot_id), 'booked_by': None},
            {'$set': {'booked_by': sid(s)}}
        )
        if result.modified_count:
            flash('Slot booked!', 'success')
        else:
            flash('Slot already booked or unavailable.', 'warning')
    return redirect(url_for('alumni_mentorship'))

# ── MARKET INTELLIGENCE ───────────────────────────────────────
@app.route('/market/skill-gap', methods=['GET', 'POST'])
@login_required
def skill_gap():
    roles_raw = list(db.market_skills.find({}, {'job_role': 1}))
    roles     = [{'id': sid(r), 'job_role': r['job_role']} for r in roles_raw]
    result    = None
    selected_role = None
    my_skills = ''

    if session.get('role') == 'student':
        s = get_student()
        if s: my_skills = s.get('skills', '')

    if request.method == 'POST':
        role_id        = request.form.get('role_id')
        user_skills_raw= request.form.get('user_skills', '')
        role_doc       = db.market_skills.find_one({'_id': oid(role_id)})
        if role_doc:
            selected_role = role_doc['job_role']
            required  = [sk.strip().lower() for sk in role_doc.get('required_skills', [])]
            user_sk   = [sk.strip().lower() for sk in user_skills_raw.split(',') if sk.strip()]
            matched   = [sk for sk in required if sk in user_sk]
            missing   = [sk for sk in required if sk not in user_sk]
            pct       = int(len(matched) / len(required) * 100) if required else 0
            result = {'role': role_doc['job_role'], 'required': required,
                      'matched': matched, 'missing': missing,
                      'pct': pct, 'insight': role_doc.get('insight', '')}

    return render_template('market/skill_gap.html',
        roles=roles, result=result, my_skills=my_skills, selected_role=selected_role)

# ── CHATBOT ───────────────────────────────────────────────────
@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot/bot.html')

@app.route('/chatbot/ask', methods=['POST'])
@login_required
def chatbot_ask():
    query = (request.get_json() or {}).get('message', '').strip().lower()
    if not query:
        return jsonify({'reply': 'Please type a message.'})

    best_match, best_score = None, 0
    for faq in db.faqs.find():
        score = 0
        for kw in (faq.get('keywords') or '').split(','):
            if kw.strip() and kw.strip().lower() in query: score += 3
        for word in faq['question'].lower().split():
            if len(word) > 3 and word in query: score += 1
        if score > best_score:
            best_score = score
            best_match = faq['answer']

    if best_match and best_score > 0:
        reply = best_match
    elif any(g in query for g in ['hi','hello','hey','good morning','good evening']):
        reply = 'Hello! 👋 I am PlacementBot. Ask me about cutoffs, drives, resume, or referrals!'
    elif 'thank' in query:
        reply = "You're welcome! Best of luck! 😊"
    elif 'bye' in query:
        reply = 'Goodbye! All the best! 🎓'
    else:
        reply = ('I\'m not sure about that. Try asking about:\n'
                 '• CGPA cutoffs\n• Interview schedule\n• How to apply\n'
                 '• Resume download\n• Alumni referrals')
    return jsonify({'reply': reply})

# ── ERRORS ────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

if __name__ == '__main__':
    app.run(debug=True, port=5000)
