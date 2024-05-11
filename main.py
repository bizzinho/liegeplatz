from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import os
from io import StringIO, BytesIO
import pandas as pd
from cryptography.fernet import Fernet
import time
import re

# TODO
# - map locations to approx regions
# - consolidate BV and Bauschaenzli into one of other catgories

URL = "https://www.stadt-zuerich.ch/appl/besys2-ew/hafen/warteliste"

USER = os.environ["USER"]
PWD = os.environ["PWD"]
# lengths to check
# higher resolution around target of 250
LENGTHS = set(range(120, 320, 20)).union(range(225, 280, 5)).union(range(245, 255))


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
                df[col] = pd.to_datetime(df[col])

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


def getData() -> pd.DataFrame:
    """Get data from ZH website.

    Returns:
        pd.DataFrame: Latest waiting times.
    """
    driver = webdriver.Firefox()
    driver.implicitly_wait(20)
    driver.get(URL)

    WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.XPATH, "//input[@id='userInputField']"))
    )

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
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, "//div[@class='stzh-table']"))
        )
        dfLoc = pd.read_html(StringIO(driver.page_source))[0]

        df = pd.concat((df, dfLoc), ignore_index=True)

    df[["Breite", "Laenge"]] = df["Grösse (Breite / Länge) in cm"].str.split(
        "/", expand=True
    )
    df = df.drop(["Grösse (Breite / Länge) in cm"], axis=1)
    for col in ["Anmeldung", "Zuteilung"]:
        df[col] = pd.to_datetime(df[col], dayfirst=True)
    for col in ["Breite", "Laenge"]:
        df[col] = df[col].astype(int)

    df = df.sort_values("Zuteilung", ignore_index=True, ascending=False)

    return df


def _calcDuration(anmeldung: pd.Series, zuteilung: pd.Series) -> pd.Series:
    return (zuteilung - anmeldung).dt.days / 365.25


def _calcType(anlage: pd.Series) -> pd.Series:
    mapfun = lambda x: re.sub(
        r".*(Hafen|Trockenplatz|Bojenfeld|Steganlage|Bauschänzli|BV).*", "\\1", x
    )

    return anlage.map(mapfun)


# def _calcRegion(anlage: pd.Series) -> pd.Series:
#     mapfun = lambda x:


def _mapRegion(anlagenStr: str) -> str:

    gold = ("Tiefenbrunnen", "Riesbach", "Rytz")
    # from south to north
    silver = (
        "Camping",
        "Wollishofen",
        "Kibag",
        "Mythenquai",
        "Enge",
        "Standard",  # where is this standard??
        "Arboretum",
        "Guisan",
    )
    fluss = ("Quaibrücke", "Bauschänzli", "Schanzengraben", "Limmatquai")

    if any(g in anlagenStr for g in gold):
        return "Goldküste"
    elif any(s in anlagenStr for s in silver):
        return "Silberküste"
    elif any(l in anlagenStr for l in fluss):
        return "Fluss"


if __name__ == "__main__":

    KEY = getKey()

    df = getData()

    dfCurrent = readAndDecrypt(KEY)
    dfAll = (
        pd.concat((dfCurrent, df), ignore_index=True)
        .drop_duplicates()
        .sort_values("Zuteilung", ignore_index=True, ascending=False)
    )

    # store (locally) a copy as csv, is gitignored
    dfAll.to_csv(
        f"liegeplatzData_{pd.Timestamp.now().date().isoformat()}.csv", index=False
    )

    encryptAndSave(dfAll, KEY)
