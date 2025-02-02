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
        return 'Некорректный URL', 422
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            try:
                created_at = datetime.now().strftime('%Y-%m-%d')
                cur.execute('INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id;', (normalized_url, created_at))
                id = cur.fetchone()[0]
                conn.commit()
                flash('Страница успешно добавлена')
            except psycopg2.errors.UniqueViolation:
                flash('Страница уже существует')
    return redirect(url_for('show_url', id=id))

@app.route('/urls/<int:id>')
def show_url(id):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, name, created_at FROM urls WHERE id = %s;', (id,))
            url = cur.fetchone()
    if url:
        return render_template('url.html', url=url)
    return redirect(url_for('list_urls'))

@app.route('/urls')
def list_urls():
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT urls.id, urls.name, MAX(url_checks.created_at), url_checks.status_code  FROM urls LEFT JOIN url_checks ON urls.id = url_checks.url_id;')
            urls = cur.fetchall()
    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    with psycopg2.connect(DATABASE_URL) as conn:
         with conn.cursor() as cur:
             created_at = datetime.now().strftime('%Y-%m-%d')
             cur.execute('INSERT INTO url_checks (url_id, created_at) VALUES (%s, %s) RETURNING id;', (id, created_at))
             conn.commit()
             flash('')
    return redirect(url_for('show_url'), id=id)


if __name__ == '__main__':
    app.run(debug=True)
