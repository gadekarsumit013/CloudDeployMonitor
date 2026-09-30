from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import psutil
import subprocess
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Secret key for sessions
app.secret_key = os.getenv("SECRET_KEY")

# ==========================================
# MySQL Database Connection
# ==========================================

def get_db_connection():

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

    return connection

# ==========================================
# Docker Status
# ==========================================

def get_docker_status():

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return "RUNNING"

        return "STOPPED"

    except Exception:
        return "NOT AVAILABLE"


# ==========================================
# Home
# ==========================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ==========================================
# Register
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            return "All fields are required."

        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if email already exists
        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            connection.close()

            return "Email already registered. Please login."

        # Hash password
        hashed_password = generate_password_hash(password)

        # Insert user
        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (name, email, hashed_password)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================================
# Login
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        # Verify user
        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            return redirect(url_for("dashboard"))

        return "Invalid email or password."

    return render_template("login.html")


# ==========================================
# Dashboard
# ==========================================

@app.route("/dashboard")
def dashboard():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # --------------------------------------
    # System Monitoring
    # --------------------------------------

    cpu_usage = psutil.cpu_percent(interval=1)

    memory_usage = psutil.virtual_memory().percent

    docker_status = get_docker_status()

    server_status = "RUNNING"

    application_status = "ONLINE"


    # --------------------------------------
    # Database Connection
    # --------------------------------------

    connection = get_db_connection()

    cursor = connection.cursor(dictionary=True)


    # --------------------------------------
    # Latest Deployment
    # --------------------------------------

    cursor.execute(
        """
        SELECT version, status, deployment_time
        FROM deployments
        ORDER BY id DESC
        LIMIT 1
        """
    )

    deployment = cursor.fetchone()


    # --------------------------------------
    # Deployment History
    # --------------------------------------

    cursor.execute(
        """
        SELECT version, status, deployment_time
        FROM deployments
        ORDER BY id DESC
        """
    )

    deployment_history = cursor.fetchall()


    # --------------------------------------
    # Application Logs
    # --------------------------------------

    cursor.execute(
        """
        SELECT log_type, message, created_at
        FROM application_logs
        ORDER BY id DESC
        LIMIT 10
        """
    )

    application_logs = cursor.fetchall()


    # Close database connection
    cursor.close()
    connection.close()


    # --------------------------------------
    # Latest Deployment Information
    # --------------------------------------

    if deployment:

        deployment_version = deployment["version"]

        deployment_status = deployment["status"]

        deployment_time = deployment["deployment_time"].strftime(
            "%d-%m-%Y %H:%M"
        )

    else:

        deployment_version = "N/A"

        deployment_status = "NO DEPLOYMENT"

        deployment_time = "N/A"


    # --------------------------------------
    # Send Data to Dashboard
    # --------------------------------------

    return render_template(
        "dashboard.html",

        user_name=session.get("user_name"),

        application_status=application_status,

        server_status=server_status,

        cpu_usage=cpu_usage,

        memory_usage=memory_usage,

        docker_status=docker_status,

        deployment_version=deployment_version,

        deployment_status=deployment_status,

        deployment_time=deployment_time,

        deployment_history=deployment_history,

        application_logs=application_logs
    )


# ==========================================
# Logout
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ==========================================
# Run Application
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)