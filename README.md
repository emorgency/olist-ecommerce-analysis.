# Olist E-Commerce Data Analysis (Dicoding Submission)

## Ringkasan

Proyek ini menganalisis data transaksi e-commerce Olist untuk periode Januari 2017–Agustus 2018. Fokusnya adalah tren pesanan dan nilai barang, kategori produk, ketepatan pengiriman terhadap rating, serta segmentasi pelanggan RFM berbasis aturan bisnis.

### Pertanyaan bisnis

1. Bagaimana jumlah pesanan delivered dan total nilai barang (tanpa ongkir) berubah tiap bulan, dan bulan mana yang mencatat nilai tertinggi?
2. Kategori produk apa yang memberikan nilai penjualan barang tertinggi, serta kategori mana yang memiliki rata-rata rating terendah dari kategori dengan minimal 100 ulasan?
3. Seberapa berbeda rata-rata rating dan proporsi rating rendah (1–2) antara pesanan terlambat dan tepat waktu/lebih cepat?

## Struktur direktori

```text
olist_submission/
├── dashboard/
│   ├── dashboard.py
│   ├── main_data.csv
│   └── category_items.csv
├── data/
│   ├── orders_dataset.csv
│   ├── order_items_dataset.csv
│   ├── customers_dataset.csv
│   ├── products_dataset.csv
│   ├── order_reviews_dataset.csv
│   └── product_category_name_translation.csv
├── notebook.ipynb
├── README.md
└── requirements.txt
```

## Cara menjalankan notebook

Jalankan dari folder utama proyek agar path `data/` terbaca.

```bash
python -m pip install -r requirements.txt
jupyter notebook notebook.ipynb
```

Jalankan semua cell dari atas ke bawah. Notebook berisi proses gathering, assessing, cleaning, EDA, visualisasi, analisis RFM, kesimpulan, dan rekomendasi.

## Cara menjalankan dashboard secara lokal

Dari folder utama proyek:

```bash
python -m pip install -r requirements.txt
streamlit run dashboard/dashboard.py
```

Streamlit akan menampilkan alamat lokal di terminal, umumnya `http://localhost:8501`. Data dashboard dibaca dari file CSV yang berada satu folder dengan `dashboard.py`, jadi folder `dashboard/` tidak boleh dipisahkan dari CSV-nya.

## Dataset dan definisi metrik

Dataset: [Brazilian E-Commerce Public Dataset by Olist di Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Dataset berlisensi CC BY-NC-SA 4.0; periksa ketentuan lisensi sebelum menggunakan data di luar tujuan pendidikan.

- Periode analisis: 1 Januari 2017 sampai 31 Agustus 2018. Bulan di bagian luar periode dikecualikan dari analisis tren karena cakupan datanya tidak merata.
- Nilai barang = jumlah kolom `price` per item; ongkos kirim tidak termasuk.
- Pesanan yang dianalisis berstatus `delivered`.
- Produk tanpa kategori diberi label `Unknown category`.
- Ulasan dengan `review_id` yang terhubung ke beberapa pesanan tidak digunakan untuk analisis rating karena atribusinya ambigu.
- RFM pada notebook memakai snapshot historis 1 September 2018. Hasilnya tidak menggambarkan perilaku pelanggan masa kini.

## Deploy Streamlit Community Cloud (opsional)

1. Unggah folder proyek ini ke repository GitHub milik Anda.
2. Buka [Streamlit Community Cloud](https://share.streamlit.io/) dan masuk menggunakan akun GitHub.
3. Pilih **Create app**, lalu tentukan repository, branch, dan file utama `dashboard/dashboard.py`.
4. Pastikan `requirements.txt` berada di root repository. Tunggu proses build selesai dan periksa dashboard dari URL yang diberikan.
5. Setelah sukses, simpan URL publik tersebut ke file `url.txt` di folder submission sebelum ZIP dikumpulkan.

## Batasan

Data bersifat historis dan observasional. Keterlambatan yang berkaitan dengan rating lebih rendah tidak otomatis membuktikan keterlambatan sebagai satu-satunya penyebab. Analisis lanjutan berdasarkan seller, wilayah, dan jenis produk diperlukan sebelum keputusan operasional diterapkan.
