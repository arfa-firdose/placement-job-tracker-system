import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="232011*Sf9635",
        database="job_tracker"
    )