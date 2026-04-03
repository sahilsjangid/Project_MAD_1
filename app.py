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

    admin = User.query.filter_by(role="admin").first()
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


# ------------------ AUTH ------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if not email or not password:
            return render_template("login.html", error="Enter email and password")

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
        else:
            return render_template("login.html", error="Invalid credentials or not approved")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        if not name or not email or not password:
            return render_template("register.html", error="All fields required")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template("register.html", error="Email already exists")

        try:
            user = User(name=name, email=email, password=password, role=role)

            if role == "student":
                user.status = "active"

            db.session.add(user)
            db.session.flush()

            if role == "company":
                company = Company(
                    user_id=user.id,
                    company_name=name,
                    hr_contact="",
                    website=""
                )
                db.session.add(company)

            db.session.commit()
            return redirect("/")

        except Exception as e:
            print(e)
            return render_template("register.html", error="Something went wrong")

    return render_template("register.html")


# ------------------ ADMIN ------------------

@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if "user_id" not in session or session["role"] != "admin":
        return redirect("/")

    search = request.form.get("search")

    if search:
        users = User.query.filter(User.name.contains(search)).all()
    else:
        users = User.query.all()

    companies = Company.query.all()
    drives = Drive.query.all()

    return render_template(
        "admin_dashboard.html",
        companies=companies,
        drives=drives,
        users=users
    )


@app.route("/delete_user/<int:id>")
def delete_user(id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect("/")

    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()

    return redirect("/admin")


@app.route("/approve_company/<int:id>")
def approve_company(id):
    company = Company.query.get(id)
    company.approval_status = "approved"

    user = User.query.get(company.user_id)
    user.status = "active"

    db.session.commit()
    return redirect("/admin")


@app.route("/approve_drive/<int:id>")
def approve_drive(id):
    drive = Drive.query.get(id)
    drive.status = "approved"
    db.session.commit()
    return redirect("/admin")


# ------------------ COMPANY ------------------

@app.route("/company")
def company_dashboard():
    if "user_id" not in session or session["role"] != "company":
        return redirect("/")

    drives = Drive.query.filter_by(company_id=session["user_id"]).all()
    return render_template("company_dashboard.html", drives=drives)


@app.route("/create_drive", methods=["GET", "POST"])
def create_drive():
    if "user_id" not in session or session["role"] != "company":
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
        return redirect("/company")

    return render_template("create_drive.html")


@app.route("/view_applications/<int:drive_id>")
def view_applications(drive_id):
    if "user_id" not in session or session["role"] != "company":
        return redirect("/")

    applications = Application.query.filter_by(drive_id=drive_id).all()
    return render_template("view_applications.html", applications=applications)


@app.route("/update_status/<int:app_id>/<status>")
def update_status(app_id, status):
    if "user_id" not in session or session["role"] != "company":
        return redirect("/")

    application = Application.query.get(app_id)
    application.status = status
    db.session.commit()

    return redirect(request.referrer)


# ------------------ STUDENT ------------------

@app.route("/student")
def student_dashboard():
    if "user_id" not in session or session["role"] != "student":
        return redirect("/")

    user = User.query.get(session["user_id"])
    drives = Drive.query.filter_by(status="approved").all()

    return render_template("student_dashboard.html", drives=drives, user=user)



@app.route("/apply/<int:drive_id>")
def apply(drive_id):
    if "user_id" not in session or session["role"] != "student":
        return redirect("/")

    # check duplicate
    existing = Application.query.filter_by(
        student_id=session["user_id"],
        drive_id=drive_id
    ).first()

    if existing:
        return redirect("/student")  # already applied

    app_entry = Application(
        student_id=session["user_id"],
        drive_id=drive_id
    )
    db.session.add(app_entry)
    db.session.commit()

    return redirect("/student")



@app.route("/my_applications")
def my_applications():
    if "user_id" not in session or session["role"] != "student":
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

    return render_template("my_applications.html", applications=data)



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ------------------ RUN ------------------

if __name__ == "__main__":
    app.run(debug=True)