#!/usr/bin/env python3

from flask import Flask
from flask import request
from flask import render_template

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

def main():
    app.run()

if __name__ == '__main__':
    main()

