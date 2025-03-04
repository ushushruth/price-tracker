
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


app = Flask(__name__)

# Scraper for Amazon
def scrape_amazon(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, "html.parser")
        price = soup.find("span", {"class": "a-price-whole"})
        return float(price.text.replace(',', '').strip()) if price else None
    except Exception as e:
        print("Amazon Scraper Error:", str(e))
        return None


# Scraper for Ajio
def scrape_ajio(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        time.sleep(5)
        price_element = driver.find_element(By.CLASS_NAME, "prod-sp")
        price = price_element.text.replace('₹', '').replace(',', '').strip()
        return float(price) if price else None
    except Exception as e:
        print("Ajio Scraper Error:", str(e))
        return None
    finally:
        driver.quit()

#Best-buy Scaraping(Not working)
def scrape_bestbuy(url):
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-geolocation")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://www.bestbuy.com/")
        time.sleep(2)

        driver.add_cookie({
            "name": "intl_splash",
            "value": "true",
            "domain": ".bestbuy.com"
        })
        print("Cookie set to bypass location selection.")

        url = url.replace("www.bestbuy.com", "www.bestbuy.com/site")

        driver.get(url)
        time.sleep(5)

        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(2)

        wait = WebDriverWait(driver, 15)
        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.priceView-hero-price.priceView-customer-price span[aria-hidden="true"]'))
        )

        price_text = price_element.text.strip()
        return float(price_text.replace("$", "").replace(",", ""))

    except Exception as e:
        print("BestBuy Scraper Error:", str(e))
        return None

    finally:
        driver.quit()





# Scraper for Flipkart
def scrape_flipkart(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, features="lxml")
        
        # Extract the price using the class name
        price_element = soup.find("div", class_="Nx9bqj CxhGGd")
        
        if price_element:
            price_text = price_element.text.replace('₹', '').replace(',', '').strip()
            return float(price_text)
        
        print("Flipkart Price Element Not Found.")
        return None
    
    except Exception as e:
        print("Flipkart Scraper Error:", str(e))
        return None


# Function to send email
def send_email(receiver_email, subject, message):
    sender_email = "ushushruth@gmail.com"
    app_password = "irhdjyowmrofsbag"  # Store securely
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
        price = scrape_amazon(url)
    elif "ajio" in url:
        price = scrape_ajio(url)
    elif "bestbuy" in url:
        price = scrape_bestbuy(url)
    elif "flipkart" in url:
        price=scrape_flipkart(url)
    else:
        return jsonify({"error": "Unsupported website"}), 400
    


    if price:
        if price <= target_price:
            email_sent = send_email(receiver_email, "Price Drop Alert!", f"The price of your product has dropped to {price}. Buy now: {url}")
            return jsonify({"message": "Price dropped! Email sent.", "price": price, "email_sent": email_sent})
        return jsonify({"message": "Price is still above target.", "price": price})
        
    
    return jsonify({"error": "Could not retrieve the price"}), 500

if __name__ == "__main__":
    app.run(debug=True)
