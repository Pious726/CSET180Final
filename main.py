from datetime import date
from flask import Flask, flash, render_template, request, session, url_for, redirect
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
        userData = dict(request.form)
        hashed_password = bcrypt.hashpw(userData["Password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        userData["Password"] = hashed_password

        conn.execute(text('''
            INSERT INTO Users (name, email_address, username, password, account_type) 
            VALUES (:Name, :Email, :Username, :Password, :account_type)
        '''), userData)
        if userData["account_type"] == "customer":
            conn.execute(text(f'insert into customer (userID, name) values (LAST_INSERT_ID(), "{userData["Name"]}")'))
        elif userData["account_type"] == "vendor":
            conn.execute(text(f'insert into vendor (userID, name) values (LAST_INSERT_ID(), "{userData["Name"]}")'))
        conn.commit()

        return render_template('login.html', success="Successful", error=None)
    except Exception as e:
        print({e})
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
        password = request.form.get("Password").encode('utf-8')
        print(password)

        user = conn.execute(
            text('SELECT userID, password, account_type FROM users WHERE email_address = :email'),
            {'email': email}
        ).fetchone()
        print(user)

        if user:
            stored_password = user[1].encode('utf-8')
            if bcrypt.checkpw(password, stored_password):
        
                session['user_id'] = user[0]
                session['email'] = email
                session['account_type'] = user[2]

                conn.execute(
                    text("UPDATE users SET IsLoggedIN = 1 WHERE email_address = :email"),
                    {"email": email}
                )
                conn.commit()

                if user[2] == 'customer':  
        
                    customer = conn.execute(
                        text("SELECT customerID FROM customer WHERE userID = :userID"),
                        {"userID": user[0]}  
                    ).fetchone()

                    if customer:
                        customerID = customer[0] 

                        existing_cart = conn.execute(
                            text("SELECT cartID FROM cart WHERE customerID = :customerID"),
                            {"customerID": customerID}
                        ).fetchone()

                        if not existing_cart:
                            conn.execute(
                                text("INSERT INTO cart (customerID) VALUES (:customerID)"),
                                {"customerID": customerID}
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
    search_results = request.args.get('search', '').strip()

    query = '''
    SELECT DISTINCT p.*, pi.Images
    FROM products p
    JOIN Product_Images pi ON p.productID = pi.productID
    LEFT JOIN Product_Sizes ps ON p.productID = ps.productID
    LEFT JOIN Product_Color pc ON p.productID = pc.productID
    '''
    
    conditions = []
    params = {}

    if search_results:
        conditions.append("p.Title LIKE :search")
        params['search'] = f'%{search_results}%'

    if categories:
        conditions.append(f"p.category IN ({', '.join(':cat' + str(i) for i in range(len(categories)))})")
        for i, val in enumerate(categories):
            params[f'cat{i}'] = val

    if colors:
        conditions.append(f"pc.Color IN ({', '.join(':color' + str(i) for i in range(len(colors)))})")
        for i, val in enumerate(colors):
            params[f'color{i}'] = val

    if sizes:
        conditions.append(f"ps.Sizes IN ({', '.join(':size' + str(i) for i in range(len(sizes)))})")
        for i, val in enumerate(sizes):
            params[f'size{i}'] = val

    if availability:
        if "In Stock" in availability and "Out of Stock" not in availability:
            conditions.append("p.inventory > 0")
        elif "Out of Stock" in availability and "In Stock" not in availability:
            conditions.append("p.inventory <= 0")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    products = list(conn.execute(text(query), params))

    product_categories = [row[0] for row in conn.execute(text('SELECT DISTINCT category FROM products')).fetchall()]
    product_sizes = [row[0] for row in conn.execute(text('SELECT DISTINCT Sizes FROM Product_Sizes')).fetchall()]
    product_colors = [row[0] for row in conn.execute(text('SELECT DISTINCT Color FROM Product_Color')).fetchall()]

    return render_template('shop.html',
                           products=products,
                           product_sizes=product_sizes,
                           product_colors=product_colors,
                           product_categories=product_categories)


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

    color_query = text("SELECT DISTINCT Color FROM Product_Color WHERE productID = :id")
    colors = [row[0] for row in conn.execute(color_query, {'id': itemID})]
    session['item_colors'] = colors

    size_query = text("SELECT DISTINCT Sizes FROM Product_Sizes WHERE productID = :id")
    sizes = [row[0] for row in conn.execute(size_query, {'id': itemID})]
    session['item_sizes'] = sizes

    inventory_query = text("SELECT DISTINCT inventory FROM products WHERE productID = :id")
    inventory = conn.execute(inventory_query, {'id': itemID}).scalar()
    session['item_inventory'] = inventory

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

    return render_template('item.html', reviewList=reviewList, colors=colors, sizes=sizes, inventory=inventory)

@app.route('/item.html', methods=['POST'])
def addtocart():
        try:
            customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1;')).scalar()
            cartID = conn.execute(text(f'select cartID from cart where customerID = {customerID}')).scalar()
            productID = session.get('itemID')
            productImage = session.get('itemImage')
            item_color = request.form.get('item_color')
            item_size = request.form.get('item_size')

            conn.execute(text(f'insert into Cart_Items (cartID, productID, Color, Size, Image) values (:cartID, :productID, :Color, :Size, :Image)'), {'cartID': cartID, 'productID': productID, 'Color': item_color, 'Size': item_size, 'Image': productImage})
            conn.commit()

            colors = session.get('item_colors')
            sizes = session.get('item_sizes')
            inventory = session.get('item_inventory')
            query = f"select * from reviews natural join customer natural join users where productID = {productID}"
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

            return render_template('item.html', success="Item added to cart successfully.", error=None, colors=colors, sizes=sizes, inventory=inventory, reviewList=reviewList, productImage=productImage)
        except:
            colors = session.get('item_colors')
            sizes = session.get('item_sizes')
            inventory = session.get('item_inventory')
            query = f"select * from reviews natural join customer natural join users where productID = {productID}"
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

            return render_template('item.html', success=None, error="Error adding item to cart.", colors=colors, sizes=sizes, inventory=inventory, reviewList=reviewList)

@app.route('/cart.html')
def getcartitems():
    totalPrice = 0
    customerID = conn.execute(text('select customerID from users natural join customer where IsLoggedIn = 1')).scalar()
    cartID = conn.execute(text(f'select cartID from cart where customerID = {customerID}')).scalar()
    cartItems = list(conn.execute(text(f'select * from Cart_Items natural join products where cartID = {cartID}')))

    totalPrice = round(sum(item.Discount_Price * item.Quantity for item in cartItems), 2)
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
    totalPrice = round(sum(item.Discount_Price * item.Quantity for item in cartItems), 2)

    conn.execute(text(f'insert into orders (customerID, OrderDate, TotalPrice, OrderStatus) values ({customerID}, CURDATE(),{totalPrice}, "Pending")'))
    orderID = conn.execute(text('select LAST_INSERT_ID()')).scalar()

    for item in cartItems:
        conn.execute(text(f'insert into OrderItems (orderID, productID, Quantity) values ({orderID}, {item.productID}, {item.Quantity})'))

    conn.execute(text(f'delete from Cart_Items where cartID = {cartID}'))
    conn.commit()

    return redirect(url_for('orderthanks'))

@app.route('/update_shipping_status', methods=['POST'])
def update_shipping_status():
    order_id = request.form.get('orderID')
    new_status = request.form.get('status')

    # Fetch current status from DB
    current_status = conn.execute(
        text("select OrderStatus from orders where orderID = :id"),
        {'id': order_id}
    ).scalar()

    valid_transitions = {
        'Pending': 'Confirmed',
        'Confirmed': 'Handed to Delivery Partner',
        'Handed to Delivery Partner': 'Shipped'
    }

    # Prevent moving from 'Confirmed' directly to 'Shipped' without 'Handed to Delivery Partner'
    if current_status == 'Confirmed' and new_status == 'Shipped':
        flash('You must first select "Handed to Delivery Partner" before marking it as shipped.')
        return redirect(url_for('vendor_orders'))

    if valid_transitions.get(current_status) == new_status:
        conn.execute(
            text("update orders set OrderStatus = :status where orderID = :id"),
            {'status': new_status, 'id': order_id}
        )
        conn.commit()

    return redirect(url_for('vendor_orders'))

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

    # Updated query with complaint status for specific orderID and productID
    raw_orders = conn.execute(text("""
        select orders.orderID, orders.orderDate, orders.totalPrice, orders.orderStatus, 
               orderitems.productID, products.title, orderitems.quantity,
               complaint.status
        from orders
        join orderitems on orders.orderID = orderitems.orderID
        join products on orderitems.productID = products.productID
        left join complaint on orders.orderID = complaint.orderID 
            and orderitems.productID = complaint.productID
        where orders.customerID = :customerID
        order by orders.orderDate desc
    """), {'customerID': customerID}).fetchall()

    orders = []
    for row in raw_orders:
        existing_order = next((order for order in orders if order['orderID'] == row[0]), None)
        product_data = {
            'productID': row[4],
            'title': row[5],
            'quantity': row[6]
        }

        # Add complaint status if it exists for the specific product and order
        if row[7]:
            product_data['status'] = row[7]

        if existing_order:
            # If product has a complaint status, append to returns; otherwise, to products
            if 'status' in product_data:
                existing_order['returns'].append(product_data)
            else:
                existing_order['products'].append(product_data)
        else:
            # If it's a new order, create a new entry
            orders.append({
                'orderID': row[0],
                'orderDate': row[1],
                'totalPrice': row[2],
                'orderStatus': row[3],
                'products': [] if 'status' in product_data else [product_data],
                'returns': [product_data] if 'status' in product_data else []
            })

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

            # Determine the vendor ID
            if account_type == 'admin':
                vendor_id = form.get('vendor_id')
            else:
                vendor_id = conn.execute(
                    text('SELECT vendorID FROM vendor WHERE userID = :user_id'),
                    {'user_id': user_id}
                ).scalar()

            # Insert the product with the category included
            conn.execute(text("""
                insert into products 
                (VendorID, Title, Description, Warranty, Inventory, Original_Price, Discount_Price, Category)
                values 
                (:vendor_id, :title, :description, :warranty, :inventory, :original_price, :discount_price, :category)
            """), {
                'vendor_id': vendor_id,
                'title': form.get('title'),
                'description': form.get('description'),
                'warranty': form.get('warranty'),
                'inventory': form.get('inventory'),
                'original_price': form.get('original_price'),
                'discount_price': form.get('discount_price'),
                'category': form.get('category')
            })

            # Get the new product ID
            product_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

            # Insert optional details
            if form.get('new_size'):
                conn.execute(text("INSERT INTO product_sizes (ProductID, Sizes) VALUES (:product_id, :size)"),
                             {'product_id': product_id, 'size': form.get('new_size')})

            if form.get('new_color'):
                conn.execute(text("INSERT INTO product_color (ProductID, Color) VALUES (:product_id, :color)"),
                             {'product_id': product_id, 'color': form.get('new_color')})

            if form.get('new_image'):
                conn.execute(text("INSERT INTO product_images (ProductID, Images) VALUES (:product_id, :image)"),
                             {'product_id': product_id, 'image': form.get('new_image')})

            conn.commit()

            if account_type == 'admin':
                return redirect(url_for('all_products'))
            else:
                return redirect(url_for('vendor_products'))

        except Exception as e:
            conn.rollback()
            print(f"Error during product insert: {e}")
            return "Something went wrong while adding your product."

    # Render form
    vendors = []
    if account_type == 'admin':
        vendors = conn.execute(text("SELECT VendorID, Name FROM vendor")).fetchall()

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
    
@app.route('/vendor_orders')
def vendor_orders():
    user_id = session.get('user_id')  # Retrieve user_id from session

    # Redirect to login if no user_id is found in the session
    if not user_id:
        return redirect(url_for('login'))

    # Query to retrieve vendor_id for the logged-in user
    vendor_id = conn.execute(
        text('SELECT vendorID FROM vendor WHERE userID = :user_id'),
        {'user_id': user_id}
    ).scalar()

    # Check if vendor_id is found, return an error message if not
    if not vendor_id:
        return "You are not registered as a vendor."

    # Debugging: print the user_id and vendor_id to check their values
    print(f"User ID: {user_id}, Vendor ID: {vendor_id}")

    # Query to retrieve orders for the vendor's products
    orders = conn.execute(text("""
    select distinct orders.orderID, orders.customerID, orders.orderDate, orders.totalPrice, orders.orderStatus
    from orders
    join orderitems on orders.orderID = orderitems.orderID
    join products on orderitems.productID = products.productID
    where products.vendorID = :vendor_id
    order by orders.orderDate desc;
"""), {'vendor_id': vendor_id}).fetchall()


    # Debugging: print the orders data to check what is returned from the query
    print(orders)

    # Render the vendor_orders.html template with the orders data
    return render_template('vendor_orders.html', orders=orders)

@app.route('/file_complaint/<int:product_id>/<int:order_id>', methods=['GET'])
def show_complaint_form(product_id, order_id):
    return render_template('file_complaints.html', product_id=product_id, order_id=order_id)

@app.route('/file_complaint/<int:product_id>/<int:order_id>', methods=['POST'])
def file_complaint(product_id, order_id):
    customer_id = conn.execute(text('select customerID from customer natural join users where IsLoggedIn = 1')).scalar()

    title = request.form['title']
    description = request.form['description']
    demand = request.form['demand']
    image_urls = request.form['image_urls']

    today = date.today()

    # Insert complaint into complaint table
    conn.execute(text(""" 
        insert into complaint (customerID, productID, orderID, Date, Title, Description, Demand, Status) 
        values (:customerID, :productID, :orderID, :date, :title, :description, :demand, 'pending') 
    """), {
        'customerID': customer_id,
        'productID': product_id,
        'orderID': order_id,
        'date': today,
        'title': title,
        'description': description,
        'demand': demand
    })

    # Get the complaintID of the newly inserted complaint
    complaint_id = conn.execute(text(""" 
        select complaintID from complaint 
        where customerID = :customerID and productID = :productID and orderID = :orderID and Date = :date 
        order by complaintID desc limit 1 
    """), {
        'customerID': customer_id,
        'productID': product_id,
        'orderID': order_id,
        'date': today
    }).scalar() 

    # Process and save image URLs if provided
    if image_urls:
        urls = [url.strip() for url in image_urls.split(',') if url.strip()]
        for url in urls:
            conn.execute(text(""" 
                insert into complaint_images (complaintID, Images) values (:complaintID, :url) 
            """), {
                'complaintID': complaint_id,
                'url': url
            })

    conn.commit()  # Commit the transaction to the database

    return redirect(url_for('getorders'))

@app.route('/admin_returns.html', methods=['GET'])
def admin_returns():
    pending_returns = conn.execute(text("""
        select complaint.complaintID, complaint.Date, complaint.Title, complaint.Description, 
               complaint.Demand, complaint.Status, users.username, products.title as product_title
        from complaint
        join customer on complaint.customerID = customer.customerID
        join users on customer.userID = users.userID
        join products on complaint.productID = products.productID
        where complaint.Status = 'pending'
    """)).fetchall()

    returns_with_images = []
    for row in pending_returns:
        images = conn.execute(text("""
            select Images from complaint_images where complaintID = :complaintID
        """), {'complaintID': row[0]}).fetchall()

        image_urls = [img[0] for img in images]
        returns_with_images.append({
            'complaintID': row[0],
            'Date': row[1],
            'Title': row[2],
            'Description': row[3],
            'Demand': row[4],
            'Status': row[5],
            'username': row[6],
            'product_title': row[7],
            'images': image_urls
        })

    return render_template('admin_returns.html', returns=returns_with_images)

@app.route('/update_return_status', methods=['POST'])
def update_return_status():
    complaint_id = request.form['complaintID']
    action = request.form['action']

    new_status = 'confirmed' if action == 'confirm' else 'rejected'

    conn.execute(text("""
        update complaint 
        set Status = :status 
        where complaintID = :complaintID
    """), {'status': new_status, 'complaintID': complaint_id})

    if new_status == 'confirmed':
        result = conn.execute(text("""
            select productID, orderID 
            from complaint 
            where complaintID = :complaintID
        """), {'complaintID': complaint_id}).fetchone()

        if result:
            product_id, order_id = result

            conn.execute(text("""
                delete from orderitems 
                where orderID = :orderID and productID = :productID 
                limit 1
            """), {'orderID': order_id, 'productID': product_id})

    return redirect(url_for('admin_returns'))

@app.route('/chat', methods=['GET', 'POST'])
def start_chat():
    user_id = session.get('user_id')
    account_type = session.get('account_type')

    if account_type != 'customer':
        return redirect(url_for('login'))

    # Get customerID from userID
    customer_row = conn.execute(
        text("select customerID from customer where userID = :uid"),
        {'uid': user_id}
    ).fetchone()

    if not customer_row:
        return "Customer not found", 404

    customer_id = customer_row[0]

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id') or None
        admin_id = request.form.get('admin_id') or None

        if vendor_id == '':
            vendor_id = None
        if admin_id == '':
            admin_id = None

        if (vendor_id and admin_id) or (not vendor_id and not admin_id):
            return "Please select either a vendor OR an admin (not both or none).", 400

        if vendor_id:
            chat = conn.execute(text(""" 
                select chatID from chat 
                where customerID = :cust and vendorID = :vend and adminID is null
            """), {'cust': customer_id, 'vend': vendor_id}).fetchone()

            if not chat:
                conn.execute(text("""
                    insert into chat (customerID, vendorID) values (:cust, :vend)
                """), {'cust': customer_id, 'vend': vendor_id})
                conn.commit()
                chat = conn.execute(text("select last_insert_id()")).fetchone()

        elif admin_id:
            chat = conn.execute(text("""
                select chatID from chat 
                where customerID = :cust and adminID = :admin and vendorID is null
            """), {'cust': customer_id, 'admin': admin_id}).fetchone()

            if not chat:
                conn.execute(text("""
                    insert into chat (customerID, adminID) values (:cust, :admin)
                """), {'cust': customer_id, 'admin': admin_id})
                conn.commit()
                chat = conn.execute(text("select last_insert_id()")).fetchone()

        return redirect(url_for('chat_page', chat_id=chat[0]))

    vendors = conn.execute(text("select vendorID, Name from vendor")).fetchall()
    admins = conn.execute(text("""
        select a.adminID, u.name 
        from admin a join users u on a.userID = u.userID
    """)).fetchall()

    return render_template('chat.html', vendors=vendors, admins=admins)


@app.route('/chat/<int:chat_id>', methods=['GET', 'POST'])
def chat_page(chat_id):
    account_type = session.get('account_type')
    user_id = session.get('user_id')

    if request.method == 'POST':
        message = request.form['message']
        conn.execute(text("""
            insert into messages (chatID, sender_type, sender_id, message_text)
            values (:chat_id, :sender_type, :sender_id, :message)
        """), {'chat_id': chat_id, 'sender_type': account_type, 'sender_id': user_id, 'message': message})
        conn.commit()
        return redirect(url_for('chat_page', chat_id=chat_id))

    # Load chat messages
    messages = conn.execute(text("""
        select sender_type, message_text, timestamp
        from messages
        where chatID = :chat_id
        order by timestamp asc
    """), {'chat_id': chat_id}).fetchall()

    return render_template('chat_page.html', messages=messages, chat_id=chat_id)

@app.route('/chat/inbox')
def chat_inbox():
    account_type = session.get('account_type')
    user_id = session.get('user_id')

    if account_type == 'customer':
        # Get customerID
        customer_row = conn.execute(
            text("select customerID from customer where userID = :uid"),
            {'uid': user_id}
        ).fetchone()

        if not customer_row:
            return "Customer not found", 404

        customer_id = customer_row[0]

        chats = conn.execute(text("""
            select c.chatID, u.name as admin_name, v.name as vendor_name
            from chat c
            left join admin a on c.adminID = a.adminID
            left join users u on a.userID = u.userID
            left join vendor v on c.vendorID = v.vendorID
            where c.customerID = :id
        """), {'id': customer_id}).fetchall()

    elif account_type == 'vendor':
        # Get vendorID
        vendor_row = conn.execute(
            text("select vendorID from vendor where userID = :uid"),
            {'uid': user_id}
        ).fetchone()

        if not vendor_row:
            return "Vendor not found", 404

        vendor_id = vendor_row[0]

        chats = conn.execute(text("""
            select c.chatID, cu.name as customer_name
            from chat c
            join customer cu on c.customerID = cu.customerID
            where c.vendorID = :id
        """), {'id': vendor_id}).fetchall()

    elif account_type == 'admin':
        # Get adminID
        admin_row = conn.execute(
            text("select adminID from admin where userID = :uid"),
            {'uid': user_id}
        ).fetchone()

        if not admin_row:
            return "Admin not found", 404

        admin_id = admin_row[0]

        chats = conn.execute(text("""
            select c.chatID, cu.name as customer_name
            from chat c
            join customer cu on c.customerID = cu.customerID
            where c.adminID = :id
        """), {'id': admin_id}).fetchall()

    else:
        return "Unauthorized", 403

    return render_template('chat_inbox.html', chats=chats, account_type=account_type)





if __name__ == '__main__':
    app.run(debug=True)