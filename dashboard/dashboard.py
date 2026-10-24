from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 1. KONFIGURASI
# =========================================================

st.set_page_config(
    page_title="Olist E-Commerce Analytics",
    page_icon="📊   ",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
MAIN_DATA_PATH = BASE_DIR / "main_data.csv"
CATEGORY_DATA_PATH = BASE_DIR / "category_items.csv"

MIN_REVIEW_COUNT = 100
PLOT_TEMPLATE = "plotly_dark"


# =========================================================
# 2. FUNGSI BANTU
# =========================================================

def format_id_number(value, decimals=0):
    """Format angka dengan konvensi Indonesia: 1.234,56."""
    if pd.isna(value):
        return "N/A"

    formatted = f"{value:,.{decimals}f}"

    return (
        formatted
        .replace(",", "TEMP")
        .replace(".", ",")
        .replace("TEMP", ".")
    )


def validate_columns(df, required_columns, filename):
    """Memeriksa apakah kolom wajib tersedia."""
    missing = sorted(set(required_columns) - set(df.columns))

    if missing:
        raise ValueError(
            f"Kolom berikut tidak ditemukan di {filename}: "
            f"{', '.join(missing)}."
        )


def score_higher_is_better(series, number_of_groups=5):
    """
    Skor 1-5 untuk Frequency dan Monetary.
    Semakin tinggi nilai, semakin tinggi skornya.
    """
    percentile_rank = series.rank(method="average", pct=True)

    scores = np.ceil(percentile_rank * number_of_groups)

    return pd.Series(
        scores,
        index=series.index
    ).clip(1, number_of_groups).astype(int)


def score_recency(series, number_of_groups=5):
    """
    Skor 1-5 untuk Recency.
    Semakin sedikit hari sejak pembelian terakhir,
    semakin tinggi skornya.
    """
    percentile_rank = series.rank(method="average", pct=True)

    scores = (
        number_of_groups + 1
        - np.ceil(percentile_rank * number_of_groups)
    )

    return pd.Series(
        scores,
        index=series.index
    ).clip(1, number_of_groups).astype(int)


# =========================================================
# 3. MEMUAT DAN MEMVALIDASI DATA
# =========================================================

@st.cache_data(show_spinner="Memuat dataset...")
def load_data():

    if not MAIN_DATA_PATH.exists():
        raise FileNotFoundError(
            f"File {MAIN_DATA_PATH.name} tidak ditemukan. "
            "Pastikan file berada satu folder dengan dashboard.py."
        )

    if not CATEGORY_DATA_PATH.exists():
        raise FileNotFoundError(
            f"File {CATEGORY_DATA_PATH.name} tidak ditemukan. "
            "Pastikan file berada satu folder dengan dashboard.py."
        )

    orders_df = pd.read_csv(MAIN_DATA_PATH)
    categories_df = pd.read_csv(CATEGORY_DATA_PATH)

    validate_columns(
        orders_df,
        [
            "order_id",
            "customer_unique_id",
            "purchase_date",
            "item_revenue",
            "delay_days",
            "delivery_group",
            "review_score",
        ],
        MAIN_DATA_PATH.name,
    )

    validate_columns(
        categories_df,
        [
            "order_id",
            "order_item_id",
            "category",
            "price",
            "purchase_date",
        ],
        CATEGORY_DATA_PATH.name,
    )

    # Mengubah kolom tanggal menjadi datetime.
    for column in [
        "purchase_date",
        "delivered_date",
        "estimated_delivery_date",
    ]:
        if column in orders_df.columns:
            orders_df[column] = pd.to_datetime(
                orders_df[column],
                errors="coerce",
            )

    categories_df["purchase_date"] = pd.to_datetime(
        categories_df["purchase_date"],
        errors="coerce",
    )

    # Memastikan kolom numerik benar-benar numerik.
    for column in [
        "item_revenue",
        "delay_days",
        "review_score",
    ]:
        orders_df[column] = pd.to_numeric(
            orders_df[column],
            errors="coerce",
        )

    for column in ["price", "order_item_id"]:
        categories_df[column] = pd.to_numeric(
            categories_df[column],
            errors="coerce",
        )

    # Menghapus baris yang tidak memiliki ID pesanan atau tanggal.
    orders_df = orders_df.dropna(
        subset=["order_id", "purchase_date"]
    ).copy()

    categories_df = categories_df.dropna(
        subset=["order_id", "purchase_date"]
    ).copy()

    # Menangani kategori dan kelompok pengiriman kosong.
    orders_df["delivery_group"] = (
        orders_df["delivery_group"]
        .fillna("Tidak diketahui")
    )

    categories_df["category"] = (
        categories_df["category"]
        .fillna("Unknown category")
    )

    # Rating hanya valid pada rentang 1-5.
    orders_df.loc[
        ~orders_df["review_score"].between(1, 5),
        "review_score",
    ] = np.nan

    return orders_df, categories_df


try:
    orders, category_items = load_data()

except (
    FileNotFoundError,
    ValueError,
    pd.errors.ParserError,
) as error:

    st.error(f"Data tidak dapat dimuat: {error}")
    st.stop()


if orders.empty:
    st.error(
        "main_data.csv tidak berisi data yang dapat dianalisis."
    )
    st.stop()


# =========================================================
# 4. JUDUL DAN FILTER TANGGAL
# =========================================================

min_date = orders["purchase_date"].min().date()
max_date = orders["purchase_date"].max().date()

st.title("Olist E-Commerce Analytics")

st.caption(
    "Analisis historis pesanan delivered, nilai barang tanpa "
    "ongkos kirim, kategori produk, ulasan pelanggan, "
    "ketepatan pengiriman, dan segmentasi RFM."
)

st.sidebar.header("Filter analisis")

selected_dates = st.sidebar.date_input(
    "Periode pembelian",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    format="DD/MM/YYYY",
)

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates


if start_date > end_date:
    st.error("Tanggal awal tidak boleh lebih besar dari tanggal akhir.")
    st.stop()


start_ts = pd.Timestamp(start_date)
end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)


filtered_orders = orders[
    (orders["purchase_date"] >= start_ts)
    & (orders["purchase_date"] < end_exclusive)
].copy()


filtered_items = category_items[
    (category_items["purchase_date"] >= start_ts)
    & (category_items["purchase_date"] < end_exclusive)
].copy()


if filtered_orders.empty:
    st.warning("Tidak ada pesanan pada periode yang dipilih.")
    st.stop()


# =========================================================
# 5. KPI UTAMA
# =========================================================

valid_ratings = filtered_orders["review_score"].dropna()

known_delivery = filtered_orders[
    filtered_orders["delay_days"].notna()
]

late_rate = (
    known_delivery["delay_days"].gt(0).mean() * 100
    if not known_delivery.empty
    else np.nan
)

item_revenue_total = filtered_orders["item_revenue"].sum(
    min_count=1
)

orders_count = filtered_orders["order_id"].nunique()

average_rating = (
    valid_ratings.mean()
    if not valid_ratings.empty
    else np.nan
)


k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Pesanan delivered",
    format_id_number(orders_count),
)

k2.metric(
    "Nilai barang",
    (
        f"R$ {format_id_number(item_revenue_total / 1_000_000, 2)} juta"
        if pd.notna(item_revenue_total)
        else "N/A"
    ),
    help="Jumlah harga item; ongkos kirim tidak termasuk.",
)

k3.metric(
    "Rata-rata rating",
    (
        f"{format_id_number(average_rating, 2)}/5"
        if pd.notna(average_rating)
        else "N/A"
    ),
)

k4.metric(
    "Pesanan terlambat",
    (
        f"{format_id_number(late_rate, 1)}%"
        if pd.notna(late_rate)
        else "N/A"
    ),
    help=(
        "Persentase pesanan yang terlambat dari pesanan "
        "yang memiliki data keterlambatan."
    ),
)

st.divider()


# =========================================================
# 6. TREN BULANAN
# =========================================================

filtered_orders["month"] = (
    filtered_orders["purchase_date"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

monthly = (
    filtered_orders.groupby("month")
    .agg(
        orders=("order_id", "nunique"),
        item_revenue=("item_revenue", "sum"),
    )
    .reset_index()
    .sort_values("month")
)


fig_month = go.Figure()

fig_month.add_trace(
    go.Scatter(
        x=monthly["month"],
        y=monthly["item_revenue"],
        mode="lines+markers",
        name="Nilai barang (R$)",
        yaxis="y",
        line=dict(color="#60A5FA", width=3),
        marker=dict(color="#60A5FA", size=7),
        hovertemplate=(
            "Bulan: %{x|%b %Y}<br>"
            "Nilai barang: R$ %{y:,.2f}"
            "<extra></extra>"
        ),
    )
)

fig_month.add_trace(
    go.Bar(
        x=monthly["month"],
        y=monthly["orders"],
        name="Pesanan",
        yaxis="y2",
        marker=dict(color="#2563EB"),
        opacity=0.45,
        hovertemplate=(
            "Bulan: %{x|%b %Y}<br>"
            "Pesanan: %{y:,}"
            "<extra></extra>"
        ),
    )
)

fig_month.update_layout(
    template=PLOT_TEMPLATE,
    title="Tren Bulanan: Nilai Barang dan Jumlah Pesanan",
    xaxis_title="Bulan pembelian",
    yaxis=dict(
        title="Nilai barang (R$)",
        rangemode="tozero",
        tickformat="~s",
    ),
    yaxis2=dict(
        title="Jumlah pesanan",
        overlaying="y",
        side="right",
        rangemode="tozero",
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    margin=dict(l=10, r=10, t=65, b=10),
    hovermode="x unified",
)

fig_month.update_xaxes(tickformat="%b %Y")

st.plotly_chart(
    fig_month,
    use_container_width=True,
)


# =========================================================
# 7. ANALISIS KATEGORI PRODUK
# =========================================================

left, right = st.columns(2)


# ---------------------------------------------------------
# 7A. Sepuluh kategori dengan nilai barang tertinggi
# ---------------------------------------------------------

with left:

    if not filtered_items.empty:

        category_sales = (
            filtered_items.groupby("category")
            .agg(
                item_revenue=("price", "sum"),
                items_sold=("order_item_id", "count"),
                orders=("order_id", "nunique"),
            )
            .reset_index()
        )

        top_categories = (
            category_sales.nlargest(10, "item_revenue")
            .sort_values("item_revenue", ascending=True)
        )

        fig_categories = px.bar(
            top_categories,
            x="item_revenue",
            y="category",
            orientation="h",
            title="10 Kategori dengan Nilai Barang Tertinggi",
            labels={
                "item_revenue": "Nilai barang (R$)",
                "category": "Kategori",
                "items_sold": "Jumlah item terjual",
                "orders": "Jumlah pesanan",
            },
            hover_data={
                "item_revenue": ":,.2f",
                "items_sold": ":,",
                "orders": ":,",
            },
            template=PLOT_TEMPLATE,
        )

        fig_categories.update_layout(
            margin=dict(l=10, r=10, t=55, b=10)
        )

        st.plotly_chart(
            fig_categories,
            use_container_width=True,
        )

    else:
        st.info("Tidak ada data item untuk periode ini.")


# ---------------------------------------------------------
# 7B. Kategori dengan rata-rata rating terendah
# ---------------------------------------------------------

with right:

    if not filtered_items.empty:

        # Setiap kombinasi order dan kategori hanya dihitung sekali.
        category_orders = (
            filtered_items[["order_id", "category"]]
            .drop_duplicates()
        )

        category_orders = category_orders.merge(
            filtered_orders[["order_id", "review_score"]],
            on="order_id",
            how="left",
            validate="many_to_one",
        )

        category_rating = (
            category_orders.groupby("category")
            .agg(
                average_rating=("review_score", "mean"),
                reviewed_orders=("review_score", "count"),
            )
            .reset_index()
        )

        # Ambang batas konsisten: minimal 100 pesanan berulasan.
        category_rating = category_rating[
            category_rating["reviewed_orders"] >= MIN_REVIEW_COUNT
        ]

        category_rating = (
            category_rating.nsmallest(10, "average_rating")
            .sort_values("average_rating", ascending=True)
        )

        if not category_rating.empty:

            fig_category_rating = px.bar(
                category_rating,
                x="average_rating",
                y="category",
                orientation="h",
                title=(
                    "Kategori dengan Rating Terendah "
                    f"(min. {MIN_REVIEW_COUNT} ulasan)"
                ),
                labels={
                    "average_rating": "Rata-rata rating (1–5)",
                    "category": "Kategori",
                    "reviewed_orders": "Pesanan dengan ulasan",
                },
                hover_data={
                    "average_rating": ":.2f",
                    "reviewed_orders": ":,",
                },
                template=PLOT_TEMPLATE,
            )

            fig_category_rating.update_xaxes(
                range=[0, 5]
            )

            fig_category_rating.update_layout(
                margin=dict(l=10, r=10, t=55, b=10)
            )

            st.plotly_chart(
                fig_category_rating,
                use_container_width=True,
            )

        else:
            st.info(
                f"Belum ada kategori dengan minimal "
                f"{MIN_REVIEW_COUNT} ulasan pada periode ini."
            )

    else:
        st.info("Tidak ada data kategori untuk periode ini.")


# =========================================================
# 8. ANALISIS RATING DAN KETEPATAN PENGIRIMAN
# =========================================================

delivery_data = filtered_orders[
    filtered_orders["delay_days"].notna()
    & filtered_orders["review_score"].notna()
].copy()


if not delivery_data.empty:

    delivery_summary = (
        delivery_data.groupby("delivery_group")
        .agg(
            reviewed_orders=("order_id", "nunique"),
            average_rating=("review_score", "mean"),
            low_rating_share=(
                "review_score",
                lambda values: values.le(2).mean() * 100,
            ),
        )
        .reset_index()
    )

    delivery_order = {
        "Tepat waktu / lebih cepat": 0,
        "Terlambat": 1,
        "Tidak diketahui": 2,
    }

    delivery_summary["_order"] = (
        delivery_summary["delivery_group"]
        .map(delivery_order)
        .fillna(99)
    )

    delivery_summary = delivery_summary.sort_values("_order")

else:

    delivery_summary = pd.DataFrame(
        columns=[
            "delivery_group",
            "reviewed_orders",
            "average_rating",
            "low_rating_share",
        ]
    )


st.subheader("Ulasan dan ketepatan pengiriman")

left_delivery, right_delivery = st.columns(2)


# ---------------------------------------------------------
# 8A. Rata-rata rating menurut ketepatan pengiriman
# ---------------------------------------------------------

with left_delivery:

    if not delivery_summary.empty:

        fig_delivery_rating = px.bar(
            delivery_summary,
            x="delivery_group",
            y="average_rating",
            title="Rating Menurut Ketepatan Pengiriman",
            labels={
                "delivery_group": "Kelompok pengiriman",
                "average_rating": "Rata-rata rating",
                "reviewed_orders": "Pesanan dengan ulasan",
                "low_rating_share": "Rating rendah (%)",
            },
            hover_data={
                "reviewed_orders": ":,",
                "low_rating_share": ":.2f",
            },
            template=PLOT_TEMPLATE,
        )

        fig_delivery_rating.update_yaxes(
            range=[0, 5]
        )

        fig_delivery_rating.update_layout(
            margin=dict(l=10, r=10, t=55, b=10)
        )

        st.plotly_chart(
            fig_delivery_rating,
            use_container_width=True,
        )

    else:
        st.info(
            "Tidak cukup data rating dan pengiriman "
            "untuk periode ini."
        )


# ---------------------------------------------------------
# 8B. Persentase rating rendah
# ---------------------------------------------------------

with right_delivery:

    if not delivery_summary.empty:

        fig_low_rating = px.bar(
            delivery_summary,
            x="delivery_group",
            y="low_rating_share",
            title="Proporsi Rating Rendah (1–2)",
            labels={
                "delivery_group": "Kelompok pengiriman",
                "low_rating_share": "Rating rendah (%)",
                "reviewed_orders": "Pesanan dengan ulasan",
            },
            hover_data={
                "reviewed_orders": ":,",
            },
            template=PLOT_TEMPLATE,
        )

        fig_low_rating.update_yaxes(
            range=[0, 100]
        )

        fig_low_rating.update_layout(
            margin=dict(l=10, r=10, t=55, b=10)
        )

        st.plotly_chart(
            fig_low_rating,
            use_container_width=True,
        )


st.caption(
    "Catatan: analisis pengiriman hanya menggunakan pesanan "
    "yang memiliki data keterlambatan dan rating. Hubungan "
    "statistik tidak membuktikan sebab-akibat."
)


# =========================================================
# 9. SEGMENTASI PELANGGAN RFM
# =========================================================

st.divider()

st.subheader("Segmentasi pelanggan RFM")

st.caption(
    "Recency menunjukkan jumlah hari sejak pembelian terakhir "
    "hingga satu hari setelah tanggal akhir filter. Frequency "
    "adalah jumlah pesanan dalam periode terpilih. Monetary "
    "adalah total nilai barang tanpa ongkos kirim."
)


rfm_base = filtered_orders[
    [
        "customer_unique_id",
        "order_id",
        "purchase_date",
        "item_revenue",
    ]
].dropna(
    subset=["customer_unique_id", "purchase_date"]
).copy()


if rfm_base.empty:

    st.info(
        "Tidak cukup data pelanggan untuk melakukan analisis RFM."
    )

else:

    # Menghitung R, F, dan M berdasarkan pelanggan.
    rfm = (
        rfm_base.groupby("customer_unique_id")
        .agg(
            last_purchase=("purchase_date", "max"),
            frequency=("order_id", "nunique"),
            monetary=("item_revenue", "sum"),
        )
        .reset_index()
    )

    # Recency menggunakan tanggal setelah periode filter.
    snapshot_date = end_exclusive.normalize()

    rfm["recency_days"] = (
        snapshot_date
        - rfm["last_purchase"].dt.normalize()
    ).dt.days.clip(lower=0)

    # Memberi skor 1-5 untuk setiap dimensi.
    rfm["R_score"] = score_recency(
        rfm["recency_days"]
    )

    rfm["F_score"] = score_higher_is_better(
        rfm["frequency"]
    )

    rfm["M_score"] = score_higher_is_better(
        rfm["monetary"]
    )

    # Skor gabungan dan kode RFM.
    rfm["RFM_score"] = rfm[
        ["R_score", "F_score", "M_score"]
    ].sum(axis=1)

    rfm["RFM_code"] = (
        rfm["R_score"].astype(str)
        + rfm["F_score"].astype(str)
        + rfm["M_score"].astype(str)
    )

    # Segmentasi berdasarkan aturan bisnis.
    conditions = [
        (
            (rfm["R_score"] >= 4)
            & (rfm["F_score"] >= 4)
            & (rfm["M_score"] >= 4)
        ),
        (
            (rfm["R_score"] >= 3)
            & (rfm["F_score"] >= 4)
        ),
        (
            (rfm["R_score"] >= 4)
            & (rfm["F_score"].between(2, 3))
        ),
        (
            (rfm["R_score"] >= 4)
            & (rfm["F_score"] == 1)
        ),
        (
            (rfm["R_score"] <= 2)
            & (rfm["F_score"] >= 3)
        ),
        (
            (rfm["R_score"] <= 2)
            & (rfm["F_score"] <= 2)
        ),
        (
            (rfm["M_score"] >= 4)
            & (rfm["F_score"] >= 3)
        ),
    ]

    segment_names = [
        "Champions",
        "Pelanggan loyal",
        "Potensial loyal",
        "Pelanggan baru/baru aktif",
        "Berisiko",
        "Perlu perhatian",
        "Pelanggan bernilai tinggi",
    ]

    rfm["segment"] = np.select(
        conditions,
        segment_names,
        default="Pelanggan lainnya",
    )

    # Ringkasan berdasarkan segmen.
    rfm_summary = (
        rfm.groupby("segment")
        .agg(
            customers=("customer_unique_id", "nunique"),
            total_item_revenue=("monetary", "sum"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            avg_rfm_score=("RFM_score", "mean"),
        )
        .reset_index()
    )

    rfm_summary["customer_share_pct"] = (
        rfm_summary["customers"]
        / rfm_summary["customers"].sum()
        * 100
    )

    rfm_summary = rfm_summary.sort_values(
        "customers",
        ascending=False,
    )

    # Grafik segmen RFM.
    fig_rfm_segments = px.bar(
        rfm_summary.sort_values(
            "customers",
            ascending=True,
        ),
        x="customers",
        y="segment",
        orientation="h",
        title="Jumlah Pelanggan per Segmen RFM",
        labels={
            "customers": "Jumlah pelanggan",
            "segment": "Segmen pelanggan",
            "customer_share_pct": "Porsi pelanggan (%)",
            "avg_recency_days": "Rata-rata recency (hari)",
            "avg_frequency": "Rata-rata frekuensi pesanan",
            "avg_monetary": "Rata-rata nilai barang (R$)",
            "avg_rfm_score": "Rata-rata skor RFM",
        },
        hover_data={
            "customer_share_pct": ":.2f",
            "avg_recency_days": ":.1f",
            "avg_frequency": ":.2f",
            "avg_monetary": ":,.2f",
        },
        template=PLOT_TEMPLATE,
    )

    fig_rfm_segments.update_layout(
        margin=dict(l=10, r=10, t=55, b=10)
    )

    st.plotly_chart(
        fig_rfm_segments,
        use_container_width=True,
    )

    # Tabel ringkasan RFM.
    rfm_display = rfm_summary.rename(
        columns={
            "segment": "Segmen RFM",
            "customers": "Jumlah pelanggan",
            "customer_share_pct": "Porsi pelanggan (%)",
            "total_item_revenue": "Total nilai barang (R$)",
            "avg_recency_days": "Rata-rata recency (hari)",
            "avg_frequency": "Rata-rata pesanan per pelanggan",
            "avg_monetary": "Rata-rata belanja (R$)",
            "avg_rfm_score": "Rata-rata skor RFM",
        }
    )

    st.dataframe(
        rfm_display.style.format(
            {
                "Jumlah pelanggan": "{:,.0f}",
                "Porsi pelanggan (%)": "{:,.2f}%",
                "Total nilai barang (R$)": "R$ {:,.2f}",
                "Rata-rata recency (hari)": "{:,.1f}",
                "Rata-rata pesanan per pelanggan": "{:,.2f}",
                "Rata-rata belanja (R$)": "R$ {:,.2f}",
                "Rata-rata skor RFM": "{:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------
    # 9B. Analisis tambahan: frekuensi pembelian
    # -----------------------------------------------------

    rfm["frequency_group"] = np.select(
        [
            rfm["frequency"] == 1,
            rfm["frequency"] == 2,
            rfm["frequency"] >= 3,
        ],
        [
            "1 pesanan",
            "2 pesanan",
            "3+ pesanan",
        ],
        default="Lainnya",
    )

    frequency_summary = (
        rfm.groupby("frequency_group")
        .agg(
            customers=("customer_unique_id", "nunique"),
            total_item_revenue=("monetary", "sum"),
            avg_spend=("monetary", "mean"),
        )
        .reset_index()
    )

    frequency_order = {
        "1 pesanan": 0,
        "2 pesanan": 1,
        "3+ pesanan": 2,
        "Lainnya": 3,
    }

    frequency_summary["_order"] = (
        frequency_summary["frequency_group"]
        .map(frequency_order)
    )

    frequency_summary = (
        frequency_summary
        .sort_values("_order")
        .drop(columns="_order")
    )

    fig_frequency = px.bar(
        frequency_summary,
        x="frequency_group",
        y="customers",
        title="Jumlah Pelanggan berdasarkan Frekuensi Pembelian",
        labels={
            "frequency_group": "Frekuensi pembelian",
            "customers": "Jumlah pelanggan",
            "total_item_revenue": "Total nilai barang (R$)",
            "avg_spend": "Rata-rata belanja (R$)",
        },
        hover_data={
            "total_item_revenue": ":,.2f",
            "avg_spend": ":,.2f",
        },
        template=PLOT_TEMPLATE,
    )

    fig_frequency.update_layout(
        margin=dict(l=10, r=10, t=55, b=10)
    )

    st.plotly_chart(
        fig_frequency,
        use_container_width=True,
    )

    frequency_display = frequency_summary.rename(
        columns={
            "frequency_group": "Frekuensi pembelian",
            "customers": "Jumlah pelanggan",
            "total_item_revenue": "Total nilai barang (R$)",
            "avg_spend": "Rata-rata belanja (R$)",
        }
    )

    st.dataframe(
        frequency_display.style.format(
            {
                "Jumlah pelanggan": "{:,.0f}",
                "Total nilai barang (R$)": "R$ {:,.2f}",
                "Rata-rata belanja (R$)": "R$ {:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Penjelasan RFM.
    with st.expander(
        "Cara membaca skor RFM dan keterbatasannya"
    ):
        st.markdown(
            """
            - **Recency (R):** jumlah hari sejak pembelian terakhir.
              Skor 5 berarti pembelian relatif baru, sedangkan skor
              1 berarti sudah lebih lama.

            - **Frequency (F):** jumlah pesanan pada periode terpilih.
              Skor 5 menunjukkan frekuensi relatif tinggi.

            - **Monetary (M):** total nilai barang yang dibeli pada
              periode terpilih. Skor 5 menunjukkan nilai relatif tinggi.

            - Skor dihitung memakai peringkat persentil. Karena banyak
              pelanggan memiliki frekuensi atau nilai belanja yang sama,
              distribusi skor tidak selalu terbagi rata.

            - Nama segmen ditentukan dengan aturan bisnis sederhana,
              bukan label pelanggan yang telah divalidasi.

            - Analisis hanya menggunakan pesanan yang tersedia pada
              periode terpilih. Transaksi di luar periode tersebut
              tidak masuk ke Frequency atau Monetary.
            """
        )


# =========================================================
# 10. CATATAN DEFINISI DAN SUMBER
# =========================================================

with st.expander("Catatan definisi dan keterbatasan data"):

    st.markdown(
        """
        - Dataset Olist bersifat historis dan mencakup periode
          2016–2018. Hasilnya tidak menggambarkan kondisi bisnis saat ini.

        - Nilai barang menjumlahkan harga item (`price`) dan tidak
          memasukkan ongkos kirim.

        - Dataset analisis utama menggunakan pesanan berstatus
          delivered.

        - `Unknown category` menandakan kategori produk yang tidak
          tersedia pada hasil pemetaan nama kategori.

        - Perbedaan rating menurut pengiriman menunjukkan hubungan
          statistik, bukan bukti bahwa keterlambatan menjadi satu-satunya
          penyebab rating rendah.

        - Rating yang tidak tersedia tidak disertakan dalam perhitungan
          rata-rata rating.
        """
    )


st.caption(
    "Sumber: Brazilian E-Commerce Public Dataset by Olist. "
    "Dashboard ini dibuat untuk analisis edukasi."
)