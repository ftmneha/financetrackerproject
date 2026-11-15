import pytest
from app import app, db
from models import User, Income, Expense, Budget


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_home_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"FinTrack Pro" in response.data


def test_register_user_success(client):
    response = client.post(
        "/register",
        data={
            "fullname": "Neha Fathima",
            "email": "neha@example.com",
            "password": "Password123!"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Registration successful" in response.data


def test_register_duplicate_email(client):
    client.post(
        "/register",
        data={"fullname": "First User", "email": "test@example.com", "password": "pass"},
        follow_redirects=True
    )
    # Second attempt with same email
    response = client.post(
        "/register",
        data={"fullname": "Second User", "email": "test@example.com", "password": "pass"},
        follow_redirects=True
    )
    assert b"Email already registered" in response.data


def test_login_success(client):
    client.post(
        "/register",
        data={"fullname": "Alice Smith", "email": "alice@example.com", "password": "secret"},
        follow_redirects=True
    )

    response = client.post(
        "/login",
        data={"email": "alice@example.com", "password": "secret"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Welcome back, Alice Smith" in response.data


def test_login_invalid_password(client):
    client.post(
        "/register",
        data={"fullname": "Bob", "email": "bob@example.com", "password": "validpassword"},
        follow_redirects=True
    )

    response = client.post(
        "/login",
        data={"email": "bob@example.com", "password": "wrongpassword"},
        follow_redirects=True
    )
    assert b"Invalid email or password" in response.data


def test_logout(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Tester"

    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been successfully logged out." in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=True)
    assert b"Please log in" in response.data


def test_dashboard_authenticated(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Test User" in response.data
    assert b"Chart.js" in response.data


def test_add_income(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    response = client.post(
        "/add_income",
        data={"source": "Salary", "amount": "50000", "date": "2026-11-01"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Income entry added successfully" in response.data

    with app.app_context():
        inc = Income.query.filter_by(source="Salary").first()
        assert inc is not None
        assert inc.amount == 50000.0


def test_add_expense(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    response = client.post(
        "/add_expense",
        data={"category": "Groceries", "amount": "4500", "date": "2026-11-05"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Expense entry added successfully" in response.data

    with app.app_context():
        exp = Expense.query.filter_by(category="Groceries").first()
        assert exp is not None
        assert exp.amount == 4500.0


def test_transactions_view_and_search(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    client.post("/add_income", data={"source": "Freelancing", "amount": "15000", "date": "2026-11-02"})
    client.post("/add_expense", data={"category": "Electricity", "amount": "2000", "date": "2026-11-03"})

    response = client.get("/transactions")
    assert response.status_code == 200
    assert b"Freelancing" in response.data
    assert b"Electricity" in response.data

    search_response = client.get("/transactions?search=Freelanc")
    assert b"Freelancing" in search_response.data


def test_edit_and_delete_transaction(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    client.post("/add_income", data={"source": "Bonus", "amount": "10000", "date": "2026-11-10"})

    with app.app_context():
        inc = Income.query.filter_by(source="Bonus").first()
        inc_id = inc.id

    # Edit
    edit_response = client.post(
        f"/edit_income/{inc_id}",
        data={"source": "Holiday Bonus", "amount": "12000", "date": "2026-11-10"},
        follow_redirects=True
    )
    assert edit_response.status_code == 200
    assert b"Income updated successfully" in edit_response.data

    # Delete
    del_response = client.get(f"/delete_income/{inc_id}", follow_redirects=True)
    assert del_response.status_code == 200
    assert b"Income deleted successfully" in del_response.data


def test_set_budget(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    response = client.post(
        "/set_budget",
        data={"amount": "30000"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Monthly budget successfully updated" in response.data

    with app.app_context():
        budget = Budget.query.first()
        assert budget is not None
        assert budget.amount == 30000.0


def test_monthly_report_filter(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    client.post("/add_income", data={"source": "Dividend", "amount": "2500", "date": "11-04-2026"})
    response = client.get("/monthly_report?month=11")
    assert response.status_code == 200
    assert b"Dividend" in response.data


def test_download_report_pdf(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    client.post("/add_income", data={"source": "Stipend", "amount": "8000", "date": "2026-11-01"})
    client.post("/add_expense", data={"category": "Books", "amount": "1200", "date": "2026-11-02"})

    response = client.get("/download_report")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.headers["Content-Disposition"].startswith("attachment")


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "personal-finance-tracker"


def test_metrics_endpoint(client):
    # Make a few calls to populate metrics
    client.get("/")
    client.get("/health")

    response = client.get("/metrics")
    assert response.status_code == 200
    data_str = response.data.decode("utf-8")
    assert "fintrack_http_requests_total" in data_str
    assert "fintrack_registered_users_total" in data_str


def test_chart_data_api(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"

    client.post("/add_income", data={"source": "Salary", "amount": "60000", "date": "2026-11-01"})
    client.post("/add_expense", data={"category": "Rent", "amount": "15000", "date": "2026-11-02"})

    response = client.get("/api/chart-data")
    assert response.status_code == 200
    data = response.get_json()
    assert data["summary"]["income"] == 60000.0
    assert data["summary"]["expense"] == 15000.0
    assert "Rent" in data["expense_categories"]["labels"]
