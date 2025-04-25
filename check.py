import psycopg2

try:
    connection = psycopg2.connect(
        dbname='voting_db',
        user='brad_pitt',
        password='twelvemonkeys',
        host='localhost',
        port='5432'
    )
    print("Connection successful")
except Exception as e:
    print(f"An error occurred: {e}")