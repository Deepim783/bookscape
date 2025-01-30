import streamlit as st 
import requests
import json
import sqlite3
import pandas as pd
import os
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

api_key = "AIzaSyBadcG4PdaA0rGSK_KENPloLi7bXUZjWHE"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILEPATH = os.path.join(BASE_DIR, "book_data.db")
JSON_FILEPATH = os.path.join(BASE_DIR, "book_data.json")


def get_books(keyword, api_key, max_results=1000):
    all_results = []
    startIndex = 0
    while len(all_results) < max_results:
        url = f"https://www.googleapis.com/books/v1/volumes?q={keyword}&startIndex={startIndex}&maxResults=40&key={api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            try:
                data = response.json()
                if "items" in data:
                    all_results.extend(data["items"])
                    
                    startIndex += 40
                else:
                    break
            except json.JSONDecodeError:
                st.error("Failed to parse API response.")
                break
        else:
            st.error(f"Error fetching data: {response.status_code}")
            break

    return all_results[:max_results]


def save_to_sql(book_data, keyword, DB_FILEPATH):
    conn = sqlite3.connect(DB_FILEPATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            Book_Id TEXT PRIMARY KEY,
            Search_Key TEXT,
            Book_Title TEXT,
            Book_Subtitle TEXT,
            Book_Authors TEXT,
            Book_Description TEXT,
            IndustryIdentifiers TEXT,
            PageCount INT,
            Categories TEXT,
            Language TEXT,
            ImageLinks TEXT,
            RatingsCount INT,
            AverageRating REAL,
            Country TEXT,
            Saleability TEXT,
            IsEbook BOOLEAN,
            Amount_ListPrice REAL,
            CurrencyCode_ListPrice TEXT,
            Amount_RetailPrice REAL,
            CurrencyCode_RetailPrice TEXT,
            BuyLink TEXT,
            Year TEXT
        )
    """)
    cursor.execute("DELETE FROM books")

    for item in book_data:
        volume_info = item.get("volumeInfo", {})
        sale_info = item.get("saleInfo", {})
        try:
            Book_Id = item["id"]
            Book_Title = volume_info.get("title", "")
            Book_Subtitle = volume_info.get("subtitle", "")
            Book_Authors = ", ".join(volume_info.get("authors", []))
            Book_Description = volume_info.get("description", "")
            IndustryIdentifiers = json.dumps(volume_info.get("industryIdentifiers", []))
            PageCount = volume_info.get("pageCount", None)
            Categories = ", ".join(volume_info.get("categories", []))
            Language = volume_info.get("language", "")
            ImageLinks = json.dumps(volume_info.get("imageLinks", {}))
            RatingsCount = volume_info.get("ratingsCount", None)
            AverageRating = volume_info.get("averageRating", None)
            Country = sale_info.get("country", "")
            Saleability = sale_info.get("saleability", "")
            IsEbook = sale_info.get("isEbook", None)
            Amount_ListPrice = sale_info.get("listPrice", {}).get("amount", None)
            CurrencyCode_ListPrice = sale_info.get("listPrice", {}).get("currencyCode", "")
            Amount_RetailPrice = sale_info.get("retailPrice", {}).get("amount", None)
            CurrencyCode_RetailPrice = sale_info.get("retailPrice", {}).get("currencyCode", "")
            BuyLink = sale_info.get("buyLink", "")
            Year = volume_info.get("publishedDate", "")

            cursor.execute("""
                INSERT OR IGNORE INTO books (
                    Book_Id, Search_Key, Book_Title, Book_Subtitle, Book_Authors, Book_Description, 
                    IndustryIdentifiers, PageCount, Categories, Language, ImageLinks, RatingsCount, 
                    AverageRating, Country, Saleability, IsEbook, Amount_ListPrice, CurrencyCode_ListPrice, 
                    Amount_RetailPrice, CurrencyCode_RetailPrice, BuyLink, Year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (Book_Id, keyword, Book_Title, Book_Subtitle, Book_Authors, Book_Description,
                  IndustryIdentifiers, PageCount, Categories, Language, ImageLinks, RatingsCount,
                  AverageRating, Country, Saleability, IsEbook, Amount_ListPrice, CurrencyCode_ListPrice,
                  Amount_RetailPrice, CurrencyCode_RetailPrice, BuyLink, Year))
        except KeyError as e:
            print(f"Error inserting book {item.get('id', '')}: Missing key {e}")
            continue

    conn.commit()
    conn.close()


def load_books_from_sql(keyword, DB_FILEPATH):
    conn = sqlite3.connect(DB_FILEPATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Book_Id, Search_Key, Book_Title, Book_Subtitle, Book_Authors, 
               Book_Description, IndustryIdentifiers, PageCount, Categories, 
               Language, ImageLinks, RatingsCount, AverageRating, Country, 
               Saleability, IsEbook, Amount_ListPrice, CurrencyCode_ListPrice, 
               Amount_RetailPrice, CurrencyCode_RetailPrice, BuyLink, Year
        FROM books WHERE Search_Key = ?
    """, (keyword,))

    rows = cursor.fetchall()
    conn.close()
    return rows


st.set_page_config(page_title="BookScape Explorer", layout="wide")
st.sidebar.title("BookScape Explorer  📓")
with st.sidebar:
    menu_option = st.selectbox("Menu", ["Search Books", "Analyze Data"])

if menu_option == "Search Books":
    st.header("🔍 Search Books")

    with st.form("search_form"):
        keyword = st.text_input("Enter a keyword to search for books:")
        submit_button = st.form_submit_button(label="Search")

    if submit_button and keyword:
        with st.spinner("Fetching data... ⏳"):
            books = get_books(keyword, api_key)
        if books:
            st.success(f"Found {len(books)} books for the keyword: {keyword}")

            # Save to JSON
            try:
                with open(JSON_FILEPATH, "w") as f:
                    json.dump(books, f, indent=4)
            except Exception as e:
                st.error(f"Error saving JSON: {e}")

            # Save to SQLite
            save_to_sql(books, keyword, DB_FILEPATH)

            # Load and display results
            books_from_db = load_books_from_sql(keyword, DB_FILEPATH)
            df = pd.DataFrame(books_from_db, columns=[
                "Book_Id", "Search_Key", "Book_Title", "Book_Subtitle", "Book_Authors",
                "Book_Description", "IndustryIdentifiers", "PageCount", "Categories", 
                "Language", "ImageLinks", "RatingsCount", "AverageRating", "Country", 
                "Saleability", "IsEbook", "Amount_ListPrice", "CurrencyCode_ListPrice", 
                "Amount_RetailPrice", "CurrencyCode_RetailPrice", "BuyLink", "Year"
            ])
            st.write("### Search Results")
            st.dataframe(df)

            # Display book images with a fallback to placeholder image if no image is found
            for index, row in df.iterrows():
                image_links = json.loads(row['ImageLinks']) if row['ImageLinks'] else None
                if image_links and 'thumbnail' in image_links:
                    image_url = image_links['thumbnail']
                else:
                    image_url = "https://via.placeholder.com/150"  # Placeholder image URL

                st.image(image_url, caption=row['Book_Title'], width=150)
        else:
            st.warning("No books found for the given keyword.")


elif menu_option == "Analyze Data":
    st.markdown("### Explore Book Insights")

    st.markdown("""
        <style>
        .query-card {
            border: 2px solid #4CAF50;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            transition: 0.3s;
            cursor: pointer;
            background-color: #f9f9f9;
        }
        .query-card:hover {
            background-color: #d9f8d9;
            transform: scale(1.02);
            border-color: #3E8E41;
        }
        </style>
    """, unsafe_allow_html=True)


    queries = {
    "Check Availability of eBooks vs Physical Books": """
        SELECT 
            CASE WHEN IsEbook = 1 THEN 'eBooks' ELSE 'Physical Books' END AS Book_Type, 
            COUNT(*) AS Count 
        FROM Books 
        GROUP BY IsEbook;
    """,
    "Find the Publisher with the Most Books Published": """
        SELECT 
            Book_Authors AS Publisher, 
            COUNT(*) AS Num_Books 
        FROM Books 
        WHERE Book_Authors IS NOT NULL AND TRIM(Book_Authors) != ''  -- Ensuring non-null, non-empty authors
        GROUP BY Book_Authors 
        ORDER BY Num_Books DESC 
        LIMIT 10;
    """,
    "Identify the Publisher with the Highest Average Rating": """
        SELECT 
            Book_Authors AS Publisher, 
            AVG(AverageRating) AS Avg_Rating 
        FROM Books 
        WHERE AverageRating IS NOT NULL 
            AND Book_Authors IS NOT NULL 
            AND TRIM(Book_Authors) != ''  -- Ensuring non-null, non-empty authors
        GROUP BY Book_Authors 
        ORDER BY Avg_Rating DESC 
        LIMIT 10;
    """,
    "Get the Top 5 Most Expensive Books by Retail Price": """
        SELECT 
            Book_Title AS Book_Title, 
            Amount_RetailPrice AS  Amount_RetailPrice , 
            CurrencyCode_RetailPrice  as CurrencyCode_RetailPrice
        FROM Books 
        WHERE Amount_RetailPrice IS NOT NULL 
        ORDER BY Amount_RetailPrice DESC 
        LIMIT 5;
    """,
    "Find Books Published After 2010 with at Least 500 Pages": """
        SELECT 
            Book_Title as Book_Title, 
            PageCount as PageCount, 
            Year as Year 
        FROM books 
        WHERE Year >= '2010' AND PageCount >= 500;
    """,
    "List Books with Discounts Greater than 20%": """
        SELECT 
            Book_Title as Book_Title, 
            Amount_ListPrice as Amount_ListPrice, 
            Amount_RetailPrice as  Amount_RetailPrice, 
            100 - (Amount_RetailPrice * 100.0 / Amount_ListPrice) AS Discount_Percentage 
        FROM books 
        WHERE Amount_ListPrice > 0 
            AND Amount_RetailPrice > 0 
            AND (100 - (Amount_RetailPrice * 100.0 / Amount_ListPrice)) > 20;
    """,
    "Find the Average Page Count for eBooks vs Physical Books": """
        SELECT 
            CASE WHEN IsEbook = 1 THEN 'eBooks' ELSE 'Physical Books' END AS Book_Type, 
            AVG(PageCount) AS Avg_Page_Count 
        FROM books 
        WHERE PageCount IS NOT NULL 
        GROUP BY IsEbook;
    """,
    "Find the Top 3 Authors with the Most Books": """
        SELECT 
            Book_Authors as Book_Authors , 
            COUNT(*) AS Num_Books 
        FROM books 
        WHERE Book_Authors IS NOT NULL AND TRIM(Book_Authors) != ''  -- Ensuring non-null, non-empty authors
        GROUP BY Book_Authors 
        ORDER BY Num_Books DESC 
        LIMIT 3;
    """,
    "List Publishers with More than 10 Books": """
        SELECT 
            Book_Authors AS Publisher, 
            COUNT(*) AS Num_Books 
        FROM books 
        WHERE Book_Authors IS NOT NULL AND TRIM(Book_Authors) != ''  -- Ensuring non-null, non-empty authors
        GROUP BY Book_Authors 
        HAVING Num_Books > 10;
    """,
    "Find the Average Page Count for Each Category": """
        SELECT 
            Categories as Categories, 
            AVG(PageCount) AS Avg_Page_Count 
        FROM books 
        WHERE Categories IS NOT NULL AND PageCount IS NOT NULL 
        GROUP BY Categories 
        ORDER BY Avg_Page_Count DESC;
    """,
    "Retrieve Books with More than 3 Authors": """
        SELECT 
            Book_Title as Book_Title, 
            Book_Authors as Book_Authors 
        FROM books 
        WHERE LENGTH(Book_Authors) - LENGTH(REPLACE(Book_Authors, ',', '')) + 1 > 3;
    """,
    "Books with Ratings Count Greater Than the Average": """
        SELECT 
            Book_Title as Book_Title, 
            RatingsCount as RatingsCount    
        FROM books 
        WHERE RatingsCount > (SELECT AVG(RatingsCount) FROM books);
    """,
    "Books with the Same Author Published in the Same Year": """
        SELECT 
            Book_Authors as Book_Author, 
            Year as Year, 
            COUNT(*) AS Num_Books 
        FROM books 
        WHERE Book_Authors IS NOT NULL AND Year IS NOT NULL AND TRIM(Book_Authors) != ''  -- Ensuring non-null, non-empty authors
        GROUP BY Book_Authors, Year 
        HAVING Num_Books > 1;
    """,
    "Books with a Specific Keyword in the Title": """
        SELECT 
            Book_Title as BookTitle_SameAsKeyword
        FROM books 
        ;
    """,
    "Year with the Highest Average Book Price": """
        SELECT 
            SUBSTR(Year, 1, 4) AS Publication_Year, 
            AVG(Amount_RetailPrice) AS Avg_Price 
        FROM books 
        WHERE Year IS NOT NULL 
        GROUP BY Publication_Year 
        ORDER BY Avg_Price DESC 
        LIMIT 1;
    """,
    "Count Authors Who Published 3 Consecutive Years": """
        SELECT 
            Book_Authors as Book_Authors, 
            COUNT(DISTINCT SUBSTR(Year, 1, 4)) AS Consecutive_Years 
        FROM books 
        WHERE Year IS NOT NULL 
            AND Book_Authors IS NOT NULL 
            AND TRIM(Book_Authors) != ''  -- Ensuring non-null, non-empty authors
        GROUP BY Book_Authors 
        HAVING Consecutive_Years >= 3;
    """,
    "Authors Published Books in Same Year, Different Publishers": """
        SELECT 
            Book_Authors as Book_Authors, 
            SUBSTR(Year, 1, 4) AS Publication_Year, 
            COUNT(DISTINCT Book_Authors) AS Num_Publishers 
        FROM books 
        WHERE Book_Authors IS NOT NULL 
        GROUP BY Book_Authors, Publication_Year 
        HAVING Num_Publishers > 1;
    """,
    "Average Retail Price of eBooks vs Physical Books": """
        SELECT 
            AVG(CASE WHEN IsEbook = 1 THEN Amount_RetailPrice END) AS Avg_Ebook_Price, 
            AVG(CASE WHEN IsEbook = 0 THEN Amount_RetailPrice END) AS Avg_Physical_Price 
        FROM books;
    """,
    "Books with Ratings Far from Average (Outliers)": """
        SELECT 
            Book_Title as Book_Title , AverageRating as AverageRating, RatingsCount as RatingCount 
        FROM books 
        WHERE ABS(AverageRating - (SELECT AVG(AverageRating) FROM books)) > 
        (2 * (SELECT SUM((AverageRating - (SELECT AVG(AverageRating) FROM books)) * 
        (AverageRating - (SELECT AVG(AverageRating) FROM books))) 
      / COUNT(AverageRating) 
       FROM books));
    """,
    "Publisher with Highest Average Rating (Min 10 Books)": """
        SELECT 
            Book_Authors AS Publisher, 
            AVG(AverageRating) AS Avg_Rating, 
            COUNT(*) AS Num_Books 
        FROM books 
        WHERE AverageRating IS NOT NULL 
            AND Book_Authors IS NOT NULL 
            AND TRIM(Book_Authors) != ''  -- Ensuring non-null, non-empty authors
        GROUP BY Book_Authors 
        HAVING Num_Books > 10 
        ORDER BY Avg_Rating DESC 
        LIMIT 1;
    """
}

    for query_name, sql_query in queries.items():
       if st.button(query_name):
        try:
            with sqlite3.connect(DB_FILEPATH) as conn:
                result_df = pd.read_sql_query(sql_query, conn)

            # Check if the query returned results
            if not result_df.empty:
                result_df.index = result_df.index + 1  # Adjusting index to start from 1
                st.write(f"**Results for: {query_name}**")
                st.dataframe(result_df)
                result_df.columns = result_df.columns.str.lower()  # Converts all column names to lowercase

                
            else:
                st.warning("No results found for this query.")
        except Exception as e:
            st.error(f"Error executing query: {e}")