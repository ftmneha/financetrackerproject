from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
# Create Flask application
app = Flask(__name__)
app.secret_key = "mysecretkey123"

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)


# =====================================
# Database Models
# =====================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), nullable=False)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), nullable=False)


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)


# =====================================
# Routes
# =====================================

@app.route("/")
def home():
    return render_template("index.html")


# Register
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "<h2>Email already registered!</h2>"

        hashed_password = generate_password_hash(password)

        new_user = User(
            fullname=fullname,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return "<h2>Registration Successful!</h2>"

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["user_name"] = user.fullname

            return redirect(url_for("dashboard"))

        return "<h2>Invalid Email or Password!</h2>"

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    name = session["user_name"]

    total_income = db.session.query(db.func.sum(Income.amount)).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount)).scalar() or 0

    balance = total_income - total_expense

    budget = Budget.query.first()
    budget_amount = budget.amount if budget else 0
    remaining_budget = budget_amount - total_expense

    return render_template(
        "dashboard.html",
        name=name,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        budget_amount=budget_amount,
        remaining_budget=remaining_budget,
        chart_image="charts/income_expense.png",
        pie_chart="charts/expense_pie.png"
    )

# Add Income
@app.route("/add_income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        source = request.form["source"]
        amount = float(request.form["amount"])
        date = request.form["date"]

        income = Income(
            source=source,
            amount=amount,
            date=date
        )

        db.session.add(income)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_income.html")


# Add Expense
@app.route("/add_expense", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        category = request.form["category"]
        amount = float(request.form["amount"])
        date = request.form["date"]

        expense = Expense(
            category=category,
            amount=amount,
            date=date
        )

        db.session.add(expense)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_expense.html")


# Transactions
@app.route("/transactions")
def transactions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "")

    incomes = Income.query.filter(
        Income.source.contains(search)
    ).all()

    expenses = Expense.query.filter(
        Expense.category.contains(search)
    ).all()

    return render_template(
        "transactions.html",
        incomes=incomes,
        expenses=expenses,
        search=search
    )
# Logout
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))
# Edit Expense
@app.route("/edit_expense/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = Expense.query.get_or_404(id)

    if request.method == "POST":

        expense.category = request.form["category"]
        expense.amount = float(request.form["amount"])
        expense.date = request.form["date"]

        db.session.commit()

        return redirect(url_for("transactions"))

    return render_template(
        "edit_expense.html",
        expense=expense
    )
# Delete Income
@app.route("/delete_income/<int:id>")
def delete_income(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    income = Income.query.get_or_404(id)

    db.session.delete(income)
    db.session.commit()

    return redirect(url_for("transactions"))


# Delete Expense
# Edit Income
@app.route("/edit_income/<int:id>", methods=["GET", "POST"])
def edit_income(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    income = Income.query.get_or_404(id)

    if request.method == "POST":

        income.source = request.form["source"]
        income.amount = float(request.form["amount"])
        income.date = request.form["date"]

        db.session.commit()

        return redirect(url_for("transactions"))

    return render_template(
        "edit_income.html",
        income=income
    )
@app.route("/delete_expense/<int:id>")
def delete_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = Expense.query.get_or_404(id)

    db.session.delete(expense)
    db.session.commit()

    return redirect(url_for("transactions"))

# Monthly Report
@app.route("/monthly_report")
def monthly_report():

    if "user_id" not in session:
        return redirect(url_for("login"))

    month = request.args.get("month", "")

    incomes = Income.query.all()
    expenses = Expense.query.all()

    if month:
        incomes = [
            income for income in incomes
            if income.date[:2] == month
        ]

        expenses = [
            expense for expense in expenses
            if expense.date[:2] == month
        ]

    total_income = sum(income.amount for income in incomes)
    total_expense = sum(expense.amount for expense in expenses)
    balance = total_income - total_expense

    return render_template(
        "monthly_report.html",
        incomes=incomes,
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        month=month
    )
@app.route("/download_report")
def download_report():

    if "user_id" not in session:
        return redirect(url_for("login"))

    buffer = io.BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 770, "Personal Finance Report")

    total_income = db.session.query(db.func.sum(Income.amount)).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    balance = total_income - total_expense

    pdf.setFont("Helvetica", 12)

    pdf.drawString(50, 730, f"Total Income : ₹ {total_income}")
    pdf.drawString(50, 710, f"Total Expense: ₹ {total_expense}")
    pdf.drawString(50, 690, f"Balance      : ₹ {balance}")

    pdf.drawString(50, 650, "Income Records")

    y = 630

    for income in Income.query.all():

        pdf.drawString(
            50,
            y,
            f"{income.source} - ₹ {income.amount} - {income.date}"
        )

        y -= 20

        if y < 100:
            pdf.showPage()
            y = 750

    y -= 20

    pdf.drawString(50, y, "Expense Records")

    y -= 20

    for expense in Expense.query.all():

        pdf.drawString(
            50,
            y,
            f"{expense.category} - ₹ {expense.amount} - {expense.date}"
        )

        y -= 20

        if y < 100:
            pdf.showPage()
            y = 750

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

    budget = Budget.query.first()

    if request.method == "POST":

        amount = float(request.form["amount"])

        if budget:
            budget.amount = amount
        else:
            budget = Budget(amount=amount)
            db.session.add(budget)

        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template(
        "set_budget.html",
        budget=budget
    )
# =====================================
# Main Program
# =====================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)