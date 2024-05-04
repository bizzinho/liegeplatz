from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import os
from io import StringIO
import pandas as pd

driver = webdriver.Firefox()
driver.implicitly_wait(10)

URL = "https://www.stadt-zuerich.ch/appl/besys2-ew/hafen/warteliste"
driver.get(URL)
USER = os.environ["USER"]
PWD = os.environ["PWD"]
# lengths to check
LENGTHS = tuple(range(120, 320, 20))

# get current table
df = pd.read_csv("liegeplatzData.csv")

userElem = driver.find_element(By.XPATH, "//input[@id='userInputField']")
pwElem = driver.find_element(By.XPATH, "//input[@id='pwInputField']")

userElem.send_keys(USER)
pwElem.send_keys(PWD)

# submit
driver.find_element(By.XPATH, "//button[@type='submit']").click()

# get data
inputFieldXPath = "//input[@id='stzh-input-0']"
submitXPath = "//button[contains(@class, 'stzh-button') and .//*[text()='Abfragen']]"
for l in LENGTHS:
    d = driver.find_element(By.XPATH, inputFieldXPath)
    d.clear()
    d.send_keys(l)
    driver.find_element(By.XPATH, submitXPath).click()
    element = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.XPATH, "//div[@class='stzh-table']"))
    )
    df_loc = pd.read_html(StringIO(driver.page_source))[0]

    df = pd.concat((df, df_loc), ignore_index=True)
