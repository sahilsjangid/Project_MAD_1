from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------ MODELS ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))
    status = db.Column(db.String(20), default="pending")


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    company_name = db.Column(db.String(100))
    hr_contact = db.Column(db.String(100))
    website = db.Column(db.String(100))
    approval_status = db.Column(db.String(20), default="pending")


class Drive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer)
    job_title = db.Column(db.String(100))
    job_description = db.Column(db.Text)
    eligibility = db.Column(db.String(100))
    deadline = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    drive_id = db.Column(db.Integer)
    status = db.Column(db.String(20), default="applied")


# ------------------ INIT DB ------------------

with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email="admin@gmail.com").first()
    if not admin:
        admin = User(
            name="Admin",
            email="admin@gmail.com",
            password="admin",
            role="admin",
            status="active"
        )
        db.session.add(admin)
        db.session.commit()
    else:
        admin.role = "admin"
        admin.status = "active"
        db.session.commit()


# ------------------ AUTH ------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        role = session["role"]
        if role == "admin":
            return redirect("/admin")
        elif role == "company":
            return redirect("/company")
        else:
            return redirect("/student")

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, password=password).first()

        if user and user.status == "active":
            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "admin":
                return redirect("/admin")
            elif user.role == "company":
                return redirect("/company")
            else:
                return redirect("/student")

        return render_template("auth/login.html", error="Invalid credentials")

    return render_template("auth/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        if User.query.filter_by(email=email).first():
            return render_template("auth/register.html", error="Email exists")

        if role not in ["student", "company"]:
            return redirect("/")

        user = User(name=name, email=email, password=password, role=role)

        if role == "student":
            user.status = "active"

        db.session.add(user)
        db.session.flush()

        if role == "company":
            db.session.add(Company(user_id=user.id, company_name=name))

        db.session.commit()
        return redirect("/")

    return render_template("auth/register.html")


# ------------------ ADMIN ------------------

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/")
    return render_template("admin/admin_dashboard.html")


@app.route("/admin/companies")
def all_companies():
    if session.get("role") != "admin":
        return redirect("/")
    companies = Company.query.all()
    return render_template("admin/all_company.html", companies=companies)


@app.route("/admin/students")
def all_students():
    if session.get("role") != "admin":
        return redirect("/")
    students = User.query.filter_by(role="student").all()
    return render_template("admin/all_student.html", students=students)


@app.route("/admin/drives")
def all_drives():
    if session.get("role") != "admin":
        return redirect("/")
    drives = Drive.query.all()
    return render_template("admin/all_drives.html", drives=drives)


@app.route("/admin/applications")
def all_applications():
    if session.get("role") != "admin":
        return redirect("/")
    applications = Application.query.all()
    return render_template("admin/all_application.html", applications=applications)


@app.route("/approve_company/<int:id>")
def approve_company(id):
    company = Company.query.get(id)
    company.approval_status = "approved"

    user = User.query.get(company.user_id)
    user.status = "active"

    db.session.commit()
    return redirect("/admin/companies")


@app.route("/approve_drive/<int:id>")
def approve_drive(id):
    drive = Drive.query.get(id)
    drive.status = "approved"
    db.session.commit()
    return redirect("/admin/drives")


@app.route("/delete_user/<int:id>")
def delete_user(id):
    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()
    return redirect("/admin/students")


# ------------------ COMPANY ------------------

@app.route("/company")
def company_dashboard():
    if session.get("role") != "company":
        return redirect("/")
    return render_template("company/company_dashboard.html")


@app.route("/company/drives")
def company_drives():
    if session.get("role") != "company":
        return redirect("/")
    drives = Drive.query.filter_by(company_id=session["user_id"]).all()
    return render_template("company/view_drives.html", drives=drives)


@app.route("/company/create", methods=["GET", "POST"])
def create_drive():
    if session.get("role") != "company":
        return redirect("/")

    if request.method == "POST":
        drive = Drive(
            company_id=session["user_id"],
            job_title=request.form["title"],
            job_description=request.form["description"],
            eligibility=request.form["eligibility"],
            deadline=request.form["deadline"]
        )
        db.session.add(drive)
        db.session.commit()
        return redirect("/company/drives")

    return render_template("company/add_new_drives.html")


@app.route("/company/applications/<int:drive_id>")
def view_applications(drive_id):
    if session.get("role") != "company":
        return redirect("/")
    applications = Application.query.filter_by(drive_id=drive_id).all()
    return render_template("company/all_applications.html", applications=applications)


@app.route("/company/profile", methods=["GET", "POST"])
def edit_profile():
    if session.get("role") != "company":
        return redirect("/")

    company = Company.query.filter_by(user_id=session["user_id"]).first()

    if request.method == "POST":
        company.company_name = request.form["company_name"]
        company.hr_contact = request.form["hr_contact"]
        company.website = request.form["website"]
        db.session.commit()
        return redirect("/company")

    return render_template("company/edit_profile.html", company=company)

@app.route("/update_status/<int:app_id>/<status>")
def update_status(app_id, status):
    if session.get("role") != "company":
        return redirect("/")

    application = Application.query.get(app_id)

    if not application:
        return redirect("/company")

    # update status
    if status in ["shortlisted", "selected", "rejected"]:
        application.status = status
        db.session.commit()

    # redirect back to same drive applications page
    return redirect(f"/company/applications/{application.drive_id}")


# ------------------ STUDENT ------------------

@app.route("/student")
def student_dashboard():
    if session.get("role") != "student":
        return redirect("/")

    user = User.query.get(session["user_id"])

    return render_template(
        "student/student_dashboard.html",
        user=user
    )


@app.route("/student/explore")
def explore_drives():
    if session.get("role") != "student":
        return redirect("/")

    user = User.query.get(session["user_id"])
    drives = Drive.query.filter_by(status="approved").all()

    applied = Application.query.filter_by(student_id=user.id).all()
    applied_ids = [a.drive_id for a in applied]

    return render_template(
        "student/explore_drives.html",
        drives=drives,
        applied_ids=applied_ids
    )


@app.route("/student/apply/<int:drive_id>")
def apply_page(drive_id):
    if session.get("role") != "student":
        return redirect("/")
    drive = Drive.query.get(drive_id)
    return render_template("student/apply_drives.html", drive=drive)


@app.route("/apply/<int:drive_id>")
def apply(drive_id):
    if session.get("role") != "student":
        return redirect("/")

    if Application.query.filter_by(
        student_id=session["user_id"], drive_id=drive_id
    ).first():
        return redirect("/student")

    db.session.add(Application(
        student_id=session["user_id"],
        drive_id=drive_id
    ))
    db.session.commit()

    return redirect("/student")


@app.route("/my_applications")
def my_applications():
    if session.get("role") != "student":
        return redirect("/")

    applications = Application.query.filter_by(student_id=session["user_id"]).all()

    data = []
    for app in applications:
        drive = Drive.query.get(app.drive_id)
        company = Company.query.filter_by(user_id=drive.company_id).first()

        data.append({
            "job_title": drive.job_title,
            "company_name": company.company_name if company else "N/A",
            "status": app.status
        })

    return render_template("student/your_application.html", applications=data)


@app.route("/student/profile", methods=["GET", "POST"])
def student_profile():
    if session.get("role") != "student":
        return redirect("/")

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        user.name = request.form["name"]
        user.email = request.form["email"]
        db.session.commit()
        return redirect("/student")

    return render_template("student/edit_profile.html", user=user)


# ------------------ LOGOUT ------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.before_request
def clear_session_on_restart():
    if not hasattr(app, "session_cleared"):
        session.clear()
        app.session_cleared = True


# ------------------ RUN ------------------

if __name__ == "__main__":
    app.run(debug=True)