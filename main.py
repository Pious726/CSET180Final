from flask import Flask, render_template, request, url_for, redirect
from sqlalchemy import create_engine, text
import bcrypt
 
app = Flask(__name__)
conn_str = "mysql://root:cset155@localhost/shop"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

@app.route('/')
def loadapp():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)