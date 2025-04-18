from flask import Flask, render_template, request, session, url_for, redirect
from sqlalchemy import create_engine, text
import bcrypt
 
app = Flask(__name__)
conn_str = "mysql://root:cset155@localhost/shop"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

app.secret_key = 's3cr3t_k3y_@420pizzaTaco'  # Needed to use sessions


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

        user = conn.execute(
            text('SELECT userID, password, account_type FROM users WHERE email_address = :email'),
            {'email': email}
        ).fetchone()

        if user:
            stored_password = user[1]
            if password == stored_password:
        
                session['user_id'] = user[0]
                session['email'] = email
                session['account_type'] = user[2]

                conn.execute(
                    text("UPDATE users SET IsLoggedIN = 1 WHERE email_address = :email"),
                    {"email": email}
                )
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

@app.route('/vendor_products')
def vendor_products():
    vendor_id = session.get('user_id')  # Get the vendor's user ID from the session

    # Query the database to fetch products created by this vendor
    products = conn.execute(
        text('SELECT * FROM products WHERE vendorID = :vendor_id'),
        {'vendor_id': vendor_id}
    ).fetchall()  # Fetch all products for the current vendor

    # Render the template and pass the products data
    return render_template('vendorproducts.html', products=products)



if __name__ == '__main__':
    app.run(debug=True)