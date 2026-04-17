import pandas as pd
import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
import nltk
import googletrans
from googletrans import Translator
import textblob from textblob import TexBlob

# Download stopwords jika belum tersedia
nltk.download('stopwords')

# Inisialisasi stopwords
STOPWORDS = set(stopwords.words('indonesian'))
STOPWORDS.update([
    'https', 'http', 'https://', 'berita:', 'copyright', '©', '403', 'client', 
    'error:', 'error', 'forbidden', 'url:', 'url', 'loading', 'di', 'ke', 'ada', 
    'adalah', 'oleh', 'pada', 'yang', 'dan', 'atau', 'tetapi', 'sehingga', 'agar', 'untuk', 'itu'
])

# Inisialisasi Stemmer
factory = StemmerFactory()
stemmer = factory.create_stemmer()

# Load kamus kata baku
kamus_baku = pd.read_excel("./kamus/kamuskatabaku.xlsx")
kamus_dict = dict(zip(kamus_baku['tidak_baku'], kamus_baku['kata_baku']))

# Fungsi pembersihan teks
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

def tokenize(text):
    return text.split()

def replace_taboo(text):
    words = text.lower().split()  # Tambahkan lower()
    return " ".join([kamus_dict[word] if word in kamus_dict else word for word in words])

def stemming(words):
    return [stemmer.stem(word) for word in words]

def remove_stopwords(words):
    return [word for word in words if word not in STOPWORDS]

# Load daftar kata positif & negatif
positive_lexicon = set(pd.read_csv("./kamus/positive.tsv", sep="\t", header=None)[0])
negative_lexicon = set(pd.read_csv("./kamus/negative.tsv", sep="\t", header=None)[0])

# Fungsi untuk analisis sentimen
def analyze_sentiment(text):
    words = text.split()
    positive_count = sum(1 for word in words if word in positive_lexicon)
    negative_count = sum(1 for word in words if word in negative_lexicon)
    if positive_count > negative_count:
        return 'Positif'
    elif negative_count > positive_count:
        return 'Negatif'
    else:
        return 'Netral'

# Load file Excel
file_path = "./db.json"  # Ganti dengan path file yang sesuai
data = pd.read_json(file_path)

# Buat DataFrame dengan hanya kolom yang dibutuhkan
df = data[['content']].fillna("").astype(str)

# Gabungkan Judul dan Isi Berita sebelum preprocessing
# data['text_gabung'] = data['Judul'].fillna("") + " " + data['Isi Berita'].fillna("")

# Pastikan tidak ada NaN setelah penggabungan
# data['text_gabung'] = data['text_gabung'].astype(str)

# Preprocessing
df['clean_text'] = df['content'].apply(remove_URL).apply(remove_html).apply(remove_number).apply(remove_symbol)
df['case_folding'] = df['clean_text'].apply(case_folding)
df['normalized_text'] = df['case_folding'].apply(replace_taboo)
df['tokenized_text'] = df['normalized_text'].apply(tokenize)
df['stemmed_text'] = df['tokenized_text'].apply(stemming)
df['stopwords_removed'] = df['stemmed_text'].apply(remove_stopwords)


# Final processed text
df['processed_text'] = df['stopwords_removed'].apply(lambda x: ' '.join(x) if isinstance(x, list) else x)

# Terapkan analisis sentimen
df['sentimen'] = df['processed_text'].apply(analyze_sentiment)

df = df[['content','sentimen']]

# Simpan hasil ke file Excel
df.to_excel("./data/preprocessed_content.xlsx", index=False)    

print(df.head())
