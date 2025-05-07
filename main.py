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

    query = 'select * from products natural join Product_Images'

    if categories:
        query += f" and Category in {categories}"

    if colors:
        query += f" and Color in {colors}"

    if sizes:
        query += f" and Sizes in {sizes}"

    if availability:
        if "In Stock" in availability and "Out of Stock" not in availability:
            query += " and stock > 0"
        elif "Out of Stock" in availability and "In Stock" not in availability:
            query += " and stock <= 0"

    products = list(conn.execute(text(query)))

    product_categories = [row[0] for row in conn.execute(text('select distinct Category from Product_Categories')).fetchall()]

    product_sizes = [row[0] for row in conn.execute(text('select distinct Sizes from Product_Sizes')).fetchall()]
    product_colors = [row[0] for row in conn.execute(text('select distinct Color from Product_Color')).fetchall()]

    return render_template('shop.html', products=products, product_sizes=product_sizes, product_colors=product_colors, product_categories=product_categories)

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
    itemID = session.get('itemID')
    query = f"select * from reviews natural join customer natural join users where productID = {itemID}"
    filterRating = request.args.get('filterRating')
    sortBy = request.args.get('sortBy')

    if filterRating:
        query += f" and Rating = {filterRating}"

    if sortBy == "date_desc":
        query += " order by Date desc"
    elif sortBy == "date_asc":
        query += " order by Date asc"
    elif sortBy == "rating_desc":
        query += " order by Rating desc"
    elif sortBy == "rating_asc":
        query += " order by Rating asc"
    else:
        query += " order by Date desc"

    reviewList = list(conn.execute(text(query)))

    return render_template('item.html', reviewList=reviewList)

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
    totalPrice = round(sum(item[9] * item[2] for item in cartItems), 2)
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

@app.route('/checkout.html', methods=['POST'])
def placeorder():
    customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1;')).scalar()
    cartID = conn.execute(text(f'select cartID from cart where customerID = {customerID}')).scalar()
    cartItems = list(conn.execute(text(f'select * from Cart_Items natural join products where cartID = {cartID}')))
    totalPrice = round(sum(item[9] * item[2] for item in cartItems), 2)

    conn.execute(text(f'insert into orders (customerID, OrderDate, TotalPrice, OrderStatus) values ({customerID}, CURDATE(),{totalPrice}, "Pending")'))
    orderID = conn.execute(text('select LAST_INSERT_ID()')).scalar()

    for item in cartItems:
        conn.execute(text(f'insert into OrderItems (orderID, productID, Quantity) values ({orderID}, {item.productID}, {item.Quantity})'))

    conn.execute(text(f'delete from Cart_Items where cartID = {cartID}'))
    conn.commit()

    return redirect(url_for('orderthanks'))

@app.route('/thanks.html')
def orderthanks():
    return render_template('thanks.html')

@app.route('/reviews.html')
def loadreviews():
    orderID = session.get('orderID')
    orderItems = conn.execute(text(f'select * from OrderItems natural join products where orderID = {orderID}'))
    return render_template('reviews.html', orderItems=orderItems)

@app.route('/reviews.html', methods=['POST'])
def createreview():
    itemName = request.form.get('itemName')
    rating = request.form.get('rating')
    itemImage = request.form.get('itemImage')
    ratingDesc = request.form.get('desc')
    ratingTitle = request.form.get('ratingTitle')
    customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1;')).scalar()
    productID = conn.execute(text(f'select productID from products where Title = :title'), {"title": itemName}).scalar()
    print(request.form)
    conn.execute(text('''
        insert into reviews 
        (customerID, productID, itemName, ratingTitle, Rating, Description, Image, Date) 
        values (:customerID, :productID, :itemName, :ratingTitle, :Rating, :Description, :Image, CURDATE())
    '''), {
        'customerID': customerID,
        'productID': productID,
        'itemName': itemName,
        'ratingTitle': ratingTitle,
        'Rating': rating,
        'Description': ratingDesc,
        'Image': itemImage
    })
    conn.commit()

    return render_template('reviews.html')

@app.route('/accounts.html', methods=['GET'])
def getaccount():
    account = conn.execute(text('select * from users where IsLoggedIn = 1')).fetchone()
    return render_template('accounts.html', account=account)

@app.route('/orders.html', methods=['GET'])
def getorders():
    customerID = conn.execute(text('select customerID from customer natural join users where IsLoggedIn = 1')).scalar()
    orders = conn.execute(text(f'select * from orders where customerID = {customerID}')).fetchall()
    return render_template('orders.html', orders=orders)

@app.route('/orders.html/reviews', methods=['POST'])
def toreviews():
    session['orderID'] = request.form.get('orderID')
    return redirect(url_for('loadreviews'))

@app.route('/all_products')
def all_products():
    
    user_id = session.get('user_id')
    account_type = session.get('account_type')

    if not user_id or account_type != 'admin':
        return redirect(url_for('login'))
    
    products = conn.execute(text('select * from products')).fetchall()

    return render_template('all_products.html', products=products)

@app.route('/vendor_products')
def vendor_products():
    user_id = session.get('user_id') 

    if not user_id:
        return redirect(url_for('login'))

    vendor_id = conn.execute(
        text('SELECT vendorID FROM vendor WHERE userID = :user_id'),
        {'user_id': user_id}
    ).scalar()

    if not vendor_id:
        return "You are not registered as a vendor."

    products = conn.execute(
        text('SELECT * FROM products WHERE vendorID = :vendor_id'),
        {'vendor_id': vendor_id}
    ).fetchall()

    return render_template('vendorproducts.html', products=products)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    user_id = session.get('user_id')
    account_type = session.get('account_type')

    if request.method == 'POST':
        form = request.form

        conn.execute(text("""
            update products
            set Title = :title,
                Description = :description,
                Warranty = :warranty,
                Inventory = :inventory,
                Original_Price = :original_price,
                Discount_Price = :discount_price
            where ProductID = :product_id
        """), {
            'title': form.get('title'),
            'description': form.get('description'),
            'warranty': form.get('warranty'),
            'inventory': form.get('inventory'),
            'original_price': form.get('original_price'),
            'discount_price': form.get('discount_price'),
            'product_id': product_id
        })

        new_size = form.get('new_size')
        if new_size:
            conn.execute(text("""
                insert into product_sizes (ProductID, Sizes)
                values (:product_id, :size)
            """), {'product_id': product_id, 'size': new_size})

        new_color = form.get('new_color')
        if new_color:
            conn.execute(text("""
                insert into product_color (ProductID, Color)
                values (:product_id, :color)
            """), {'product_id': product_id, 'color': new_color})

      
        new_image = form.get('new_image')
        if new_image:
            conn.execute(text("""
                insert into product_images (ProductID, Images)
                values (:product_id, :image)
            """), {'product_id': product_id, 'image': new_image})

       
        conn.commit()

        if account_type == 'admin':  
            return redirect(url_for('all_products'))
        else:
            return redirect(url_for('vendor_products'))

    
    if account_type == 'admin':  
        product = conn.execute(
            text("select * from products where ProductID = :product_id"),
            {'product_id': product_id}
        ).fetchone()
    else:
        vendor_id = conn.execute(
            text("select vendorID from vendor where userID = :user_id"),
            {'user_id': user_id}
        ).scalar()

        product = conn.execute(
            text("select * from products where ProductID = :product_id and vendorID = :vendor_id"),
            {'product_id': product_id, 'vendor_id': vendor_id}
        ).fetchone()

    if not product:
        return "Product not found", 404

    sizes = conn.execute(
        text("select Sizes from product_sizes where ProductID = :product_id"),
        {'product_id': product_id}
    ).fetchall()

    colors = conn.execute(
        text("select Color from product_color where ProductID = :product_id"),
        {'product_id': product_id}
    ).fetchall()

    images = conn.execute(
        text("select Images from product_images where ProductID = :product_id"),
        {'product_id': product_id}
    ).fetchall()

    return render_template('editproduct.html',
                           product=product,
                           sizes=[size[0] for size in sizes],
                           colors=[color[0] for color in colors],
                           images=[image[0] for image in images])

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    account_type = session.get('account_type')
    user_id = session.get('user_id')

    if request.method == 'POST':
        try:
            form = request.form

            if account_type == 'admin':
                vendor_id = form.get('vendor_id')
            else:
                
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

            if account_type == 'admin':
                return redirect(url_for('all_products'))
            else:
                return redirect(url_for('vendor_products'))
            
        except:
            conn.rollback()
            return "Something went wrong while adding your product."
        
    vendors = []
    if account_type == 'admin':
        vendors = conn.execute(text("select VendorID, Name from vendor")).fetchall()
    return render_template('addproduct.html', vendors=vendors, account_type=account_type)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):

    account_type = session.get('account_type')


    conn.execute(text("Delete From product_images Where ProductID = :product_id"), {'product_id': product_id})
    conn.execute(text("Delete From product_sizes Where ProductID = :product_id"), {'product_id': product_id})
    conn.execute(text("Delete From product_color Where ProductID = :product_id"), {'product_id': product_id})

    conn.execute(text("Delete From products Where ProductID = :product_id"), {'product_id': product_id})
    conn.commit()

    if account_type == 'admin':
        return redirect(url_for('all_products'))
    else:
        return redirect(url_for('vendor_products'))


if __name__ == '__main__':
    app.run(debug=True)