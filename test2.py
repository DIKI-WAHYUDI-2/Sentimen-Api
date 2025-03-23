import pandas as pd
import re
from bs4 import BeautifulSoup

data = pd.read_excel("./data/data-berita.xlsx")

df = data[['title','Sentimen']].fillna("").astype(str)

df = df.drop_duplicates(subset='title', keep='first')

def remove_URL(text):
    return re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)

def remove_html(text):
    return BeautifulSoup(text, "html.parser").get_text()

def remove_number(text):
    return re.sub(r"\d+", "", text)

def remove_symbol(text):
    return re.sub(r"[^\w\s.,]", "", text)  # Menjaga titik (.), koma (,)

def case_folding(text):
    return text.lower()

df['title'] = df['title'].apply(remove_URL).apply(remove_html).apply(remove_symbol).apply(case_folding)

sentimen_counts = data['Sentimen'].value_counts()

print(sentimen_counts)
df.to_excel('data-berita1.xlsx', index = False)
