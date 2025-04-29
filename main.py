from flask import Flask, render_template, request, session, url_for, redirect
from sqlalchemy import create_engine, text
import bcrypt
 
app = Flask(__name__)
conn_str = "mysql://root:cset155@localhost/shop"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()
app.secret_key = 's3cr3t_k3y_@420pizzaTaco'


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
    
@app.route('/login.html', methods=["GET"])
def getlogins():
    conn.execute(text('update users set IsLoggedIn = 0 where IsLoggedIn = 1'))
    conn.commit()
    return render_template('login.html')

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
    products = conn.execute(text('select * from products natural join Product_Images')).fetchall()
    return render_template('home.html', products=products)

@app.route('/shop.html', methods=['GET'])
def loadshop():
    categories = request.args.getlist('category')
    colors = request.args.getlist('color')
    sizes = request.args.getlist('size')
    availability = request.args.getlist('availability')

    query = '''select * from products natural join Product_Images'''
    params={}

    if categories:
        query += " and Category in :categories"
        params['categories'] = tuple(categories)
    if colors:
        query += " and Color in :colors"
        params['colors'] = tuple(colors)
    if sizes:
        query += " and Sizes in :sizes"
        params['sizes'] = tuple(sizes)
    if availability:
        if "In Stock" in availability and "Out of Stock" not in availability:
            query += " and stock > 0"
        elif "Out of Stock" in availability and "In Stock" not in availability:
            query += " and stock <= 0"

    products = conn.execute(text(query), params).fetchall()

    product_sizes = [row[0] for row in conn.execute(text('select distinct Sizes from Product_Sizes')).fetchall()]
    product_colors = [row[0] for row in conn.execute(text('select distinct Color from Product_Color')).fetchall()]

    return render_template('shop.html', products=products, product_sizes=product_sizes, product_colors=product_colors)

@app.route('/shop.html', methods=['POST'])
def saveiteminfo():
    session['itemID'] = request.form.get('id')
    session['itemName'] = request.form.get('name')
    session['price'] = request.form.get('price')
    session['itemDesc'] = request.form.get('description')
    session['itemImage'] = request.form.get('image')
    return redirect(url_for('loaditem'))

@app.route('/item.html')
def loaditem():
    return render_template('item.html')

@app.route('/item.html', methods=['POST'])
def addtocart():
        try:
            customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1;')).scalar()
            cartID = conn.execute(text(f'select cartID from cart where customerID = {customerID}')).scalar()
            productID = session.get('itemID')
            conn.execute(text(f'insert into Cart_Items (cartID, productID) values ({cartID}, {productID})'))
            conn.commit()
            return render_template('item.html', success="Item added to cart successfully.", error=None)
        except:
            return render_template('item.html', success=None, error="Error adding item to cart.")

@app.route('/cart.html')
def getcartitems():
    totalPrice = 0
    customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1')).scalar()
    cartID = conn.execute(text(f'select cartID from cart where customerID = {customerID}')).scalar()
    cartItems = list(conn.execute(text(f'select * from Cart_Items natural join products where cartID = {cartID}')))
    totalPrice = sum(item[9] * item[2] for item in cartItems)
    return render_template('cart.html', cartItems=cartItems, totalPrice=totalPrice)

@app.route('/cart.html', methods=['POST'])
def removeitem():
    customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1;')).scalar()
    cartID = conn.execute(text(f'select cartID from cart where customerID = {customerID}')).scalar()
    productID = request.form.get('id')
    conn.execute(text(f'delete from Cart_Items where productID = {productID} and cartID = {cartID}'))
    conn.commit()
    return redirect(url_for('getcartitems'))

@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    new_quantity = request.form.get('quantity')
    customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1;')).scalar()
    cartID = conn.execute(text(f'select cartID from cart where customerID = {customerID}')).scalar()
    productID = request.form.get('id')
    conn.execute(text(f'update Cart_Items set Quantity = {new_quantity} where cartID = {cartID} and productID = {productID}'))
    conn.commit()
    return redirect(url_for('getcartitems'))

@app.route('/checkout.html')
def loadcheckout():
    return render_template('checkout.html')

@app.route('/accounts.html', methods=['GET'])
def getaccount():
    account = conn.execute(text('select * from users where IsLoggedIn = 1')).fetchone()
    return render_template('accounts.html', account=account)

@app.route('/orders.html', methods=['GET'])
def getorders():
    customerID = conn.execute(text('select customerID from customer natural join users where IsLoggedIn = 1')).scalar()
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