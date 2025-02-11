from flask import Flask, request, jsonify, render_template, redirect, url_for
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import smtplib
import time

app = Flask(__name__)

# Function to scrape Amazon
def scrape_amazon(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, "html.parser")
        price = soup.find("span", {"class": "a-price-whole"})
        return float(price.text.replace(',', '').strip()) if price else None
    except Exception:
        return None

# Function to scrape Ajio
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
    except Exception:
        return None
    finally:
        driver.quit()

# Function to scrape BestBuy
def scrape_bestbuy(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, "html.parser")
        price = soup.find("div", {"class": "priceView-hero-price priceView-customer-price"})
        return float(price.text.replace('$', '').replace(',', '').strip()) if price else None
    except Exception:
        return None

# Function to send email
def send_email(receiver_email, subject, message):
    sender_email = "ushushruth@gmail.com"
    app_password = "sdkaztjyrkftbggp"  # Store securely
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

@app.route("/track", methods=["POST"])
def track_price():
    data = request.json
    url = data.get("url")
    target_price = float(data.get("target_price"))
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
