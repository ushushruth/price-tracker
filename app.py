
from flask import Flask, request, jsonify, render_template, redirect, url_for
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from requests_html import HTMLSession
import smtplib
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from requests_html import HTMLSession
import smtplib
import time
import sqlite3
import re


app = Flask(__name__)

# Function to connect to the database
def connect_db():
    return sqlite3.connect("D:/database/databse.db")
#create table

def create_table():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Sayu (
                SayuID INTEGER PRIMARY KEY AUTOINCREMENT,
                Email TEXT NOT NULL,
                AlertPrice REAL NOT NULL CHECK(AlertPrice > 0),
                URL TEXT NOT NULL,
                ProductName TEXT
            )
        ''')
        conn.commit()


create_table()


# Scraper for Myntra
def scrape_myntra(url):
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        wait = WebDriverWait(driver, 10)

        name = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pdp-name"))).text.strip()
        rating = driver.find_element(By.CLASS_NAME, "index-overallRating").text.strip()
        price = driver.find_element(By.CLASS_NAME, "pdp-price").text.replace("₹", "").replace(",", "").strip()
        details = [el.text.strip() for el in driver.find_elements(By.CLASS_NAME, "pdp-product-description-content li")]

        productdata1={"name": name, "price": float(price), "rating": float(rating), "details": details}
        return productdata1
    except Exception as e:
        print("Myntra Error:", e)
        return None
    finally:
        driver.quit()


# Scraper for Amazon
def scrape_amazon(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        soup = BeautifulSoup(requests.get(url, headers=headers).content, "html.parser")
        name = soup.select_one("#productTitle").get_text(strip=True)
        price = soup.select_one(".a-price-whole")
        rating = soup.select_one("span.a-icon-alt")

        price_value = float(price.get_text(strip=True).replace(",", "")) if price else None
        rating_value = float(rating.get_text(strip=True).split()[0]) if rating else 0.0

      #  details = [el.get_text(strip=True) for el in soup.select("ul.a-unordered-list span.a-list-item")]
        details = [el.get_text(strip=True) for el in soup.select("#feature-bullets ul.a-unordered-list span.a-list-item")]


        productdata1 ={"name": name, "price": price_value, "rating": rating_value, "details": details}
        return productdata1
    except Exception as e:
        print("Amazon Error:", e)
        return None


# Scraper for Ajio
def scrape_ajio(url):
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(5)

        name = driver.find_element(By.CLASS_NAME, "prod-name").text.strip()
        price = re.search(r'\d+', driver.find_element(By.CLASS_NAME, "prod-sp").text.replace(",", "")).group()
        try:
            rating = driver.find_element(By.CLASS_NAME, "_1P7MF").text.strip()
        except:
            rating = "0"

        details = [d.text.strip() for d in driver.find_elements(By.CLASS_NAME, "prod-list")]

        productdata1= {"name": name, "price": float(price), "rating": float(rating), "details": details}
        return productdata1
    except Exception as e:
        print("Ajio Error:", e)
        return None
    finally:
        driver.quit()


# Scraper for Flipkart
def scrape_flipkart(url):
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(5)

        name = driver.find_element(By.CLASS_NAME, "VU-ZEz").text.strip()
        price = driver.find_element(By.CLASS_NAME, "Nx9bqj").text.replace("₹", "").replace(",", "").strip()
        rating = driver.find_element(By.CLASS_NAME, "ipqd2A").text.strip()
        details = [el.text.strip() for el in driver.find_elements(By.CLASS_NAME, "_7eSDEz")]

        productdata1= {"name": name, "price": float(price), "rating": float(rating), "details": details}
        return productdata1
    except Exception as e:
        print("Flipkart Error:", e)
        return None
    finally:
        driver.quit()


# Scraper for Meesho
def scrape_meesho(url):
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(5)

        name = driver.find_element(By.CLASS_NAME, "fhfLdV").text.strip()
        price = driver.find_element(By.CLASS_NAME, "biMVPh").text.replace("₹", "").replace(",", "").strip()
        rating = driver.find_element(By.CLASS_NAME, "laVOtN").text.strip()
        details = [el.text.strip() for el in driver.find_elements(By.CLASS_NAME, "pre")]

        productdata1= {"name": name, "price": float(price), "rating": float(rating), "details": details}
        return productdata1
    except Exception as e:
        print("Meesho Error:", e)
        return None
    finally:
        driver.quit()


# Scraper for BestBuy (price only)
def scrape_bestbuy(url):
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.bestbuy.com/")
        time.sleep(2)
        driver.add_cookie({"name": "intl_splash", "value": "true", "domain": ".bestbuy.com"})
        driver.get(url.replace("www.bestbuy.com", "www.bestbuy.com/site"))
        time.sleep(5)

        price_text = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.priceView-hero-price span[aria-hidden="true"]'))
        ).text.strip()

        productdata1= {"name": "BestBuy Product", "price": float(price_text.replace("$", "").replace(",", "")), "rating": 0.0, "details": []}
        return productdata1
    except Exception as e:
        print("BestBuy Error:", e)
        return None
    finally:
        driver.quit()



# Function to send email
def send_email(receiver_email, subject, message):
    sender_email = "ushushruth@gmail.com"
    app_password = "abnumazbcqflcanw"  # Store securely
    text = f"Subject: {subject}\n\n{message}"
    try:
        server = smtplib.SMTP("smtp.gmail.com", 465)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        return True
    except Exception:
        return False
    
@app.route("/")
def home():
    return render_template("home1.html")

@app.route("/track-page")
def track_page():
    return render_template("track.html")
@app.route("/p-details")
def p_details():
    return render_template("pdetails.html")
@app.route("/p-details", methods=["POST"])
@app.route("/p-details", methods=["POST"])
def get_product_details():
    data1 = request.json
    url1 = data1.get("productURL")
    product_data = None

    if "amazon" in url1:
        product_data = scrape_amazon(url1)
    elif "flipkart" in url1:
        product_data = scrape_flipkart(url1)
    elif "meesho" in url1:
        product_data = scrape_meesho(url1)
    elif "ajio" in url1:
        product_data = scrape_ajio(url1)

    if product_data:
        return jsonify(product_data)
    else:
        return jsonify({"error": "Failed to fetch product details"}), 500

    
        
    


@app.route("/track-page", methods=["POST"])
def track_price():
    data = request.json
    url = data.get("url")
    target_price = float(data.get("price"))
    receiver_email = data.get("email")

    if not url or not target_price or not receiver_email:
        return jsonify({"error": "Missing required fields"}), 400

    price = None
    if "amazon" in url:
        price_data = scrape_amazon(url)
        if price_data:
            price=price_data.get("price")
    elif "ajio" in url:
        price_data = scrape_ajio(url)
        if price_data:
            price=price_data.get("price")
    elif "bestbuy" in url:
        price_data = scrape_bestbuy(url)
        if price_data:
            price=price_data.get("price")
    elif "flipkart" in url:
        price_data = scrape_flipkart(url)
        if price_data:
            price=price_data.get("price")
    elif "meesho" in url:
        price_data=scrape_meesho(url)
        if price_data:
            price=price_data.get("price")
    elif "myntra" in url:
        price_data=scrape_myntra(url)
        if price_data:
            price=price_data.get("price")
    
    else:
        return jsonify({"error": "Unsupported website"}), 400
    


    if price:
        product_name = price_data.get("name")
        try:
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO Sayu (Email, AlertPrice, URL, ProductName) VALUES (?, ?, ?, ?)",
                    (receiver_email, target_price, url, product_name)
                )
                conn.commit()
        except Exception as e:
            print("Database Insert Error:", str(e))

        if price <= target_price:
            email_sent = send_email(receiver_email, "Price Drop Alert!", f"The price of your product has dropped to {price}. Buy now: {url}")
            return jsonify({"message": "Price dropped! Email sent.", "price": price, "email_sent": email_sent})
        
        return jsonify({"message": "Price is still above target.", "price": price})
        
    
    return jsonify({"error": "Could not retrieve the price"}), 500

if __name__ == "__main__":
    app.run(debug=True)