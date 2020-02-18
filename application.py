# API KEY export API_KEY=pk_1e5e405e8b9e4e3593c1cebbf004ce98
import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, lookupAV

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
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id = session["user_id"]

    user_Portfolio = db.execute("SELECT symbol, shares FROM Portfolios WHERE id = :id ", id=id)
    user_Cash = db.execute("SELECT cash FROM users WHERE id=:id", id=id)[0]['cash']
    totaled = usd(user_Cash)

    stock_owned = []
    for stock in user_Portfolio:
        dict = {}
        symbol = stock["symbol"]
        shares = stock["shares"]
        dict.update({"symbol": symbol})
        dict.update({"shares": shares})
        lookedup = lookup(symbol)
        dict.update({"name": lookedup["name"]})
        dict.update({"price": usd(lookedup["price"])})
        total_Price = lookedup["price"] * shares
        dict.update({"total": usd(total_Price)})
        stock_owned.append(dict)

    return render_template("index.html", stocks=stock_owned, totaled = totaled)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        #get quote using lookup function
        symbol_input = request.form.get("symbol")
        quote = lookup(symbol_input)
        shares = int((request.form.get("shares")))

        if not quote:
            return apology("Input stock does not exist", 403)

        if not shares:
            return apology("Please input number of shares", 403)

        name = quote["name"]
        price = quote["price"]
        symbol = quote["symbol"]
        id = session["user_id"]

        user_balance = db.execute("SELECT cash FROM users WHERE id = :id", id = id)
        # Turn Dicts to Float
        user_balance = user_balance[0]["cash"]

        transaction_amount = (shares * price)
        if user_balance >= transaction_amount: # checks user can afford
            user_balance = user_balance - transaction_amount
            # Update uer balance
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=user_balance, id=id)
            #Update Transaction History
            db.execute("INSERT INTO TransactionHistory (symbol, name, shares, price, id, transaction_amount) VALUES(:symbol, :name, :shares, :price, :id, :transaction_amount);", symbol=symbol, name=name, shares=shares, price=price, id=id, transaction_amount=transaction_amount)

            #Search if user already has some shares in portfolio
            list_shares = db.execute("SELECT shares FROM Portfolios WHERE id = :id AND symbol = :symbol", id=id, symbol=symbol)

            if list_shares:
                list_shares = int(list_shares[0]["shares"])
                totalshares = list_shares + shares
                db.execute("UPDATE Portfolios SET shares = :list_shares WHERE id = :id AND symbol =:symbol", list_shares=list_shares, id=id, symbol=symbol)
            else:
                db.execute("INSERT INTO Portfolios (symbol, shares, id) VALUES(:symbol, :shares, :id);", symbol=symbol, shares=shares, id=id)
            # Redirect user to home page
            return redirect("/")
        else:
            return apology("You have insufficient funds")
    else:
        return render_template("buy.html")

@app.route("/graph", methods=["GET", "POST"])
@login_required
def graph():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)
        stockLink = lookupAV(request.form.get("symbol"))
        if not stockLink:
            return apology("Input stock does not exist", 403)
        print(stockLink)
        return render_template("graph.html", stockLink=stockLink)
    else:
        return render_template("graph.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    id = session["user_id"]

    user_History = db.execute("SELECT symbol, shares, price, transaction_time FROM TransactionHistory WHERE id = :id ", id=id)
    print(user_History[0])
    stock_owned = []
    for stock in user_History:
        dict = {}
        symbol = stock["symbol"]
        shares = stock["shares"]
        price = stock["price"]
        transaction_time = stock["transaction_time"]
        dict.update({"symbol": symbol})
        dict.update({"shares": shares})
        dict.update({"price": price})
        dict.update({"transacted":transaction_time})
        stock_owned.append(dict)

    return render_template("history.html", stocks=stock_owned)


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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)
        stock = lookup(request.form.get("symbol"))

        if not stock:
            return apology("Input stock does not exist", 403)
        return render_template("quoted.html", name=stock["name"], symbol=stock["symbol"], price=stock["price"])
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure name was submitted
        if not request.form.get("name"):
            return apology("must provide name", 403)

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password do not match", 403)

        # Query database for username & insert user if no existing clash
        checkUser = db.execute("SELECT * FROM users WHERE username = :username",username=request.form.get("username"))

        if len(checkUser) >= 1:
            return apology("username exists in server", 403)

        if len(checkUser) == 0:
            rows = db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username=request.form.get("username"), password=generate_password_hash(request.form.get("password")))
            # Redirect user to home page
            return render_template("login.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

    return apology("TODO")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        #get quote using lookup function
        symbol_input = request.form.get("symbol")
        quote = lookup(symbol_input)
        sellShares = int((request.form.get("shares")))

        name = quote["name"]
        price = quote["price"]
        symbol = quote["symbol"]
        id = session["user_id"]

        user_balance = db.execute("SELECT cash FROM users WHERE id = :id", id = id)
        # Turn Dicts to Float
        user_balance = user_balance[0]["cash"]

        transaction_amount = (sellShares * price)
        #Checks if user have enough number of shares
        list_shares = db.execute("SELECT shares FROM Portfolios WHERE id = :id AND symbol = :symbol", id=id, symbol=symbol)
        existingShares = int(list_shares[0]["shares"])
        user_balance = user_balance + transaction_amount

        if existingShares >= sellShares:
            remainingShares = existingShares - sellShares
            db.execute("UPDATE Portfolios SET shares =:remainingShares WHERE id = :id AND symbol = :symbol", remainingShares=remainingShares, id=id, symbol=symbol)
            db.execute("INSERT INTO TransactionHistory (symbol, name, shares, price, id, transaction_amount) VALUES(:symbol, :name, :shares, :price, :id, :transaction_amount)", symbol=symbol, name=name, shares=sellShares, price=price, id=id, transaction_amount=transaction_amount)
            db.execute("UPDATE users SET cash=:user_balance WHERE id = :id", user_balance=user_balance, id=id)
            return redirect("/")
        else:
            return apology("You have insufficient shares")

    else:
        """Check Portfolio & send symbol to page"""
        id = session["user_id"]

        user_Portfolio = db.execute("SELECT symbol, shares FROM Portfolios WHERE id = :id ", id=id)

        stock_owned = []
        for stock in user_Portfolio:
            dict = {}
            symbol = stock["symbol"]
            dict.update({"symbol": symbol})
            lookedup = lookup(symbol)
            stock_owned.append(dict)

        return render_template("sell.html", stocks=stock_owned)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
