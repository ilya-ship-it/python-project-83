import os
import validators
import psycopg2
import requests
import page_analyzer.db as db
from flask import Flask, render_template, redirect, request, flash, url_for
from dotenv import load_dotenv
from urllib.parse import urlparse
from bs4 import BeautifulSoup


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def add_url():
    url = request.form.get('url')
    if not validators.url(url):
        flash('Некорректный URL', 'danger')
        return render_template('index.html')
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    conn = db.get_connection()
    try:
        id = db.add_url(conn, normalized_url)
        db.commit(conn)
        flash('Страница успешно добавлена', 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        url = db.get_url_by_name(conn, normalized_url)
        id = url.id
        flash('Страница уже существует', 'info')
    conn.close()
    return redirect(url_for('show_url', id=id))


@app.route('/urls/<int:id>')
def show_url(id):
    conn = db.get_connection()
    url = db.get_url(conn, id)
    checks = db.get_checks(conn, id)
    conn.close()
    if url:
        return render_template('url.html', url=url, checks=checks)
    return redirect(url_for('list_urls'))


@app.route('/urls')
def list_urls():
    conn = db.get_connection()
    urls = db.get_all_urls(conn)
    conn.close()
    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    conn = db.get_connection()
    url = db.get_url(conn, id)
    try:
        responce = requests.get(url.name, timeout=2)
        responce.raise_for_status()
        status_code = responce.status_code
    except requests.exceptions.RequestException:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('show_url', id=id))

    soup = BeautifulSoup(responce.text, 'html.parser')
    h1 = soup.find('h1').text[:255] if soup.find('h1') else None
    title = soup.find('title').text[:255] if soup.find('title') else None
    meta_tag = soup.find('meta', {'name': 'description'})
    description = meta_tag.get('content')[:255] if meta_tag else None

    check = db.URLCheck(
        url_id=id,
        status_code=status_code,
        h1=h1, title=title,
        description=description
    )
    db.add_check(conn, check)
    db.commit(conn)
    conn.close()
    flash('Страница успешно проверена', 'success')
    return redirect(url_for('show_url', id=id))


if __name__ == '__main__':
    app.run(debug=True)
