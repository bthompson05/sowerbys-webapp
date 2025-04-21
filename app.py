from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import json
import os
import requests
from urllib.parse import quote
import hashlib
from modules.ShopifyResources import ShopifyResources
from modules.UKD import UKDStock
from queue import Queue
import threading
import time
import csv

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key in production

# Create directory for cached images if it doesn't exist
CACHE_DIR = os.path.join('static', 'cache', 'products')
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache expiration time in seconds (1 hour)
CACHE_EXPIRATION = 3600

# Add logging directory for Shopify API commands
LOGS_DIR = os.path.join('logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# File to store user data
USERS_FILE = os.path.join('users.json')

def is_cache_valid(cached_path):
    """Check if the cached file is still valid (less than 1 hour old)."""
    if not os.path.exists(cached_path):
        return False
    
    current_time = time.time()
    file_modified_time = os.path.getmtime(cached_path)
    
    return (current_time - file_modified_time) < CACHE_EXPIRATION

def download_and_cache_image(image_url, sku):
    """Download and cache an image, return the local cached path."""
    try:
        # Create a unique filename based on the SKU
        safe_sku = quote(sku, safe='')
        file_ext = '.jpg'  # Default to jpg for UKD images
        cached_filename = f"{safe_sku}{file_ext}"
        cached_path = os.path.join(CACHE_DIR, cached_filename)
        
        # If image is already cached and not expired, return the cached path
        if is_cache_valid(cached_path):
            return f'/static/cache/products/{cached_filename}'
        
        # Download the image if cache is expired or doesn't exist
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            with open(cached_path, 'wb') as f:
                f.write(response.content)
            # Update the file's modification time to now
            os.utime(cached_path, None)
            return f'/static/cache/products/{cached_filename}'
    except Exception as e:
        print(f"Error downloading image for {sku}: {str(e)}")
    
    return None

def cleanup_expired_cache():
    """Remove expired cache files."""
    try:
        current_time = time.time()
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path):
                file_modified_time = os.path.getmtime(file_path)
                if (current_time - file_modified_time) >= CACHE_EXPIRATION:
                    os.remove(file_path)
                    print(f"Removed expired cache file: {filename}")
    except Exception as e:
        print(f"Error during cache cleanup: {str(e)}")

# Run cache cleanup when starting the application
cleanup_expired_cache()

# Global variables for tracking update status
update_status = {
    'is_running': False,
    'percentage': 0,
    'messages': [],
    'last_update': None
}

def log_message(message):
    update_status['messages'].append(message)
    if len(update_status['messages']) > 100:  # Keep only last 100 messages
        update_status['messages'].pop(0)

class LoggingShopifyResources(ShopifyResources):
    def CountUpdate(self, Count, Increment):
        if Count % Increment == 0:
            message = f"{Count} products processed"
            log_message(message)
            print(message)

    def UKDStockUpdate(self):
        global update_status
        try:
            log_message("Starting UKD stock update...")
            ukd_stock = UKDStock().GetFullStock()
            self.GetLatestShopifyProducts()
            NumberOfProducts = len(self.Products)
            log_message(f"Found {NumberOfProducts} products to process")

            while len(self.Products) > 0:
                SKU, InventoryID = self.Products.pop()
                if SKU in ukd_stock:
                    Count = NumberOfProducts - len(self.Products)
                    if Count % 1000 == 0:  # Show message every 1000 products
                        message = f"{Count} products processed"
                        log_message(message)
                        print(message)
                    
                    message = f"Stock updated for {SKU}"
                    log_message(message)
                    print(message)
                    
                    self.SetPercentageComplete(Count, NumberOfProducts)
                    Quantity = ukd_stock[SKU]
                    if InventoryID is not None:
                        self.ShopifyStock(InventoryID, self.UKD_LocationID, Quantity)
                else:
                    message = f"{SKU} not stocked by UKD"
                    log_message(message)
                    print(message)

            log_message("UKD stock update completed!")
        except Exception as e:
            log_message(f"Error during update: {str(e)}")
            raise e
        finally:
            update_status['is_running'] = False

    def SetPercentageComplete(self, Searched, Total):
        self.PercentageComplete = round((Searched / Total) * 100)
        update_status['percentage'] = self.PercentageComplete
        log_message(f"Progress: {self.PercentageComplete}%")

# Initialize users from file or use default if file doesn't exist
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        'benthompson2385@gmail.com': {
            'password': 'password123',
            'name': 'Ben Thompson',
            'is_admin': True,
            'role': 'Admin',
            'status': 'Active'
        },
        'clivesowerby3@gmail.com': {
            'password': 'password123',
            'name': 'Clive Sowerby',
            'is_admin': False,
            'role': 'Staff',
            'status': 'Active'
        }
    }

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(USERS, f, indent=4)

# Load initial users
USERS = load_users()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('is_admin', False):
            flash('Admin access required')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('store_stock'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email in USERS and USERS[email]['password'] == password and USERS[email]['status'] == 'Active':
            session.clear()
            session['logged_in'] = True
            session['email'] = email
            session['name'] = USERS[email]['name']
            session['is_admin'] = USERS[email]['is_admin']
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid credentials or account inactive')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    name = session.get('name', 'User')
    email = session.get('email', 'No email set')
    is_admin = session.get('is_admin', False)
    user = USERS.get(email, {})
    return render_template('home.html', name=name, email=email, is_admin=is_admin, user=user)

@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role', 'Staff')
        
        if email and password and name:
            if email in USERS:
                flash('Email already exists')
            else:
                USERS[email] = {
                    'password': password,
                    'name': name,
                    'is_admin': role == 'Admin',
                    'role': role,
                    'status': 'Active'
                }
                save_users()
                flash('User created successfully')
                return redirect(url_for('admin_dashboard'))
        else:
            flash('All fields are required')
    
    return render_template('create_user.html')

@app.route('/admin/edit_user/<email>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(email):
    if email not in USERS:
        flash('User not found')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        status = request.form.get('status')
        new_password = request.form.get('new_password')
        
        if name and role and status:
            USERS[email]['name'] = name
            USERS[email]['role'] = role
            USERS[email]['is_admin'] = role == 'Admin'
            USERS[email]['status'] = status
            if new_password:
                USERS[email]['password'] = new_password
            
            save_users()
            flash('User updated successfully')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Name, role, and status are required')
    
    return render_template('edit_user.html', email=email, user=USERS[email])

@app.route('/admin/delete_user/<email>')
@login_required
@admin_required
def delete_user(email):
    if email == session['email']:
        flash('Cannot delete your own account')
        return redirect(url_for('admin_dashboard'))
    
    if email in USERS:
        del USERS[email]
        save_users()
        flash('User deleted successfully')
    else:
        flash('User not found')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_status/<email>')
@login_required
@admin_required
def toggle_status(email):
    if email == session['email']:
        flash('Cannot modify your own account status')
        return redirect(url_for('admin_dashboard'))
    
    if email in USERS:
        USERS[email]['status'] = 'Inactive' if USERS[email]['status'] == 'Active' else 'Active'
        save_users()
        flash(f"User status changed to {USERS[email]['status']}")
    else:
        flash('User not found')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin-dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Get user data
    users = USERS
    
    # Get product information from UKD
    ukd = UKDStock()
    products = ukd.GetAllProducts()
    
    # Calculate product statistics
    total_products = len(products)
    in_stock_products = sum(1 for p in products if p.get('inStock', 0) > 0)
    out_of_stock_products = total_products - in_stock_products
    
    # Calculate brand statistics
    brands = set(p.get('brand', '') for p in products)
    brand_count = len(brands)
    active_brands = len(set(p.get('brand', '') for p in products if p.get('inStock', 0) > 0))
    
    # Calculate price statistics
    prices = [float(p.get('price', 0)) for p in products if p.get('price')]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0
    min_price = round(min(prices), 2) if prices else 0
    max_price = round(max(prices), 2) if prices else 0
    
    return render_template('admin_dashboard.html', 
                         users=users,
                         total_products=total_products,
                         in_stock_products=in_stock_products,
                         out_of_stock_products=out_of_stock_products,
                         brand_count=brand_count,
                         active_brands=active_brands,
                         avg_price=avg_price,
                         min_price=min_price,
                         max_price=max_price)

@app.route('/stock/add')
@login_required
def add_stock():
    return render_template('add_stock.html')

@app.route('/stock/shopify')
@login_required
def shopify_stock():
    return render_template('shopify_stock.html')

@app.route('/stock/store')
@login_required
def store_stock():
    return render_template('store_stock.html')

@app.route('/stock/sale-book')
@login_required
def sale_book():
    return render_template('sale_book.html')

@app.route('/fulfill-orders')
@login_required
def fulfill_orders():
    return render_template('fulfill_orders.html')

@app.route('/scan-barcode', methods=['POST'])
@login_required
def scan_barcode():
    try:
        data = request.get_json()
        raw_barcode = data.get('barcode', '')
        
        print(f"\n=== Barcode Scan Request ===")
        print(f"Raw barcode input: {raw_barcode}")
        
        # Clean up barcode
        barcode = raw_barcode.strip()
        if len(barcode) > 13:
            # Check for duplication
            first_half = barcode[:len(barcode)//2]
            second_half = barcode[len(barcode)//2:]
            if first_half == second_half:
                barcode = first_half
            else:
                # If not duplicated, take first 13 digits
                barcode = barcode[:13]
        
        print(f"Cleaned barcode: {barcode}")
        
        if not barcode:
            print("No barcode provided in request")
            return jsonify({
                'success': False,
                'message': 'No barcode provided'
            })
        
        # Initialize UKD Stock
        print("\nInitializing UKDStock...")
        ukd = UKDStock()
        
        print(f"\nLooking up product info for barcode: {barcode}")
        product_info = ukd.GetProductFromBarcode(barcode)
        print(f"Product info result: {product_info}")
        
        if product_info:
            # Initialize ShopifyResources and get Shopify product info
            shopify = ShopifyResources()
            style_no = product_info.get('styleNo', '')
            shopify_info = shopify.GetProductByStyleNo(style_no) if style_no else {'found': False}
            
            # Combine UKD and Shopify info
            response_data = {
                'success': True,
                'barcode': barcode,
                'styleNo': style_no,
                'size': product_info.get('size', ''),
                'brand': product_info.get('brand', ''),
                'name': product_info.get('name', ''),
                'message': f'Found: {style_no} - Size {product_info.get("size", "")}',
                'shopify': shopify_info
            }
            
            print(f"Returning success response with Shopify info: {response_data}")
            return jsonify(response_data)
        else:
            print(f"No product found for barcode: {barcode}")
            return jsonify({
                'success': False,
                'message': f'No product found for barcode: {barcode}'
            })
            
    except Exception as e:
        error_msg = f"Error processing barcode: {str(e)}"
        print(f"Error in scan_barcode: {error_msg}")
        return jsonify({
            'success': False,
            'message': error_msg
        })

@app.route('/update-ukd-stock', methods=['POST'])
@login_required
def update_ukd_stock():
    global update_status
    
    if update_status['is_running']:
        return jsonify({'success': False, 'error': 'Update already in progress'}), 400
    
    try:
        update_status['is_running'] = True
        update_status['percentage'] = 0
        update_status['messages'] = []
        
        def run_update():
            try:
                shopify = LoggingShopifyResources()
                shopify.UKDStockUpdate()
            except Exception as e:
                print(f"Error in update thread: {e}")
                update_status['is_running'] = False

        thread = threading.Thread(target=run_update)
        thread.daemon = True  # Make thread daemon so it doesn't block program exit
        thread.start()
        
        return jsonify({'success': True, 'message': 'Update started'})
    except Exception as e:
        update_status['is_running'] = False
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update-status')
@login_required
def get_update_status():
    return jsonify({
        'is_running': update_status['is_running'],
        'percentage': update_status['percentage'],
        'messages': update_status['messages']
    })

def download_product_images(variants_found):
    """Download images for all found variants of a product"""
    try:
        # Base URL for UKD images
        base_url = 'https://www.ukdistributors.co.uk/photos/840'
        downloaded_images = {}
        
        print("\nStarting image downloads:")
        print("------------------------")
        
        # Use the color codes we actually found in the stock data
        for color_code in variants_found:
            try:
                # Format code - only add space if it starts with a single letter
                # Find the position where numbers start
                num_start = next((i for i, c in enumerate(color_code) if c.isdigit()), -1)
                
                if num_start == 1:  # Single letter prefix (e.g., "B430A")
                    formatted_code = color_code[0] + ' ' + color_code[1:]
                else:  # Two or more letter prefix (e.g., "MS161") or no numbers
                    formatted_code = color_code
                
                variant_images = []
                
                print(f"\nProcessing variant: {color_code}")
                print(f"Formatted code: {formatted_code}")
                
                # Try base version and numbered versions (1-5)
                image_variations = [formatted_code] + [f"{formatted_code}{i}" for i in range(1, 6)]
                
                for variation in image_variations:
                    # Create the UKD URL with proper encoding
                    url = f"{base_url}/{quote(variation)}.jpg"
                    
                    # Create a safe filename for local storage (without spaces)
                    safe_filename = variation.replace(' ', '') + '.jpg'
                    cache_path = os.path.join(CACHE_DIR, safe_filename)
                    
                    print(f"\nTrying variation: {variation}")
                    print(f"Download URL: {url}")
                    print(f"Cache path: {cache_path}")
                    
                    # Download and save the image if it doesn't exist
                    if not os.path.exists(cache_path):
                        print(f"Downloading new image...")
                        try:
                            response = requests.get(url, timeout=5)
                            if response.status_code == 200:
                                with open(cache_path, 'wb') as f:
                                    f.write(response.content)
                                print(f"✓ Successfully downloaded and saved image")
                                variant_images.append(f'/static/cache/products/{safe_filename}')
                            else:
                                print(f"✗ Failed to download image: HTTP {response.status_code}")
                        except Exception as e:
                            print(f"✗ Error downloading {variation}: {str(e)}")
                            continue
                    else:
                        print("Using existing cached image")
                        variant_images.append(f'/static/cache/products/{safe_filename}')
                
                if variant_images:
                    downloaded_images[color_code] = variant_images
                    print(f"✓ Found {len(variant_images)} images for {color_code}")
                else:
                    print(f"✗ No images available for {color_code}")
                
            except Exception as e:
                print(f"✗ Error processing {color_code}: {str(e)}")
                continue
        
        print("\nDownload summary:")
        print(f"Total variants processed: {len(variants_found)}")
        print(f"Successfully cached variants: {len(downloaded_images)}")
        total_images = sum(len(imgs) for imgs in downloaded_images.values())
        print(f"Total images downloaded: {total_images}")
        print("------------------------\n")
        
        return downloaded_images
    except Exception as e:
        print(f"✗ Error in download_product_images: {str(e)}")
        return {}

@app.route('/search-product', methods=['POST'])
@login_required
def search_product():
    try:
        data = request.get_json()
        distributor = data.get('distributor')
        product_code = data.get('productCode')

        if not distributor or not product_code:
            return jsonify({'success': False, 'message': 'Missing distributor or product code'})

        if distributor == 'ukd':
            # Remove any spaces from the product code
            product_code = product_code.replace(' ', '')
            
            # Get UKD stock
            ukd = UKDStock()
            stock_data = ukd.GetFullStock()
            
            # Load UKD data file to get color names and EAN13 codes
            data_file_path = os.path.join("files", "UKDData.csv")
            ukd_data = {}
            
            print(f"\n=== Processing UKD Search ===")
            print(f"Product code: {product_code}")
            print(f"Looking for data file: {data_file_path}")
            
            if os.path.exists(data_file_path):
                print(f"File exists, processing...")
                try:
                    # Read the entire file as a string to fix line break issues
                    with open(data_file_path, 'r', encoding='utf-8-sig') as file:
                        file_contents = file.read()
                        
                    # Fix line endings and excessive whitespace
                    cleaned_content = file_contents.replace('\r', '').replace('\n', '').replace('  ', ' ')
                    
                    # Create a list of rows with proper line breaks
                    rows = [row for row in cleaned_content.split(product_code) if row]
                    
                    # Process the first row to get headers
                    header_row = rows[0] if rows else ""
                    headers = header_row.split(',')
                    
                    # Find column indices
                    style_idx = 0  # StyleNo is first column
                    color_idx = 3  # Color is 4th column
                    size_idx = 13  # Size is 14th column
                    price_idx = 14 # Price is 15th column
                    vat_idx = 15   # VAT is 16th column
                    ean13_idx = 17  # EAN13 is 18th column
                    
                    print(f"Using fixed column indices:")
                    print(f" - StyleNo: {style_idx}")
                    print(f" - Color: {color_idx}")
                    print(f" - Size: {size_idx}")
                    print(f" - Price: {price_idx}")
                    print(f" - VAT: {vat_idx}")
                    print(f" - EAN13: {ean13_idx}")
                    
                    matched_count = 0
                    
                    # Use the UKD.GetProductInfo method to get product info directly
                    for sku, stock in stock_data.items():
                        base_sku = sku.split('-')[0] if '-' in sku else sku
                        if base_sku.upper().startswith(product_code.upper()):
                            parts = sku.split('-')
                            if len(parts) >= 2:
                                color_code = parts[0].rstrip('+')
                                size = parts[1]
                                
                                # Try to get more detailed info
                                product_info = ukd.GetProductInfo(color_code)
                                if product_info:
                                    matched_count += 1
                                    ukd_data[sku] = {
                                        'color_name': product_info.get('color', color_code),
                                        'ean13': product_info.get('ean13', ''),
                                        'tradePriceEx': product_info.get('tradePriceEx', '0.00'),
                                        'tradePriceInc': product_info.get('tradePriceInc', '0.00')
                                    }
                                    if matched_count <= 3:  # Just show the first few matches for debugging
                                        print(f"Found match via GetProductInfo: {sku}")
                                        print(f" - Color: {product_info.get('color', 'N/A')}")
                                        print(f" - EAN13: {product_info.get('ean13', 'N/A')}")
                                        print(f" - Price (ex VAT): £{product_info.get('tradePriceEx', '0.00')}")
                                        print(f" - Price (inc VAT): £{product_info.get('tradePriceInc', '0.00')}")
                    
                    # If no data was found, use the barcode map
                    if not ukd_data:
                        print("No data found via GetProductInfo, using BarcodeMap")
                        for barcode, info in ukd.BarcodeMap.items():
                            style_no = info.get('styleNo', '')
                            if style_no.upper().startswith(product_code.upper()):
                                size = info.get('size', '')
                                sku = f"{style_no}-{size}"
                                color_name = info.get('color', style_no)
                                trade_price_ex = info.get('tradePriceEx', '0.00')
                                trade_price_inc = info.get('tradePriceInc', '0.00')
                                
                                ukd_data[sku] = {
                                    'color_name': color_name,
                                    'ean13': barcode,
                                    'tradePriceEx': trade_price_ex,
                                    'tradePriceInc': trade_price_inc
                                }
                                
                                matched_count += 1
                                if matched_count <= 3:
                                    print(f"Found match via BarcodeMap: {sku}")
                                    print(f" - Color: {color_name}")
                                    print(f" - EAN13: {barcode}")
                                    print(f" - Price (ex VAT): £{trade_price_ex}")
                                    print(f" - Price (inc VAT): £{trade_price_inc}")
                    
                    print(f"Found {matched_count} matches")
                    print(f"UKD data contains {len(ukd_data)} entries")
                
                except Exception as e:
                    print(f"Error processing UKD data file: {str(e)}")
            else:
                print(f"UKD data file not found at {data_file_path}")
            
            # Group variants by color (ignoring + suffix)
            variants = {}
            total_variants = 0
            color_codes = set()  # Keep track of unique color codes
            
            # First pass: collect all color codes
            for sku, stock in stock_data.items():
                base_sku = sku.split('-')[0] if '-' in sku else sku
                base_sku = base_sku.rstrip('+')  # Remove '+' suffix for grouping
                
                if base_sku.upper().startswith(product_code.upper()):
                    parts = sku.split('-')
                    if len(parts) >= 2:
                        color_code = parts[0].rstrip('+')  # Remove '+' from color code
                        color_codes.add(color_code)

            # Download images for all color codes
            downloaded_images = download_product_images(color_codes)
            
            # Get product info for additional details
            style_info = ukd.GetProductInfo(product_code) or {}
            print(f"Style info for {product_code}: {style_info}")
            
            # Second pass: group variants and use downloaded images
            for sku, stock in stock_data.items():
                base_sku = sku.split('-')[0] if '-' in sku else sku
                base_sku = base_sku.rstrip('+')
                
                if base_sku.upper().startswith(product_code.upper()):
                    parts = sku.split('-')
                    if len(parts) >= 2:
                        color_code = parts[0].rstrip('+')
                        size = parts[1]
                        
                        # Get color name and EAN13 from the UKD data
                        ukd_item_data = ukd_data.get(sku, {})
                        color_name = ukd_item_data.get('color_name', color_code)
                        ean13_code = ukd_item_data.get('ean13', '')
                        
                        # Get price information from ukd_data or style_info
                        ex_price = ukd_item_data.get('tradePriceEx', style_info.get('tradePriceEx', '0.00'))
                        inc_price = ukd_item_data.get('tradePriceInc', style_info.get('tradePriceInc', '0.00'))
                        
                        # Clean up EAN13 code (remove any non-digit characters)
                        cleaned_ean13 = ''.join(c for c in str(ean13_code) if c.isdigit())
                        if cleaned_ean13 and len(cleaned_ean13) >= 8:  # Minimum length for a valid barcode
                            ean13_code = cleaned_ean13
                        
                        # If we have no data from UKD data file, try to get barcode via BarcodeMap
                        if not ean13_code:
                            for barcode, info in ukd.BarcodeMap.items():
                                if info.get('styleNo') == color_code and info.get('size') == size:
                                    ean13_code = barcode
                                    # Also try to get price from BarcodeMap if not set yet
                                    if ex_price == '0.00':
                                        ex_price = info.get('tradePriceEx', '0.00')
                                    if inc_price == '0.00':
                                        inc_price = info.get('tradePriceInc', '0.00')
                                    break
                        
                        # For debugging
                        if total_variants < 3:
                            print(f"Processing variant: {sku}")
                            print(f" - Color code: {color_code}")
                            print(f" - Color name: {color_name}")
                            print(f" - EAN13: {ean13_code}")
                            print(f" - Price (ex VAT): £{ex_price}")
                            print(f" - Price (inc VAT): £{inc_price}")
                            print(f" - UKD data entry: {ukd_data.get(sku)}")
                        
                        # Initialize color group if it doesn't exist
                        if color_code not in variants:
                            variants[color_code] = {
                                'sizes': [],
                                'image_url': downloaded_images.get(color_code, []),  # Use downloaded images
                                'color': color_name  # Use actual color name instead of color code
                            }
                        
                        # Add size variant with extended information
                        variants[color_code]['sizes'].append({
                            'sku': sku,
                            'size': size,
                            'stock': stock,
                            'ean13': ean13_code,  # Use actual EAN13 from data
                            'price': ex_price,
                            'vat': inc_price
                        })
                        total_variants += 1
            
            print(f"Total variants found: {total_variants}")
            print(f"=== End of Processing ===\n")
            
            if variants:
                return jsonify({
                    'success': True,
                    'variants': variants,
                    'totalVariants': total_variants
                })
            else:
                return jsonify({'success': False, 'message': 'No variants found for this product code'})
                
        elif distributor == 'comfort':
            # Handle Comfort Shoes logic here
            return jsonify({'success': False, 'message': 'Comfort Shoes integration not implemented yet'})
        
        return jsonify({'success': False, 'message': 'Invalid distributor'})
        
    except Exception as e:
        print(f"Error in search_product: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/add-to-inventory', methods=['POST'])
@login_required
def add_to_inventory():
    data = request.get_json()
    distributor = data.get('distributor')
    skus = data.get('skus', [])
    
    if not skus:
        return jsonify({
            'success': False,
            'message': 'No SKUs provided'
        })
    
    try:
        # Here you would implement the logic to add the products to your inventory
        # For now, we'll just return a success message with the count of added items
        return jsonify({
            'success': True,
            'message': f'{len(skus)} products added to inventory'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error adding products to inventory: {str(e)}'
        })

@app.route('/product-details', methods=['GET', 'POST'])
@login_required
def product_details():
    if request.method == 'POST':
        # Get the variants data from the form
        variants_data = request.form.get('variants_data')
        if variants_data:
            # Store in session
            session['variants_data'] = variants_data
            # If we have product details in session, use them for pre-filling the form
            product_details = session.get('product_details', {})
            return render_template('product_details.html', 
                                variants_data=variants_data,
                                product_details=product_details)
    else:
        # GET request - check if we have data in session
        variants_data = session.get('variants_data')
        product_details = session.get('product_details', {})
        if variants_data:
            return render_template('product_details.html', 
                                variants_data=variants_data,
                                product_details=product_details)
    
    flash('No variant data available', 'error')
    return redirect(url_for('add_stock'))

@app.route('/save-product-details', methods=['POST'])
@login_required
def save_product_details():
    try:
        # Get form data
        product_details = {
            'product_name': request.form.get('product_name'),
            'price': request.form.get('price'),
            # Add UKD info
            'brand': 'ROAMERS',
            'description': 'Twin Gusset Boot',
            'trade_price_ex_vat': '18.25',
            'trade_price_inc_vat': '21.90',
            'colors': ['Black', 'Tan'],
            'sizes': ['6', '7', '8', '9', '10', '11', '12'],
            'variant_count': 14
        }
        
        # Store in session
        session['product_details'] = product_details
        variants_data = json.loads(request.form.get('variants_data'))

        # Here you would typically save this data to your database
        print(f"Product Details: {product_details}")
        print(f"Variants: {variants_data}")

        flash('Product details saved successfully', 'success')
        return redirect(url_for('review_product'))

    except Exception as e:
        flash(f'Error saving product details: {str(e)}', 'error')
        return redirect(url_for('product_details'))

@app.route('/review-product', methods=['GET'])
@login_required
def review_product():
    variants_data = session.get('variants_data')
    variants_data = session.get('variants_data')
    product_details = session.get('product_details')
    
    if not variants_data or not product_details:
        flash('Missing product information', 'error')
        return redirect(url_for('add_stock'))
    
    return render_template('review_product.html', 
                         variants_data=variants_data,
                         product_details=product_details)

@app.route('/clear-product-session', methods=['POST'])
@login_required
def clear_product_session():
    # Clear product-related session data
    session.pop('variants_data', None)
    session.pop('product_details', None)
    return jsonify({'success': True})

@app.route('/get-product-info', methods=['POST'])
def get_product_info():
    try:
        data = request.get_json()
        sku = data.get('sku')
        
        print(f"Received request for SKU: {sku}")
        
        if not sku:
            print("No SKU provided in request")
            return jsonify({'success': False, 'message': 'SKU is required'})
        
        # Extract the base style number from the SKU (everything before the size)
        style_no = sku.split('-')[0] if '-' in sku else sku
        style_no = style_no.rstrip('+')  # Remove any '+' suffix
        
        print(f"Extracted style number: {style_no}")
        
        ukd = UKDStock()
        print(f"Calling GetProductInfo for style number: {style_no}")
        product_info = ukd.GetProductInfo(style_no)
        print(f"Product info result: {product_info}")
        
        if product_info:
            return jsonify({
                'success': True,
                'productInfo': {
                    'brand': product_info.get('brand', ''),
                    'name': product_info.get('name', ''),
                    'description': product_info.get('description', ''),
                    'tradePriceEx': product_info.get('tradePriceEx', ''),
                    'tradePriceInc': product_info.get('tradePriceInc', '')
                }
            })
        else:
            print(f"No product information found for style number: {style_no}")
            return jsonify({'success': False, 'message': 'Product information not found'})
            
    except Exception as e:
        print(f"Error in get-product-info: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def log_shopify_command(command_type, data):
    """Log Shopify API commands to a file"""
    try:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_file = os.path.join(LOGS_DIR, 'shopify_commands.log')
        with open(log_file, 'a') as f:
            f.write(f"\n[{timestamp}] {command_type}\n")
            f.write(json.dumps(data, indent=2))
            f.write("\n" + "-"*50 + "\n")
    except Exception as e:
        print(f"Error logging Shopify command: {e}")

@app.route('/post-to-shopify', methods=['POST'])
@login_required
def post_to_shopify():
    # This function is now deprecated and redirects to the create-product endpoint
    try:
        data = request.get_json()
        return jsonify({
            'success': False,
            'message': 'This endpoint is deprecated. Please use /create-product instead.'
        })
    except Exception as e:
        print(f"Error in deprecated post_to_shopify: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/shopify-variant', methods=['POST'])
@login_required
def get_shopify_variant():
    try:
        data = request.get_json()
        sku = data.get('sku')
        
        if not sku:
            return jsonify({
                'success': False,
                'message': 'No SKU provided'
            })
            
        # GraphQL query for Shopify
        query = """
        query getVariantDetails($sku: String!) {
            productVariants(first: 1, query: $sku) {
                edges {
                    node {
                        price
                        image {
                            originalSrc
                        }
                        product {
                            title
                        }
                    }
                }
            }
        }
        """
        
        # Initialize ShopifyResources
        shopify = ShopifyResources()
        
        # Execute GraphQL query
        result = shopify.ExecuteGraphQL(query, variables={'sku': f'sku:{sku}'})
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"Error in get_shopify_variant: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/check-unfulfilled-orders', methods=['POST'])
@login_required
def check_unfulfilled_orders():
    try:
        data = request.get_json()
        sku = data.get('sku')
        
        if not sku:
            return jsonify({
                'success': False,
                'message': 'No SKU provided'
            })
            
        # GraphQL query to get unfulfilled orders containing the SKU
        query = '''
        query getUnfulfilledOrders {
          orders(first: 50, query: "fulfillment_status:unfulfilled") {
            edges {
              node {
                id
                name
                createdAt
                lineItems(first: 50) {
                  edges {
                    node {
                      sku
                      quantity
                      title
                    }
                  }
                }
              }
            }
          }
        }
        '''
        
        # Initialize ShopifyResources
        shopify = ShopifyResources()
        
        # Execute GraphQL query
        try:
            response = requests.post(
                shopify.Url,
                headers=shopify.Headers,
                data=query,
                verify=False
            )
            result = response.json()
            
            if 'data' not in result or 'orders' not in result['data']:
                return jsonify({
                    'success': False,
                    'message': 'Failed to fetch orders from Shopify'
                })
            
            # Filter orders that contain the SKU
            matching_orders = []
            for edge in result['data']['orders']['edges']:
                order = edge['node']
                for item_edge in order['lineItems']['edges']:
                    item = item_edge['node']
                    if item['sku'] == sku:
                        matching_orders.append({
                            'order_number': order['name'],
                            'created_at': order['createdAt'],
                            'quantity': item['quantity'],
                            'product_title': item['title']
                        })
            
            return jsonify({
                'success': True,
                'orders': matching_orders
            })
            
        except Exception as e:
            print(f"Error querying Shopify: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error querying Shopify: {str(e)}'
            })
            
    except Exception as e:
        print(f"Error in check_unfulfilled_orders: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/create-product', methods=['POST'])
def create_product():
    try:
        data = request.json
        product_name = data.get('productName')
        price = data.get('price')
        variants_data = data.get('variants')

        if not all([product_name, price, variants_data]):
            return jsonify({'success': False, 'message': 'Missing required fields'})

        ukd = UKDStock()
        shopify = ShopifyResources()

        # Get the first variant to use for product details
        first_color = next(iter(variants_data.values()))
        if not first_color or not first_color.get('sizes'):
            return jsonify({'success': False, 'message': 'No variant data found'})

        # Get the first size data
        first_size = first_color['sizes'][0]
        first_sku = first_size['sku']
        style_no = first_sku.split('-')[0] if '-' in first_sku else first_sku
        
        # Get product info from UKD
        product_info = ukd.GetProductInfo(style_no)
        if not product_info:
            return jsonify({'success': False, 'message': 'Product information not found'})

        # Generate description HTML in the desired format
        upper = product_info.get('upper', '')
        desc = product_info.get('description', '') # Use 'description' key now
        sole = product_info.get('sole', '')
        
        description_html = f"<ul>"
        if upper: description_html += f"<li>{upper} upper</li>"
        if desc: description_html += f"<li>{desc}</li>"
        if sole: description_html += f"<li>{sole} sole</li>"
        description_html += f"</ul><p>Don't forget, we pay the postage! Shipped from our family run store in Stourbridge.</p>"

        # Escape quotes for JSON safety within GraphQL
        description_html = description_html.replace('"', '\\"')

        # Format variants for Shopify
        variants_list = "["
        all_color_codes = set()
        for color_code, color_data in variants_data.items():
            all_color_codes.add(color_code) # Collect unique color codes
            for size_data in color_data['sizes']:
                # Get actual stock quantity from size_data, or default to 0 if not available
                stock_quantity = size_data.get('stock', 0)
                
                # Get the color name
                color_name = color_data.get('color', color_code)
                
                # Get barcode (EAN13) from variant data
                barcode = size_data.get('ean13', '')
                # Clean up barcode - ensure it only contains digits
                barcode = ''.join(c for c in barcode if c.isdigit())
                
                # Format variant - always include barcode field regardless of its content
                variant = '''{options: ["%s", "%s"], sku: "%s", barcode: "%s", price: %s, inventoryItem: {tracked: true, cost: 0}, inventoryPolicy: DENY, inventoryQuantities: [{locationId: "%s", availableQuantity: %s}]}''' % (
                    color_name.strip(), size_data['size'].strip(), size_data['sku'].strip(), barcode, price,
                    shopify.UKD_LocationID, stock_quantity)
                
                variants_list += variant + ","
        
        # Remove trailing comma and close bracket
        if variants_list.endswith(","):
            variants_list = variants_list[:-1]
        variants_list += "]"

        # Generate image list if available
        images_list = "["
        all_image_urls = set() # Use a set to avoid duplicate URLs
        
        # Debug the structure of variants_data to see what's available
        print("\n=== DEBUGGING VARIANTS DATA STRUCTURE ===")
        for color_code in all_color_codes:
            if color_code in variants_data:
                print(f"Color {color_code} data keys: {variants_data[color_code].keys()}")
                # Check if the image_url key exists and what its value is
                if 'image_url' in variants_data[color_code]:
                    print(f"  image_url type: {type(variants_data[color_code]['image_url'])}")
                    print(f"  image_url value: {variants_data[color_code]['image_url']}")
                else:
                    print(f"  No image_url key found for color {color_code}")
        
        # Log all image URLs for debugging
        print("\n=== Image URLs in Data ===")
        for color_code in all_color_codes:
            if color_code in variants_data and variants_data[color_code].get('image_url'):
                print(f"Color {color_code} has {len(variants_data[color_code]['image_url'])} images:")
                for img_url in variants_data[color_code]['image_url']:
                    print(f" - {img_url}")

        # Ensure we use the collected color codes to find images
        for color_code in all_color_codes:
            if color_code in variants_data and variants_data[color_code].get('image_url'):
                for image_url in variants_data[color_code]['image_url']:
                    if image_url and image_url not in all_image_urls:
                         # Check if image URL is relative or absolute
                         # If it's a relative path starting with /static/, convert to absolute URL
                         # If it's already an absolute URL (starts with http), use as is
                         if image_url.startswith('/static/'):
                             # Use the absolute path with the domain for Shopify
                             base_url = request.host_url.rstrip('/')
                             full_url = f"{base_url}{image_url}"
                             print(f"Image URL for Shopify (converted from relative): {full_url}")
                         elif image_url.startswith('http'):
                             # Already a full URL
                             full_url = image_url
                             print(f"Image URL for Shopify (already absolute): {full_url}")
                         else:
                             # Unknown format, try to use as is
                             full_url = image_url
                             print(f"Image URL for Shopify (unknown format): {full_url}")
                         
                         # Add to the media list for Shopify
                         images_list = images_list + (('''{mediaContentType:IMAGE,originalSource:"%s"}''' % (full_url.strip(),)) + ',')
                         all_image_urls.add(image_url)
        
        # Remove trailing comma and close bracket
        if images_list.endswith(","):
            images_list = images_list[:-1]
        images_list += "]"
        
        print(f"\n=== Final images_list ===\n{images_list}\n")

        # Construct the full GraphQL mutation for logging and display
        mutation = f'''mutation productCreate {{
          productCreate(input: {{
            title: "{product_name}",
            descriptionHtml: "{description_html}",
            options: ["Color", "Size"],
            variants: {variants_list},
            vendor: "{product_info['brand']}",
            tags: []
          }}, media: {images_list}) {{
            product {{
              id
              title
            }}
            userErrors {{
              field
              message
            }}
          }}
        }}'''

        # Log the mutation for debugging
        print("\n=== SHOPIFY API MUTATION ===")
        print(mutation)
        print("=== END MUTATION ===\n")
        
        # Log to file
        log_file_path = os.path.join(LOGS_DIR, 'shopify_mutations.log')
        with open(log_file_path, 'a') as log_file:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"\n[{timestamp}] MUTATION FOR PRODUCT: {product_name}\n")
            log_file.write(mutation)
            log_file.write("\n" + "-"*80 + "\n")

        # Create product in Shopify
        response = shopify.AddProducts(
            Title=product_name,
            Description=description_html, # Already formatted HTML
            Variants=variants_list,       # Pass the JSON string
            Images=images_list,     # Pass the JSON string
            Vendor=product_info['brand']
        )

        if response:
            # Extract product ID from the response
            product_id = ""
            if isinstance(response, dict) and 'id' in response:
                # The ID might be in the format 'gid://shopify/Product/1234567890'
                # Extract the numeric part at the end
                full_id = response['id']
                if 'gid://shopify/Product/' in full_id:
                    product_id = full_id.replace('gid://shopify/Product/', '')
                else:
                    product_id = full_id
                product_url = f"https://admin.shopify.com/store/sowerbys/products/{product_id}"
            else:
                product_url = "https://admin.shopify.com/store/sowerbys/products"
                
            return jsonify({
                'success': True,
                'message': 'Product created successfully',
                'productUrl': product_url,
                'productId': product_id,
                'openInNewTab': True,
                'shopifyMutation': mutation  # Include the full mutation in the response
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create product in Shopify',
                'shopifyMutation': mutation  # Include the mutation even on failure for debugging
            })

    except Exception as e:
        print(f"Error creating product: {str(e)}")
        return jsonify({'success': False, 'message': f'Error creating product: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, port=5004)
