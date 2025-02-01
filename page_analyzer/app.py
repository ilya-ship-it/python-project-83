import os
import validators
import psycopg2
from datetime import datetime
from flask import Flask, render_template, redirect, request, flash, url_for
from dotenv import load_dotenv
from urllib.parse import urlparse


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/urls', methods=['POST'])
def add_url():
    url = request.form.get('url')
    if not validators.url(url):
        return "Некорректный URL", 422
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id;", (normalized_url, datetime.now()))
                url_id = cur.fetchone()[0]
                conn.commit()
                flash('url успешно добавлен')
            except psycopg2.errors.UniqueViolation:
                flash('url уже существует')
    return redirect(url_for('show_url', url_id=url_id))

@app.route('/urls/<int:url_id>')
def show_url(url_id):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM urls WHERE id = %s;", (url_id,))
            url = cur.fetchone()
    if url:
        return render_template('url.html', url=url)
    return redirect(url_for('list_urls'))

@app.route('/urls', methods=['GET'])
def list_urls():
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM urls;")
            urls = cur.fetchall()
    return render_template("urls.html", urls=urls)


if __name__ == '__main__':
    app.run(debug=True)
