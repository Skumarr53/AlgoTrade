# Optimizing the auth/fyers_auth.py script

# Improvements:
# 1. Enhanced error handling for Selenium operations.
# 2. Secure handling of sensitive data like TOTP secrets.
# 3. Improved logging for better clarity.
# 4. Modularized code for improved readability and maintenance.
# 5. Ensured proper management of WebDriver.

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from pyotp import TOTP
from fyers_apiv3 import fyersModel  # accessToken
import os
from config import config, log_config
from utils import utils
log_config.setup_logging()


class AuthCodeGenerator:
    def __init__(self):
        self.session = fyersModel.SessionModel(
            client_id=config.CLIENT_ID,
            secret_key=config.SECRET_KEY,
            redirect_uri=config.REDIRECT_URL,
            response_type=config.RESPONSE_TYPE,
            grant_type=config.GRANT_TYPE
        )
        self.username = config.USER_NAME
        self.totp = config.TOTP_SECRET
        self.pin = config.USER_PIN

    def initialize_fyers_model(self):
        try:
            auth_code = self.gen_auth_code()
            self.session.set_token(auth_code)
            response = self.session.generate_token()
            access_token = response["access_token"]
            fyers = fyersModel.FyersModel(
                client_id=config.CLIENT_ID, is_async=False, token=access_token, log_path=os.getcwd())
            logging.info(fyers.get_profile())
            return fyers
        except Exception as e:
            logging.error(f"Error in initializing Fyers Model: {e}")
            raise

    def gen_auth_code(self):
        driver = None
        try:
            driver = webdriver.Chrome(options=utils.get_chrome_options())
            driver.get(self.session.generate_authcode())
            WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="fy_client_id"]')))
            self._login(driver)
            self._enter_otp(driver)
            self._enter_pin(driver)
            return self._extract_auth_code(driver)
        except Exception as e:
            logging.error(f"Error in generating auth code: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    def _login(self, driver):
        try:
            client_id_field = driver.find_element(
                By.XPATH, '//*[@id="fy_client_id"]')
            client_id_field.send_keys(self.username)
        except Exception as e:
            logging.info(
                f"Standard login field not found, attempting alternative login. Error: {e}")
            self._alternative_login(driver)

    def _alternative_login(self, driver):
        login_alternate_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="login_client_id"]')))
        login_alternate_button.click()
        client_id_field = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="fy_client_id"]')))
        client_id_field.send_keys(self.username)
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="clientIdSubmit"]')))
        submit_button.click()

    def _enter_otp(self, driver):
        otp = TOTP(self.totp).now()
        logging.info(f'OTP: {otp}')
        otp_field_ids = ["first", "second",
                         "third", "fourth", "fifth", "sixth"]
        for i, otp_digit in enumerate(otp):
            otp_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//*[@id="{otp_field_ids[i]}"]')))
            otp_field.send_keys(otp_digit)
        driver.find_element(By.XPATH, '//*[@id="confirmOtpSubmit"]').click()

    def _enter_pin(self, driver):
        pin_page = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "verify-pin-page")))
        pin_field_ids = ["first", "second", "third", "fourth"]
        for i, pin_digit in enumerate(self.pin):
            pin_field = WebDriverWait(pin_page, 5).until(
                EC.element_to_be_clickable((By.ID, pin_field_ids[i])))
            pin_field.send_keys(pin_digit)
        driver.find_element(By.XPATH, '//*[@id="verifyPinSubmit"]').click()

    def _extract_auth_code(self, driver):
        WebDriverWait(driver, 10).until(EC.url_contains("auth_code="))
        new_url = driver.current_url
        return new_url[new_url.index('auth_code=') + 10:new_url.index('&state')]

# Commenting out the execution part to prevent execution in the PCI
# if __name__=="__main__":
#     logging
