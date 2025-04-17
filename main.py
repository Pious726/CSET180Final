from flask import Flask, render_template, request, url_for, redirect
from sqlalchemy import create_engine, text
import bcrypt
 
app = Flask(__name__)
conn_str = "mysql://root:cset155@localhost/shop"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

@app.route('/')
def loadapp():
    return render_template('index.html')

@app.route('/register', methods=["POST"])
def signup():
    try:
        conn.execute(text('''
            INSERT INTO Users (name, email_address, username, password, account_type) 
            VALUES (:Name, :Email, :Username, :Password, :account_type)
        '''), request.form)

        conn.commit()
        return render_template('login.html', success="Successful", error=None)
    except:
        return render_template('index.html', error="Failed", success=None)
    

@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("Email")
        password = request.form.get("Password")

        stored_password = conn.execute(text('Select Password From users Where email_address = :email'), {'email': email}).scalar()

        if stored_password:
            if password == stored_password:
                conn.execute(text("Update users Set IsLoggedIN = 1 Where email_address = :email"), {"email": email})
                conn.commit()
                return redirect(url_for('loadhome'))  
            else:
                return render_template('login.html', error='Incorrect email or password.', success=None)
        else:
            return render_template('login.html', error='Account not found.', success=None)

    return render_template('login.html') 

@app.route('/logout')
def logout():
    conn.execute(text('Update users Set IsLoggedIn = 0 Where IsLoggedIn = 1'))
    conn.commit()
    return redirect(url_for('login'))

@app.route('/home.html')
def loadhome():
    return render_template('home.html')

@app.route('/shop.html', methods=['GET'])
def loadshop():
    products = conn.execute(text('select * from products natural join Product_Images')).fetchall()
    return render_template('shop.html', products=products)

@app.route('/accounts.html', methods=['GET'])
def getaccount():
    account = conn.execute(text('select * from users where IsLoggedIn = 1')).fetchall()
    return render_template('accounts.html', account=account)

@app.route('/orders.html', methods=['GET'])
def getorders():
    customerID = conn.execute(text('select customerID from customers natural join users where IsLoggedIn = 1')).scalar()
    orders = conn.execute(text(f'select * from orders where customerID = {customerID}')).fetchall()
    return render_template('orders.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)