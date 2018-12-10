import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
import plotly as py
import plotly.graph_objs as go
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

    # The 'total' variable keeps track of networth and displays at the bottom.
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

    # Pass list of accounts to populate drop-down menu for removing accounts
    return render_template("accounts.html", accounts=accounts)


@app.route("/add", methods=["POST"])
@login_required
def add():
    """Adds account that was entered on the accounts page"""
    if not request.form.get('name'):
        return apology("Name cannot be empty")

    user_id = session['user_id']
    name = request.form.get('name')
    acctype = request.form.get('type')
    value = float(request.form.get('value'))

    if not request.form.get('value'):
        value = 0

    if acctype == 'Loan' or acctype == 'Credit':
        value = value * -1

    db.execute(
        'INSERT INTO "accounts" ("name","userid","value","type")' +
        'VALUES (:name, :user_id, :value, :acctype)', name=name, user_id=session['user_id'], value=value, acctype=acctype)

    newaccount = db.execute('SELECT * FROM accounts WHERE userid = :user_id AND name = :name', user_id=user_id, name=name)

    db.execute(
        'INSERT INTO "history" ("accountid","value","userid") ' +
        'VALUES (:accountid, :value, :user_id)', accountid=newaccount[0]['id'], value=value, user_id=user_id)
    return redirect("/accounts")


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Show history of transactions"""
    if request.method == "POST":
        user_id = session['user_id']
        history = db.execute("SELECT * FROM history WHERE userid=:user_id", user_id=user_id)
        for row in history:
            if request.form.get(str(row['id'])) == "on":
                db.execute("DELETE FROM history WHERE id=:accid", accid=row['id'])

        userhistory = db.execute(
            "SELECT history.date, accounts.name, history.value, history.id FROM history INNER JOIN accounts " +
            "ON history.accountid=accounts.id WHERE history.userid=:user_id ORDER BY date DESC", user_id=user_id)
        return render_template("history.html", userhistory=userhistory)

    else:
        user_id = session['user_id']
        userhistory = db.execute(
            "SELECT history.date, accounts.name, history.value, history.id FROM history INNER JOIN accounts " +
            "ON history.accountid=accounts.id WHERE history.userid=:user_id ORDER BY date DESC", user_id=user_id)
        return render_template("history.html", userhistory=userhistory)


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
                          username=request.form.get("username").lower())

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

        username = request.form.get("username").lower()
        for char in username:
            if not char.isalnum():
                return apology("Please only use letters and numbers for username")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        if len(rows) != 0:
            return apology("Username already taken", 400)

        name = request.form.get("username")
        password = request.form.get("password")
        passhash = generate_password_hash(password)
        realname = request.form.get("name")

        db.execute("INSERT INTO users (username, hash, realname) VALUES (:name, :passhash, :realname)", name=name, passhash=passhash, realname=realname)

        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)

    else:
        return render_template("register.html")


@app.route("/remove", methods=["POST"])
@login_required
def remove():
    """Remove account from database and clear associated history"""
    account = request.form.get('account')
    rows = db.execute('SELECT * FROM accounts WHERE userid = :userid AND name = :account', userid=session['user_id'], account=account)
    accountid = rows[0]['id']
    db.execute('DELETE FROM "accounts" WHERE userid = :userid AND name = :account', userid=session['user_id'], account=account)
    db.execute('DELETE FROM "history" WHERE accountid = :accountid', accountid=accountid)

    # Redirect user back to the accounts page.
    return redirect("/accounts")


@app.route("/reports")
@login_required
def reports():
    """Generate a graph of account history using Plotly"""
    dates = []
    values = []
    data = []

    user_id = session['user_id']

    # Get all accounts that belong to the user
    accounts = db.execute("SELECT * FROM accounts WHERE userid=:user_id", user_id=user_id)

    # For each account, get the history associated with the account id
    for account in accounts:
        history = db.execute("SELECT * FROM history WHERE accountid=:accountid", accountid=account['id'])

        # For each row in the account's history, add the date and value to the data
        for row in history:
            dates.append(row['date'])
            values.append(row['value'])

        # Create a new trace with the data from the account
        newtrace = go.Scatter(
            x = dates,
            y = values,
            name = account['name']
        )

        # Clear data for next account
        dates.clear()
        values.clear()

        # Add the new trace to the list of traces
        data.append(newtrace)

    # Add networth trace
    networth = db.execute("SELECT * FROM networth WHERE userid=:user_id", user_id=user_id)
    for row in networth:
        dates.append(row['date'])
        values.append(row['value'])

    newtrace = go.Scatter(
        x = dates,
        y = values,
        name = "Net Worth"
    )

    data.append(newtrace)

    # Generate file name and store in the templates directory
    file = "templates/accounts-" + str(user_id) + ".html"

    # Gives parameters for the layout of the graph
    layout = go.Layout(
        title='Account Values Over Time',
        xaxis=dict(
            title='Date',
            titlefont=dict(
                family='Arial, sans-serif',
                size=18,
                color='#7f7f7f'
            )
        ),
        yaxis=dict(
            title='Value ($)',
            titlefont=dict(
                family='Arial, sans-serif',
                size=18,
                color='#7f7f7f'
            )
        )
    )

    # Send data to Plotly
    fig = go.Figure(data=data, layout=layout)
    py.offline.plot(fig, filename=file, auto_open=False)

    return render_template("report.html")


@app.route("/plot")
@login_required
def plot():
    """When called, this fuction returns the html page generated by Plotly"""
    user_id = session['user_id']
    graphname = "accounts-" + str(user_id) + ".html"
    return render_template(graphname)



@app.route("/update", methods=["GET", "POST"])
@login_required
def update():
    """Updates the values of the accounts"""

    # User submitted values with POST
    if request.method == "POST":
        user_id = session['user_id']
        accounts = db.execute("SELECT * FROM accounts WHERE userid = :user_id", user_id=user_id)
        networth = 0
        for account in accounts:

            # If user did not enter a new value for an account, reuse the previous value
            if not request.form.get(account['name']):
                newvalue = account['value']
            else:
                newvalue = float(request.form.get(account['name']))
                if account['type'] == 'Credit' or account['type'] == 'Loan':
                    newvalue = newvalue * -1
                print("value for " + account['name'] + " is")

            print(newvalue)
            networth += float(newvalue)
            db.execute(
                'INSERT INTO "history" ("accountid","value","userid") VALUES (:accountid, :newvalue, :user_id)', accountid=account['id'], newvalue=newvalue, user_id=user_id)
            db.execute('UPDATE accounts SET value = :newvalue WHERE id = :accountid', newvalue=newvalue, accountid=account['id'])

        # Update networth for the current date
        db.execute('INSERT INTO "networth" ("userid","value") VALUES (:user_id, :networth)', user_id=user_id, networth=networth)

        # Send user back to the homepage
        return redirect("/")

    # User visited page by GET
    else:
        user_id = session['user_id']
        accounts = db.execute("SELECT * FROM accounts WHERE userid = :user_id", user_id=user_id)
        return render_template("update.html", accounts=accounts)



def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
