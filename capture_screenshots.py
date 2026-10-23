import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

def capture_ui_screenshots():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        print("[INFO] Navigating to http://localhost:8501...")
        driver.get("http://localhost:8501")
        time.sleep(5)

        driver.save_screenshot("screenshots/1_app_overview.png")
        print("[SUCCESS] Saved screenshots/1_app_overview.png")

        # Test Question 1: Supported
        text_area = driver.find_element(By.TAG_NAME, "textarea")
        text_area.click()
        text_area.send_keys(Keys.COMMAND, 'a')
        text_area.send_keys(Keys.BACKSPACE)
        q1 = "How long does a proprietor have copyright in a registered design, and can it be extended?"
        text_area.send_keys(q1)
        time.sleep(1)

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Ask Question" in b.text:
                b.click()
                break

        print("[INFO] Waiting for Question 1 response...")
        time.sleep(14)  # Give enough time for embedding + Gemini inference
        driver.save_screenshot("screenshots/2_supported_question_1.png")
        print("[SUCCESS] Saved screenshots/2_supported_question_1.png")

        # Refresh page for Question 3
        driver.get("http://localhost:8501")
        time.sleep(4)
        text_area = driver.find_element(By.TAG_NAME, "textarea")
        text_area.click()
        text_area.send_keys(Keys.COMMAND, 'a')
        text_area.send_keys(Keys.BACKSPACE)
        q3 = "What is the government fee to register a trademark?"
        text_area.send_keys(q3)
        time.sleep(1)

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            if "Ask Question" in b.text:
                b.click()
                break

        print("[INFO] Waiting for Question 3 response...")
        time.sleep(12)
        driver.save_screenshot("screenshots/3_unsupported_question_3.png")
        print("[SUCCESS] Saved screenshots/3_unsupported_question_3.png")

    finally:
        driver.quit()

if __name__ == "__main__":
    capture_ui_screenshots()
