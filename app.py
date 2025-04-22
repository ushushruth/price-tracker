
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
# --- Chrome Options Setup (Common for Selenium scrapers) ---

def get_chrome_options():
    chrome_options = Options()
    # Standard options to make Selenium look less like a bot
    chrome_options.add_argument("--headless") # Run in headless mode
    chrome_options.add_argument("--disable-gpu") # Disable GPU hardware acceleration
    chrome_options.add_argument("--no-sandbox") # Bypass OS security model, required for some environments
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
    chrome_options.add_argument("--window-size=1920,1080") # Specify window size
    # More sophisticated options to counter detection
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    return chrome_options

# Scraper for Myntra
# --- Scraper for Myntra (using Selenium - updated wait logic slightly) ---
def scrape_myntra(url):
    chrome_options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    product_data = { "name": None, "price": None, "rating": None, "details": None }

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20) # Increased wait time

        # Scrape Name
        try:
            name_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "pdp-name")))
            product_data["name"] = name_element.text.strip()
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Myntra Scraper: Name not found or timed out. Error: {e}")

        # Scrape Rating
        try:
            # Rating might load slightly later or be absent
            rating_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "index-overallRating")))
            # Clean rating text (assuming it might have extra characters)
            rating_text = rating_element.text.strip()
            rating_match = re.search(r'\d+\.?\d*', rating_text) # Find the first number
            if rating_match:
                product_data["rating"] = float(rating_match.group())
        except (TimeoutException, NoSuchElementException) as e:
             print(f"Myntra Scraper: Rating not found or timed out. Error: {e}")
             product_data["rating"] = "Not Available" # Handle missing rating

        # Scrape Price
        try:
            price_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "pdp-price")))
            price_text = price_element.text.replace('₹', '').replace(',', '').strip()
            # Find the first price value if multiple exist (e.g., discounted price)
            price_match = re.search(r'\d+\.?\d*', price_text)
            if price_match:
                 product_data["price"] = float(price_match.group())
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Myntra Scraper: Price not found or timed out. Error: {e}")

        # Scrape Details
        try:
            details_section = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pdp-product-description-content")))
            items = details_section.find_elements(By.TAG_NAME, "li")
            product_data["details"] = [item.text.strip() for item in items if item.text.strip()]
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Myntra Scraper: Details not found or timed out. Error: {e}")
            product_data["details"] = [] # Return empty list if details not found

        return product_data

    except Exception as e:
        print(f"Myntra Scraper Error: An unexpected error occurred: {e}")
        return None
    finally:
        driver.quit()


# --- Scraper for Amazon (using requests/BeautifulSoup - likely more stable) ---
def scrape_amazon(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Connection": "keep-alive",
        "DNT": "1", # Do Not Track Request Header
        "Upgrade-Insecure-Requests": "1"
    }
    product_data = { "name": None, "price": None, "rating": None, "details": None }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, "html.parser")

        # Scrape Name
        name_element = soup.select_one("#productTitle")
        if name_element:
            product_data["name"] = name_element.text.strip()
        else:
             print("Amazon Scraper: Name not found.")

        # Scrape Price
        # Try different selectors as Amazon varies its structure
        price_element = soup.select_one("span.a-price-whole")
        if not price_element:
             price_element = soup.select_one("span.a-price .a-offscreen") # Another common pattern
        if price_element:
            price_text = price_element.text.replace('₹', '').replace(',', '').strip()
            price_match = re.search(r'\d+\.?\d*', price_text)
            if price_match:
                product_data["price"] = float(price_match.group())
        else:
            print("Amazon Scraper: Price not found.")


        # Scrape Rating
        rating_element = soup.select_one("span[data-hook='rating-out-of-text']") # Preferred selector
        if not rating_element:
             rating_element = soup.select_one("i.a-icon-star span.a-icon-alt") # Alternative
        if rating_element:
            rating_text = rating_element.text.strip()
            # Extract the number (e.g., "4.5 out of 5 stars" -> 4.5)
            rating_match = re.search(r'\d+\.?\d*', rating_text)
            if rating_match:
                product_data["rating"] = float(rating_match.group())
        else:
            print("Amazon Scraper: Rating not found.")
            product_data["rating"] = "Not Available"

        # Scrape Details
        details_list = soup.select("#feature-bullets ul.a-unordered-list li span.a-list-item")
        if details_list:
            product_data["details"] = [item.text.strip() for item in details_list if item.text.strip()]
        else:
            print("Amazon Scraper: Details not found.")
            product_data["details"] = []

        return product_data

    except requests.exceptions.RequestException as e:
        print(f"Amazon Scraper Error: Request failed: {e}")
        return None
    except Exception as e:
        print(f"Amazon Scraper Error: An unexpected error occurred: {e}")
        return None
    

    
# --- Updated Scraper for Ajio (using Selenium) ---
def scrape_ajio(url):
    chrome_options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    product_data = { "name": None, "price": None, "rating": None, "details": None }

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 25) # Increased wait time significantly for Ajio

        # Scrape Name
        try:
            name_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "prod-name")))
            product_data["name"] = name_element.text.strip()
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Ajio Scraper: Name not found or timed out. Error: {e}")

        # Scrape Price
        try:
            price_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "prod-sp")))
            price_text = price_element.text.replace('₹', '').replace(',', '').strip()
            price_match = re.search(r'\d+\.?\d*', price_text)
            if price_match:
                product_data["price"] = float(price_match.group())
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Ajio Scraper: Price not found or timed out. Error: {e}")

        # Scrape Rating
        try:
            # Use XPath for potentially more stable targeting within the rating structure
            # Wait for the container first
            rating_container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rating-popup")))
            # Then find the specific span with the rating number
            rating_element = rating_container.find_element(By.XPATH, ".//span[contains(@class, '_3c5q0')]")
            rating_text = rating_element.text.strip()
            rating_match = re.search(r'\d+\.?\d*', rating_text) # Extract number
            if rating_match:
                product_data["rating"] = float(rating_match.group())
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Ajio Scraper: Rating not found or timed out. Error: {e}")
            product_data["rating"] = "Not Available"

        # Scrape Details
        try:
            # Wait for the container of the details list
            details_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.prod-desc ul.prod-list")))
            # Find all 'li' elements with class 'detail-list' within that container
            items = details_container.find_elements(By.CSS_SELECTOR, "li.detail-list")
            # Filter out empty strings and potentially unwanted list items
            details = [item.text.strip() for item in items if item.text.strip() and "About" not in item.text and "Product Code:" not in item.text]
            product_data["details"] = details
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Ajio Scraper: Details not found or timed out. Error: {e}")
            product_data["details"] = []

        return product_data

    except Exception as e:
        print(f"Ajio Scraper Error: An unexpected error occurred: {e}")
        return None
    finally:
        driver.quit()


# --- Updated Scraper for Flipkart (using Selenium) ---
def scrape_flipkart(url):
    chrome_options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    product_data = { "name": None, "price": None, "rating": None, "details": None }

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20) # Increased wait time

        # Scrape Name
        try:
            # Use CSS Selector which might be more stable than just class name
            name_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "span.VU-ZEz")))
            product_data["name"] = name_element.text.strip()
        except (TimeoutException, NoSuchElementException) as e:
             print(f"Flipkart Scraper: Name not found or timed out. Error: {e}")
             # Fallback attempt with potentially different selector if needed
             try:
                 name_element = driver.find_element(By.XPATH, "//h1/span[contains(@class, 'VU-ZEz')]") # Example XPATH
                 product_data["name"] = name_element.text.strip()
             except NoSuchElementException:
                  print(f"Flipkart Scraper: Name fallback also failed.")


        # Scrape Price
        try:
            price_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.Nx9bqj")))
            price_text = price_element.text.replace('₹', '').replace(',', '').strip()
            price_match = re.search(r'\d+\.?\d*', price_text)
            if price_match:
                product_data["price"] = float(price_match.group())
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Flipkart Scraper: Price not found or timed out. Error: {e}")

        # Scrape Rating
        try:
            # Wait specifically for the rating div
            rating_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.XQDdHH")))
            rating_text = rating_element.text.strip()
            rating_match = re.search(r'\d+\.?\d*', rating_text) # Extract just the number
            if rating_match:
                product_data["rating"] = float(rating_match.group())
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Flipkart Scraper: Rating not found or timed out. Error: {e}")
            product_data["rating"] = "Not Available"

        # Scrape Details (Highlights)
        try:
            # Wait for the container div first
            details_container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "xFVion")))
            # Find list items within that container
            items = details_container.find_elements(By.CSS_SELECTOR, "li._7eSDEz")
            product_data["details"] = [item.text.strip() for item in items if item.text.strip()]
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Flipkart Scraper: Details (Highlights) not found or timed out. Error: {e}")
            # Fallback: Sometimes details are in a different structure
            try:
                 details_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, '_4gvKMe'))) # Look for description div
                 items = details_div.find_elements(By.TAG_NAME, "p") # Paragraphs in description
                 if items:
                      product_data["details"] = [item.text.strip() for item in items if item.text.strip()]
                 else: # Try another common pattern
                      items = details_div.find_elements(By.CSS_SELECTOR, "div > ul > li")
                      product_data["details"] = [item.text.strip() for item in items if item.text.strip()]

            except (TimeoutException, NoSuchElementException) as e2:
                  print(f"Flipkart Scraper: Details fallback also failed. Error: {e2}")
                  product_data["details"] = []


        return product_data

    except Exception as e:
        print(f"Flipkart Scraper Error: An unexpected error occurred: {e}")
        return None
    finally:
        driver.quit()



# --- Scraper for Meesho (using Selenium - review selectors if needed) ---
def scrape_meesho(url):
    chrome_options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    product_data = { "name": None, "price": None, "rating": None, "details": None }

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20) # Increased wait time

        # Scrape Price (Update class name if it has changed)
        try:
             price_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "h4.biMVPh"))) # Example: using h4 tag if class alone isn't unique
             price_text = price_element.text.replace('₹', '').replace(',', '').strip()
             price_match = re.search(r'\d+\.?\d*', price_text)
             if price_match:
                  product_data["price"] = float(price_match.group())
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Meesho Scraper: Price not found or timed out (tried 'h4.biMVPh'). Error: {e}")

        # Scrape Name (Update class name if it has changed)
        try:
             name_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "span.fhfLdV")))
             product_data["name"] = name_element.text.strip()
        except (TimeoutException, NoSuchElementException) as e:
             print(f"Meesho Scraper: Name not found or timed out (tried 'span.fhfLdV'). Error: {e}")

        # Scrape Rating (Update class name/structure if it has changed)
        try:
            rating_element_container = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div[class*='Rating__StyledRating']"))) # Example using partial class match
            rating_text_element = rating_element_container.find_element(By.TAG_NAME, "span") # Assuming rating is in a span inside
            rating_text = rating_text_element.text.strip()
            rating_match = re.search(r'\d+\.?\d*', rating_text)
            if rating_match:
                 product_data["rating"] = float(rating_match.group())
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Meesho Scraper: Rating not found or timed out. Error: {e}")
            product_data["rating"] = "Not Available"


        # Scrape Details (Update class name/structure if it has changed)
        try:
            # Often in divs with specific structure, might need XPath
            details_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'ProductDetails__Detail')]/p[contains(@class, 'Paragraph')]"))) # Example XPath
            product_data["details"] = [item.text.strip() for item in details_elements if item.text.strip()]
            if not product_data["details"]: # Fallback if above fails
                 details_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-iBYQkv"))) # Original user attempt
                 items = details_container.find_elements(By.CSS_SELECTOR, "pre") # Original user attempt
                 product_data["details"] = [item.text.strip() for item in items if item.text.strip()]

        except (TimeoutException, NoSuchElementException) as e:
            print(f"Meesho Scraper: Details not found or timed out. Error: {e}")
            product_data["details"] = []


        return product_data

    except Exception as e:
        print(f"Meesho Scraper Error: An unexpected error occurred: {e}")
        return None
    finally:
        driver.quit()



# Function to send email
def send_email(receiver_email, subject, message):
    sender_email = "sayutracker@gmail.com"
    app_password = "wttlebjkwwelabyl"  # Store securely
    text = f"Subject: {subject}\n\n{message}"
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
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