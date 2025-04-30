import mysql.connector
from mysql.connector import Error

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'student_performance_db'
}

def test_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Successfully connected to the database")
            connection.close()
        else:
            print("Failed to connect to the database")
    except Error as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_connection()
