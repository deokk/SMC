from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 로드

api_key = os.getenv("SEOUL_API_KEY")
db_user = os.getenv("DB_USER")

print(f"API KEY: {api_key}")
print(f"DB USER: {db_user}")

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, SMC Backend! 🚲'

if __name__ == '__main__':
    app.run(debug=True)
