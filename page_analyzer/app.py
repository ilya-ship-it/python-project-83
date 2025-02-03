import os
import validators
import psycopg2
from datetime import datetime
from flask import Flask, render_template, redirect, request, flash, url_for
from dotenv import load_dotenv
from urllib.parse import urlparse
from bs4 import BeautifulSoup


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
                cur.execute(
                    'INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id;',
                    (normalized_url, created_at)
                )
                id = cur.fetchone()[0]
                conn.commit()
                flash('Страница успешно добавлена', 'success')
            except psycopg2.errors.UniqueViolation:
                cur.execute('SELECT id FROM urls WHERE name = %s;', (normalized_url,))
                id = cur.fetchone()[0]
                flash('Страница уже существует', 'error')
    return redirect(url_for('show_url', id=id))

@app.route('/urls/<int:id>')
def show_url(id):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, name, created_at FROM urls WHERE id = %s;', (id,))
            url = cur.fetchone()
            cur.execute(
                'SELECT id, status_code, created_at FROM url_checks WHERE url_id = %s ORDER BY created_at DESC;',
                (id,)
            )
            checks = cur.fetchall()
    if url:
        return render_template('url.html', url=url, checks=checks)
    return redirect(url_for('list_urls'))

@app.route('/urls')
def list_urls():
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT urls.id, urls.name, MAX(url_checks.created_at), url_checks.status_code
                FROM urls 
                LEFT JOIN url_checks ON urls.id = url_checks.url_id
                GROUP BY urls.id
                ORDER BY urls.id DESC;
            """)
            urls = cur.fetchall()
    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            created_at = datetime.now().strftime('%Y-%m-%d')  
            cur.execute('SELECT name FROM urls WHERE id = %s;', (id,))
            url = cur.fetchone()[0]

    try:
        responce = request.get(url, timeout=1)
        responce.raise_for_status()
        status_code = responce.status_code
    except request.exceptions.RequestException:
        flash('Произошла ошибка при проверке', 'error')
        return redirect(url_for('show_url', id=id))
    
    soup = BeautifulSoup(responce.text, 'html.parser')
    h1 =  soup.h1.text
    title = soup.title.text
    description_tag = soup.find('meta', {'name': 'description'})
    description = description_tag['content'] if description_tag else None

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO url_checks (url_id, status_code, h1, title, description, created_at) VALUES (%s, %s, %s, %s, %s, %s);',
                (id, status_code, h1, title, description, created_at)
            )
            conn.commit()
            flash('Страница успешно проверена', 'success')
    return redirect(url_for('show_url'), id=id)


if __name__ == '__main__':
    app.run(debug=True)
