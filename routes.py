from flask import render_template, request, redirect, url_for
from app import app
from models import db, User, Income, Expense


# Home Page
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

        new_user = User(
            fullname=fullname,
            email=email,
            password=password
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

        user = User.query.filter_by(
            email=email,
            password=password
        ).first()

        if user:
            return redirect(url_for("dashboard", name=user.fullname))

        return "<h2>Invalid Email or Password!</h2>"

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
def dashboard():

    name = request.args.get("name")

    total_income = db.session.query(db.func.sum(Income.amount)).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount)).scalar() or 0

    balance = total_income - total_expense

    return render_template(
        "dashboard.html",
        name=name,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )


# Add Income
@app.route("/add_income", methods=["GET", "POST"])
def add_income():

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

    incomes = Income.query.all()
    expenses = Expense.query.all()

    return render_template(
        "transactions.html",
        incomes=incomes,
        expenses=expenses
    )