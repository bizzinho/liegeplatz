from selenium import webdriver
from selenium.webdriver.common.by import By
import os

driver = webdriver.Firefox()
driver.implicitly_wait(10)

URL = "https://www.stadt-zuerich.ch/appl/besys2-ew/hafen/warteliste"
driver.get(URL)
USER = os.environ["USER"]
PWD = os.environ["PWD"]
# lengths to check
LENGTHS = tuple(range(120, 320, 20))


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

    break