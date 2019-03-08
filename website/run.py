#!/usr/bin/env python
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def welcomePage():
    return render_template("welcome.html")

@app.route("/status")
def statusPage():
    return render_template("status.html")

@app.route("/submit")
def submitPage():
    return render_template("submit.html")

@app.route("/help")
def helpPage():
    return render_template("help.html")

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)