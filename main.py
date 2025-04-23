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
    user_id = session.get('user_id')  # Get the user's ID from session

    if not user_id:
        return redirect(url_for('login'))

    # Get the actual vendorID from the vendor table
    vendor_id = conn.execute(
        text('SELECT vendorID FROM vendor WHERE userID = :user_id'),
        {'user_id': user_id}
    ).scalar()

    if not vendor_id:
        return "You are not registered as a vendor."

    # Fetch products using the correct vendorID
    products = conn.execute(
        text('SELECT * FROM products WHERE vendorID = :vendor_id'),
        {'vendor_id': vendor_id}
    ).fetchall()

    return render_template('vendorproducts.html', products=products)
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if request.method == 'POST':
        form = request.form

        # Update main product info
        conn.execute(text("""
            UPDATE products
            SET Title = :title,
                Description = :description,
                Warranty = :warranty,
                Inventory = :inventory,
                Original_Price = :original_price,
                Discount_Price = :discount_price
            WHERE ProductID = :product_id
        """), {
            'title': form.get('title'),
            'description': form.get('description'),
            'warranty': form.get('warranty'),
            'inventory': form.get('inventory'),
            'original_price': form.get('original_price'),
            'discount_price': form.get('discount_price'),
            'product_id': product_id
        })

       
        if form.get('new_size'):
            conn.execute(text("INSERT INTO product_sizes (ProductID, Size) VALUES (:product_id, :size)"),
                         {'product_id': product_id, 'size': form.get('new_size')})

        if form.get('new_color'):
            conn.execute(text("INSERT INTO product_color (ProductID, Color) VALUES (:product_id, :color)"),
                         {'product_id': product_id, 'color': form.get('new_color')})

      
        if form.get('new_image'):
            conn.execute(text("INSERT INTO product_images (ProductID, Images) VALUES (:product_id, :image)"),
                         {'product_id': product_id, 'image': form.get('new_image')})

        conn.commit()
        return redirect(url_for('vendor_products'))
        

    
    product = conn.execute(
        text("SELECT * FROM products WHERE ProductID = :product_id"),
        {'product_id': product_id}
    ).fetchone()

    return render_template('editproduct.html', product=product)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        try:
            form = request.form
            user_id = session.get('user_id')
            vendor_id = conn.execute(
                text('SELECT vendorID FROM vendor WHERE userID = :user_id'),
                {'user_id': user_id}
            ).scalar()

            conn.execute(text("""
                Insert Into products (VendorID, Title, Description, Warranty, Inventory, Original_Price, Discount_Price)
                Values (:vendor_id, :title, :description, :warranty, :inventory, :original_price, :discount_price)
            """), {
                'vendor_id': vendor_id,
                'title': form.get('title'),
                'description': form.get('description'),
                'warranty': form.get('warranty'),
                'inventory': form.get('inventory'),
                'original_price': form.get('original_price'),
                'discount_price': form.get('discount_price')
            })

            product_id = conn.execute(text("Select Last_Insert_ID()")).scalar()

            if form.get('new_size'):
                conn.execute(text("Insert Into product_sizes (ProductID, Sizes) Values (:product_id, :size)"),
                             {'product_id': product_id, 'size': form.get('new_size')})

            if form.get('new_color'):
                conn.execute(text("Insert Into product_color (ProductID, Color) Values (:product_id, :color)"),
                             {'product_id': product_id, 'color': form.get('new_color')})

            if form.get('new_image'):
                conn.execute(text("Insert Into product_images (ProductID, Images) Values (:product_id, :image)"),
                             {'product_id': product_id, 'image': form.get('new_image')})

            conn.commit()
            return redirect(url_for('vendor_products'))
        except:
            conn.rollback()
            return "Something went wrong while adding your product."

    return render_template('addproduct.html')




        


if __name__ == '__main__':
    app.run(debug=True)