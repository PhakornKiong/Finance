import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = "pk_1e5e405e8b9e4e3593c1cebbf004ce98"
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def lookupAV(symbol):
    """Lookup in AlphaVantage."""
    # Contact API
    try:
        api_keyAV="ZTEQABT0PBHNCA7W"
        response = requests.get(f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={urllib.parse.quote_plus(symbol)}&outputsize=full&apikey={api_keyAV}")
        response.raise_for_status()
        print(f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={urllib.parse.quote_plus(symbol)}&outputsize=full&apikey={api_keyAV}")
    except requests.RequestException:
        return None

    #Send Link to parse in javascript
    return f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={urllib.parse.quote_plus(symbol)}&outputsize=full&apikey={api_keyAV}"
