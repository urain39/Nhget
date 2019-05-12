#!/usr/bin/env python3

from flask import Flask
from flask import render_template


app = Flask(__name__)

@app.errorhandler(404)
def error_page_not_found(error):
    return render_template('404.html', error=error)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/post/<caption>', methods=['GET'])
def post(caption=None):
    return render_template('post.html', caption=caption)

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

def main():
    app.run()

if __name__ == '__main__':
    main()

