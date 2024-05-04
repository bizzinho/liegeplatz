from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import os
from io import StringIO, BytesIO
import pandas as pd
from cryptography.fernet import Fernet
import time


URL = "https://www.stadt-zuerich.ch/appl/besys2-ew/hafen/warteliste"

USER = os.environ["USER"]
PWD = os.environ["PWD"]
# lengths to check
LENGTHS = tuple(range(120, 320, 20))


def getKey() -> Fernet:
    """Get Fernet key.

    Key must be stored in 'key.key. in local folder.
    Returns:
        Fernet: The Fernet key used to de-/encrypt data.
    """
    # get Fernet key
    with open("key.key", "rb") as f:
        KEY = Fernet(f.read())

    return KEY


def readAndDecrypt(KEY: Fernet | None = None) -> pd.DataFrame:
    """Read and decrypt current dataset in 'liegePlatzData.encrypted'.

    Args:
        KEY (Fernet | None, optional): The Fernet key. Defaults to None.

    Returns:
        pd.DataFrame: The (unencrypted) complete dataset.
    """
    if KEY is None:
        KEY = getKey()

    # decrypt
    try:
        with open("liegePlatzData.encrypted", "rb") as f:
            df = pd.read_csv(BytesIO(KEY.decrypt(f.read())))
            for col in ["Anmeldung", "Zuteilung"]:
                df[col] = pd.to_datetime(df[col], dayfirst=True)

    except FileNotFoundError:
        # return empy df
        df = pd.DataFrame()

    return df


def encryptAndSave(df: pd.DataFrame, KEY: Fernet | None = None):
    """Encrypt dataframe and save to file.

    Args:
        df (pd.DataFrame): The dataframe to encrypt and save.
        KEY (Fernet | None, optional): The Fernet key used for encryption.
            Defaults to None.
    """
    if KEY is None:
        KEY = getKey()

    # encrypt
    with open("liegePlatzData.encrypted", "wb") as f:
        f.write(KEY.encrypt(df.to_csv(index=False).encode()))


if __name__ == "__main__":

    KEY = getKey()

    driver = webdriver.Firefox()
    driver.implicitly_wait(10)
    driver.get(URL)

    userElem = driver.find_element(By.XPATH, "//input[@id='userInputField']")
    pwElem = driver.find_element(By.XPATH, "//input[@id='pwInputField']")

    userElem.send_keys(USER)
    pwElem.send_keys(PWD)

    # log in
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    # get data
    df = pd.DataFrame()
    inputFieldXPath = "//input[@id='stzh-input-0']"
    submitXPath = (
        "//button[contains(@class, 'stzh-button') and .//*[text()='Abfragen']]"
    )
    for length in LENGTHS:
        d = driver.find_element(By.XPATH, inputFieldXPath)
        d.clear()
        d.send_keys(length)
        driver.find_element(By.XPATH, submitXPath).click()
        time.sleep(0.1)  # seems this can otherwise be too fast
        element = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, "//div[@class='stzh-table']"))
        )
        dfLoc = pd.read_html(StringIO(driver.page_source))[0]

        df = pd.concat((df, dfLoc), ignore_index=True)

    df[["Breite", "Laenge"]] = df["Grösse (Breite / Länge) in cm"].str.split(
        "/", expand=True
    )
    df = df.drop(["Grösse (Breite / Länge) in cm"], axis=1)

    dfCurrent = readAndDecrypt(KEY)
    dfAll = pd.concat((dfCurrent, df), ignore_index=True).drop_duplicates()

    # store (locally) a copy as csv, is gitignored
    dfAll.to_csv(
        f"liegeplatzData_{pd.Timestamp.now().date().isoformat()}.csv", index=False
    )

    encryptAndSave(dfAll, KEY)
