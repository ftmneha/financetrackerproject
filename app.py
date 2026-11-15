import os
import io
import time
from collections import defaultdict
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
    jsonify,
    Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from config import config_by_name
from models import db, User, Income, Expense, Budget

# Optional matplotlib support (kept for legacy asset generation)
# Optional matplotlib support (kept for legacy asset generation)
try:
    import matplotlib
    matplotlib.use("Agg")
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =====================================
# Application Factory / Initialization
# =====================================
env_name = os.environ.get("FLASK_ENV", os.environ.get("CONFIG_ENV", "default"))
app = Flask(__name__)
app.config.from_object(config_by_name.get(env_name, config_by_name["default"]))

# Override database URI if DATABASE_URL is set in environment
if os.environ.get("DATABASE_URL"):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

db.init_app(app)

# =====================================
# Prometheus Metrics State
# =====================================
METRICS = {
    "requests_total": defaultdict(int),
    "request_duration_sum": defaultdict(float),
    "request_duration_count": defaultdict(int),
    "start_time": time.time()
}


@app.before_request
def before_request_metrics():
    request._start_time = time.time()


@app.after_request
def after_request_metrics(response):
    if hasattr(request, "_start_time"):
        duration = time.time() - request._start_time
        endpoint = request.endpoint or "unknown"
        method = request.method
        status = str(response.status_code)
        key = (method, endpoint, status)
        METRICS["requests_total"][key] += 1
        METRICS["request_duration_sum"][endpoint] += duration
        METRICS["request_duration_count"][endpoint] += 1
    return response


# =====================================
# Health Check & Monitoring Endpoints
# =====================================

@app.route("/health")
def health():
    """Health check endpoint for Kubernetes probes & AWS ALB."""
    db_status = "healthy"
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    is_healthy = db_status == "healthy"
    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "personal-finance-tracker",
        "database": db_status,
        "uptime_seconds": int(time.time() - METRICS["start_time"]),
        "version": "1.0.0"
    }
    return jsonify(response), (200 if is_healthy else 503)


@app.route("/metrics")
def metrics():
    """Prometheus exposition metrics endpoint."""
    lines = []

    # App info
    lines.append("# HELP fintrack_app_info Application build and version information")
    lines.append("# TYPE fintrack_app_info gauge")
    lines.append('fintrack_app_info{version="1.0.0",framework="flask",subject="INT378"} 1')

    # Total requests
    lines.append("# HELP fintrack_http_requests_total Total HTTP requests handled")
    lines.append("# TYPE fintrack_http_requests_total counter")
    for (method, endpoint, status), count in METRICS["requests_total"].items():
        metric = f'fintrack_http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
        lines.append(metric)

    # Request duration sum
    lines.append("# HELP fintrack_http_request_duration_seconds_sum Total duration of HTTP requests in seconds")
    lines.append("# TYPE fintrack_http_request_duration_seconds_sum counter")
    for endpoint, dur_sum in METRICS["request_duration_sum"].items():
        lines.append(f'fintrack_http_request_duration_seconds_sum{{endpoint="{endpoint}"}} {dur_sum:.6f}')

    # Request duration count
    lines.append("# HELP fintrack_http_request_duration_seconds_count Count of HTTP requests tracked for duration")
    lines.append("# TYPE fintrack_http_request_duration_seconds_count counter")
    for endpoint, dur_count in METRICS["request_duration_count"].items():
        lines.append(f'fintrack_http_request_duration_seconds_count{{endpoint="{endpoint}"}} {dur_count}')

    # Application business metrics from database
    try:
        total_users = User.query.count()
        total_incomes = Income.query.count()
        total_expenses = Expense.query.count()
        income_sum = db.session.query(db.func.sum(Income.amount)).scalar() or 0.0
        expense_sum = db.session.query(db.func.sum(Expense.amount)).scalar() or 0.0
        budget_record = Budget.query.first()
        budget_amt = budget_record.amount if budget_record else 0.0

        lines.append("# HELP fintrack_registered_users_total Total registered users")
        lines.append("# TYPE fintrack_registered_users_total gauge")
        lines.append(f"fintrack_registered_users_total {total_users}")

        lines.append("# HELP fintrack_transactions_total Total financial transactions recorded")
        lines.append("# TYPE fintrack_transactions_total gauge")
        lines.append(f"fintrack_transactions_total {total_incomes + total_expenses}")

        lines.append("# HELP fintrack_income_total_amount Sum of all income recorded")
        lines.append("# TYPE fintrack_income_total_amount gauge")
        lines.append(f"fintrack_income_total_amount {float(income_sum):.2f}")

        lines.append("# HELP fintrack_expense_total_amount Sum of all expenses recorded")
        lines.append("# TYPE fintrack_expense_total_amount gauge")
        lines.append(f"fintrack_expense_total_amount {float(expense_sum):.2f}")

        lines.append("# HELP fintrack_budget_amount Current set budget")
        lines.append("# TYPE fintrack_budget_amount gauge")
        lines.append(f"fintrack_budget_amount {float(budget_amt):.2f}")
    except Exception:
        pass

    return Response("\n".join(lines) + "\n", mimetype="text/plain; version=0.0.4; charset=utf-8")


@app.route("/api/chart-data")
def chart_data():
    """API endpoint providing live JSON chart data for Chart.js."""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    incomes = Income.query.filter((Income.user_id == user_id) | (Income.user_id.is_(None))).all()
    expenses = Expense.query.filter((Expense.user_id == user_id) | (Expense.user_id.is_(None))).all()

    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)

    categories = {}
    for exp in expenses:
        categories[exp.category] = round(categories.get(exp.category, 0.0) + exp.amount, 2)

    return jsonify({
        "summary": {
            "income": round(total_income, 2),
            "expense": round(total_expense, 2),
            "balance": round(total_income - total_expense, 2)
        },
        "expense_categories": {
            "labels": list(categories.keys()),
            "data": list(categories.values())
        }
    })


# =====================================
# Main Application Routes
# =====================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not fullname or not email or not password:
            flash("All fields are required!", "warning")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered! Please log in or use another email.", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(
            fullname=fullname,
            email=email,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in with your credentials.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.fullname
            flash(f"Welcome back, {user.fullname}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password! Please check your credentials.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access your dashboard.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    name = session.get("user_name", "User")

    incomes = Income.query.filter((Income.user_id == user_id) | (Income.user_id.is_(None))).all()
    expenses = Expense.query.filter((Expense.user_id == user_id) | (Expense.user_id.is_(None))).all()

    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)
    balance = total_income - total_expense

    budget = Budget.query.filter((Budget.user_id == user_id) | (Budget.user_id.is_(None))).first()
    budget_amount = budget.amount if budget else 0.0
    remaining_budget = budget_amount - total_expense

    # Category breakdown for Chart.js
    categories = {}
    for exp in expenses:
        categories[exp.category] = round(categories.get(exp.category, 0.0) + exp.amount, 2)

    category_labels = list(categories.keys())
    category_data = list(categories.values())

    return render_template(
        "dashboard.html",
        name=name,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        balance=round(balance, 2),
        budget_amount=round(budget_amount, 2),
        remaining_budget=round(remaining_budget, 2),
        category_labels=category_labels,
        category_data=category_data,
        chart_image="charts/income_expense.png",
        pie_chart="charts/expense_pie.png"
    )


@app.route("/add_income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        source = request.form.get("source", "").strip()
        amount_val = request.form.get("amount", "0")
        date = request.form.get("date", "").strip()

        try:
            amount = float(amount_val)
        except ValueError:
            flash("Invalid amount entered.", "danger")
            return redirect(url_for("add_income"))

        income = Income(
            user_id=session.get("user_id"),
            source=source,
            amount=amount,
            date=date
        )
        db.session.add(income)
        db.session.commit()
        flash("Income entry added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_income.html")


@app.route("/add_expense", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        category = request.form.get("category", "").strip()
        amount_val = request.form.get("amount", "0")
        date = request.form.get("date", "").strip()

        try:
            amount = float(amount_val)
        except ValueError:
            flash("Invalid amount entered.", "danger")
            return redirect(url_for("add_expense"))

        expense = Expense(
            user_id=session.get("user_id"),
            category=category,
            amount=amount,
            date=date
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense entry added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_expense.html")


@app.route("/transactions")
def transactions():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    search = request.args.get("search", "").strip()

    income_query = Income.query.filter((Income.user_id == user_id) | (Income.user_id.is_(None)))
    expense_query = Expense.query.filter((Expense.user_id == user_id) | (Expense.user_id.is_(None)))

    if search:
        income_query = income_query.filter(Income.source.contains(search))
        expense_query = expense_query.filter(Expense.category.contains(search))

    incomes = income_query.all()
    expenses = expense_query.all()

    return render_template(
        "transactions.html",
        incomes=incomes,
        expenses=expenses,
        search=search
    )


@app.route("/edit_income/<int:id>", methods=["GET", "POST"])
def edit_income(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    income = Income.query.get_or_404(id)

    if request.method == "POST":
        income.source = request.form.get("source", income.source).strip()
        try:
            income.amount = float(request.form.get("amount", income.amount))
        except ValueError:
            pass
        income.date = request.form.get("date", income.date).strip()
        db.session.commit()
        flash("Income updated successfully!", "success")
        return redirect(url_for("transactions"))

    return render_template("edit_income.html", income=income)


@app.route("/delete_income/<int:id>")
def delete_income(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    income = Income.query.get_or_404(id)
    db.session.delete(income)
    db.session.commit()
    flash("Income deleted successfully!", "info")
    return redirect(url_for("transactions"))


@app.route("/edit_expense/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = Expense.query.get_or_404(id)

    if request.method == "POST":
        expense.category = request.form.get("category", expense.category).strip()
        try:
            expense.amount = float(request.form.get("amount", expense.amount))
        except ValueError:
            pass
        expense.date = request.form.get("date", expense.date).strip()
        db.session.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for("transactions"))

    return render_template("edit_expense.html", expense=expense)


@app.route("/delete_expense/<int:id>")
def delete_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted successfully!", "info")
    return redirect(url_for("transactions"))


@app.route("/monthly_report")
def monthly_report():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    month = request.args.get("month", "").strip()

    incomes = Income.query.filter((Income.user_id == user_id) | (Income.user_id.is_(None))).all()
    expenses = Expense.query.filter((Expense.user_id == user_id) | (Expense.user_id.is_(None))).all()

    if month:
        # Check against MM or YYYY-MM
        incomes = [
            inc for inc in incomes
            if (len(inc.date) >= 2 and inc.date[:2] == month)
            or (f"-{month}-" in inc.date)
            or inc.date.endswith(f"-{month}")
        ]
        expenses = [
            exp for exp in expenses
            if (len(exp.date) >= 2 and exp.date[:2] == month)
            or (f"-{month}-" in exp.date)
            or exp.date.endswith(f"-{month}")
        ]

    total_income = sum(inc.amount for inc in incomes)
    total_expense = sum(exp.amount for exp in expenses)
    balance = total_income - total_expense

    return render_template(
        "monthly_report.html",
        incomes=incomes,
        expenses=expenses,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        balance=round(balance, 2),
        month=month
    )


@app.route("/download_report")
def download_report():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    incomes = Income.query.filter((Income.user_id == user_id) | (Income.user_id.is_(None))).all()
    expenses = Expense.query.filter((Expense.user_id == user_id) | (Expense.user_id.is_(None))).all()

    total_income = sum(i.amount for i in incomes)
    total_expense = sum(e.amount for e in expenses)
    balance = total_income - total_expense

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    # Document Header
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(180, 760, "Personal Finance Report")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(180, 742, "Cloud-Native DevOps Personal Finance Application")

    # Financial Summary Box
    pdf.setStrokeColorRGB(0.2, 0.4, 0.6)
    pdf.rect(45, 650, 520, 75, fill=0)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(55, 705, f"Total Income : INR {total_income:.2f}")
    pdf.drawString(55, 685, f"Total Expense: INR {total_expense:.2f}")
    pdf.drawString(55, 665, f"Balance      : INR {balance:.2f}")

    # Income Section
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, 620, "Income Records")
    pdf.setLineWidth(1)
    pdf.line(50, 615, 560, 615)

    y = 595
    pdf.setFont("Helvetica", 10)
    for income in incomes:
        pdf.drawString(55, y, f"• {income.source}  -  INR {income.amount:.2f}  -  {income.date}")
        y -= 20
        if y < 100:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 740

    # Expense Section
    y -= 15
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Expense Records")
    pdf.line(50, y - 5, 560, y - 5)
    y -= 25

    pdf.setFont("Helvetica", 10)
    for expense in expenses:
        pdf.drawString(55, y, f"• {expense.category}  -  INR {expense.amount:.2f}  -  {expense.date}")
        y -= 20
        if y < 100:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 740

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Finance_Report.pdf",
        mimetype="application/pdf"
    )


@app.route("/set_budget", methods=["GET", "POST"])
def set_budget():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    budget = Budget.query.filter((Budget.user_id == user_id) | (Budget.user_id.is_(None))).first()

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            flash("Please enter a valid numeric budget.", "danger")
            return redirect(url_for("set_budget"))

        if budget:
            budget.amount = amount
            budget.user_id = user_id
        else:
            budget = Budget(user_id=user_id, amount=amount)
            db.session.add(budget)

        db.session.commit()
        flash("Monthly budget successfully updated!", "success")
        return redirect(url_for("dashboard"))

    return render_template("set_budget.html", budget=budget)


# Create tables on application start
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
