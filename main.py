import requests
import xlwt
from datetime import datetime, timedelta
import os
import imghdr
import sqlite3

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

from flask import Flask, render_template, send_from_directory, request, jsonify

base_url = "https://www.instacart.com"

app = Flask(__name__)

def create_database_table(db_name, table_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    print(table_name)

    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY,
        store_page_link TEXT,
        product_item_page_link TEXT,
        platform TEXT,
        store TEXT,
        product_name TEXT,
        weight_quantity TEXT,
        price TEXT,
        image_file_name TEXT,
        image_link TEXT,
        product_rating TEXT,
        product_review_number TEXT,
        address TEXT,
        phone_number TEXT,
        latitude TEXT,
        longitude TEXT
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()

def insert_product_record(db_name, table_name, record):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    insert_query = f"""
    INSERT INTO {table_name} (store_page_link, product_item_page_link, platform, store, product_name,
        weight_quantity, price, image_file_name, image_link, product_rating, product_review_number,
        address, phone_number, latitude, longitude)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    cursor.execute(insert_query, record)
    conn.commit()
    conn.close()

def get_list(driver, keyword, current_zip_code, db_name, table_name, current_time, prefix):
    scraped_stores = []
    search_url = f"https://www.instacart.com/store/s?k={keyword}&current_zip_code={current_zip_code}"

    driver.get(search_url)
    driver.execute_script("document.body.style.zoom='50%'")
    scroll_to_bottom_multiple_times(driver, 2, 10)
    time.sleep(5)
    stores = driver.find_elements(By.CLASS_NAME, "e-14qbqkc")
    
    for store in stores:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", store)
            link_element = store.find_element(By.XPATH, ".//a[contains(@class, 'e-8sr6ht') or contains(@class, 'e-h91tqw')]")

            link = link_element.get_dom_attribute("href")
            print(link)

            store_title_element = store.find_element(By.CLASS_NAME, "e-ji0c6k")
            store_title = store_title_element.text.strip()
            print(store_title)

            scraped_stores.append({"url": f"{base_url}{link}", "title": store_title})
        except:
            print("Error")
    products = get_products(driver, scraped_stores, keyword, current_zip_code, db_name, table_name, current_time, prefix)
    return products

def scroll_to_bottom_multiple_times(driver, scroll_pause_time=2, max_scrolls=10):
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    while scroll_count < max_scrolls:
        # Scroll down to the bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)  # Wait for new content to load

        # Calculate new scroll height and check if we've reached the bottom
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # Exit loop if no new content loads
        last_height = new_height
        scroll_count += 1

def get_products(driver, stores, keyword, current_zip_code, db_name, table_name, current_time, prefix):
    section_id = 1
    products = []
    store_num = 0
    for store in stores:
        if(store_num >= 10):
            break
        driver.get(store["url"])
        # driver.execute_script("document.body.style.zoom='25%'")
        scroll_to_bottom_multiple_times(driver, 2, 80)
        time.sleep(5)
        elements = driver.find_elements(By.XPATH, "//div[@aria-label='Product']")
        num = 0
        
        for element in elements:
            if(num >= 5):
                break

            image_url = ""
            title = ""
            rating = ""
            rating_count = ""
            product_link = ""
            price = ""
            download_url = ""
            weight = ""

            driver.execute_script("arguments[0].scrollIntoView();", element)

            try:
                img_element = element.find_element(By.TAG_NAME, "img")
                image_url = img_element.get_attribute("srcset").split(", ")[0]
            except:
                image_url = ""
            
            if(image_url):
                try:
                    responseImage = requests.get(image_url)
                    image_type = imghdr.what(None, responseImage.content)
                    if responseImage.status_code == 200:
                        img_url = "products/"+current_time+"_"+keyword+"_"+current_zip_code+"/images/"+prefix+str(section_id)+'.'+image_type
                        with open(img_url, 'wb') as file:
                            file.write(responseImage.content)
                            download_url = img_url
                    # download_url = "products/"+current_time+"_"+keyword+"_"+current_zip_code+"/images/"+prefix+str(section_id)+'.'+"jpg"
                except Exception as e:
                    print(e)
            try:
                title_element = element.find_element(By.CLASS_NAME, "e-1pnf8tv")
                title = title_element.text.strip()
            except:
                title = ""

            try:
                weight_element = element.find_element(By.CLASS_NAME, "e-zjik7")
                weight = weight_element.text.strip()
            except:
                weight = ""
            
            try:
                product_link_element = element.find_element(By.TAG_NAME, "a")
                product_link = product_link_element.get_attribute("href")
            except:
                product_link = ""

            try:
                informations = element.find_element(By.CLASS_NAME, "screen-reader-only").text
                price_splits = informations.split(":")
                price = price_splits[1].strip()
            except:
                price = ""

            record = [
                str(section_id),
                "https://instacart.com",
                product_link,
                "Instacart",
                store["title"],
                "",
                title,
                weight,
                "",
                price,
                download_url,
                image_url,
                "",
                "",
                rating,
                rating_count,
                "50 Beale St # 600, San Francisco, California 94105, US",
                "+18882467822",
                "37.7914",
                "122.3960",
                "",
            ]

            db_record = (
                "https://instacart.com",
                product_link,
                "Instacart",
                store["title"],
                title,
                weight,
                price,
                download_url,
                image_url,
                "",
                "",
                "50 Beale St # 600, San Francisco, California 94105, US",
                "+18882467822",
                "37.7914",
                "122.3960",
            )

            insert_product_record(db_name, table_name, db_record)
            
            products.append(record)
            print(record)
            section_id = section_id + 1
            num = num + 1

        store_num = store_num + 1

    driver.quit()

    return products

@app.route('/')
def index():
    db_name = "product_data.db"
    page = request.args.get('page', 1, type=int)
    
    # Function to fetch table names
    def get_table_names(db_name):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return [table[0] for table in tables]

    # Fetch the table names
    table_names = get_table_names(db_name)

    # Pass the table names to the template
    return render_template('index.html', table_names=table_names, page=page, total_pages=0)

@app.route('/products/<table_name>')
def get_products_by_table(table_name):
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Number of products per page
    db_name = "product_data.db"

    def get_table_names(db_name):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return [table[0] for table in tables]
    
    # Function to fetch product data from a specific table with pagination
    def get_products_from_table(db_name, table_name, page, per_page):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        offset = (page - 1) * per_page  # Calculate the offset for pagination
        
        cursor.execute(f"""
            SELECT store, product_name, price, image_file_name, product_item_page_link 
            FROM {table_name}
            WHERE price IS NOT NULL AND price != ''
            ORDER BY CAST(REPLACE(REPLACE(price, '$', ''), ',', '') AS FLOAT) ASC
            LIMIT {per_page} OFFSET {offset}
        """)
        products = cursor.fetchall()
        conn.close()
        return products

    # Fetch the products for the selected table
    products = get_products_from_table(db_name, table_name, page, per_page)
    
    # Fetch total number of products to calculate total pages
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE price IS NOT NULL AND price != ''")
    total_products = cursor.fetchone()[0]
    conn.close()

    total_pages = (total_products // per_page) + (1 if total_products % per_page != 0 else 0)

    # Return the template with the products and pagination info
    return render_template(
        'index.html', 
        table_names=get_table_names(db_name), 
        products=products, 
        selected_table=table_name,
        page=page,
        total_pages=total_pages
    )

@app.route('/products/<path:filename>')
def serve_products(filename):
    return send_from_directory('products', filename)

@app.route('/get_products', methods=['GET'])
def get_products_api():
    keyword = request.args.get("keyword", "").strip()
    current_zip_code = request.args.get("zip_code", "").strip()

    options = uc.ChromeOptions()
    # options.add_argument("--headless=new")  # Enable headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--start-maximized")  # Debugging support
    driver = uc.Chrome(options=options)
    titleData = ["id","Store page link", "Product item page link", "Platform", "Store", "Product_description", "Product Name", "Weight/Quantity", "Units/Counts", "Price", "image_file_names", "Image_Link", "Store Rating", "Store Review number", "Product Rating", "Product Review number", "Address", "Phone number", "Latitude", "Longitude", "Description Detail"]
    widths = [10,50,50,60,45,70,35,25,25,20,130,130,30,30,30,30,60,50,60,60,80]
    style = xlwt.easyxf('font: bold 1; align: horiz center')
    
    if(not os.path.isdir("products")):
        os.mkdir("products")

    now = datetime.now()
    current_time = now.strftime("%m_%d_%Y_%H_%M_%S")
    prefix = now.strftime("%Y%m%d%H%M%S%f_")
    os.mkdir("products/"+current_time+"_"+keyword+"_"+current_zip_code)
    os.mkdir("products/"+current_time+"_"+keyword+"_"+current_zip_code+"/images")

    db_name = "product_data.db"
    table_name = f"search_{current_time}_{keyword.replace(' ', '_')}"
    
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('Sheet1')
    
    for col_index, value in enumerate(titleData):
        first_col = sheet.col(col_index)
        first_col.width = 256 * widths[col_index]  # 20 characters wide
        sheet.write(0, col_index, value, style)
    
    create_database_table(db_name, table_name)
    records = get_list(driver=driver, keyword=keyword, current_zip_code=current_zip_code, db_name=db_name, table_name=table_name, current_time=current_time, prefix=prefix)
        
    for row_index, row in enumerate(records):
        for col_index, value in enumerate(row):
            sheet.write(row_index+1, col_index, value)

    # Save the workbook
    workbook.save("products/"+current_time+"_"+keyword+"_"+current_zip_code+"/products.xls")
    return jsonify({"response": True})

if __name__ == "__main__":
    app.run(threaded=True,)



