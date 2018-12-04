import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")


@app.route("/")
@login_required
def index():
    """Show values of accounts"""
    user_id = session['user_id']
    accounts = db.execute("SELECT * FROM accounts WHERE userid = :user_id ORDER BY value DESC", user_id=user_id)
    user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=user_id)
    total = 0
    for row in accounts:
        total += row['value']
    return render_template("index.html", accounts=accounts, user=user, total=total)


@app.route("/accounts")
@login_required
def accounts():
    """Shows page to add, remove, or change accounts"""
    user_id = session['user_id']
    accounts = db.execute("SELECT * FROM accounts WHERE userid = :user_id", user_id=user_id)
    total = 0
    for row in accounts:
        total += row['value']
    return render_template("accounts.html", accounts=accounts)


@app.route("/add", methods=["POST"])
@login_required
def add():
    """Adds account that was entered on the accounts page"""
    user_id = session['user_id']
    name = request.form.get('name')
    acctype = request.form.get('type')
    value = request.form.get('value')
    db.execute(
        'INSERT INTO "accounts" ("name","userid","value","type")' +
        'VALUES (:name, :user_id, :value, :acctype)', name=name, user_id=session['user_id'], value=value, acctype=acctype)

    newaccount = db.execute('SELECT * FROM accounts WHERE userid = :user_id AND name = :name', user_id=user_id, name=name)

    db.execute('INSERT INTO "history" ("accountid","value") VALUES (:accountid, :value)', accountid=newaccount[0]['id'], value=value)
    return redirect("/accounts")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session['user_id']
    rows = db.execute("SELECT * FROM history WHERE userID = :user_id", user_id=user_id)
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif not request.form.get("confirmation"):
            return apology("must re-enter password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        if len(rows) != 0:
            return apology("Username already taken", 400)

        name = request.form.get("username")
        password = request.form.get("password")
        passhash = generate_password_hash(password)

        db.execute("INSERT INTO users (username, hash) VALUES (:name, :passhash)", name=name, passhash=passhash)

        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)

    else:
        return render_template("register.html")


@app.route("/remove", methods=["POST"])
@login_required
def remove():
    account = request.form.get('account')
    db.execute('DELETE FROM "accounts" WHERE userid = :userid AND name = :account', userid=session['user_id'], account=account)
    return redirect("/accounts")

def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
