
from flask import Flask, render_template, request, url_for
from splice import *
app = Flask(__name__)

@app.route('/')
def index():
	return render_template("main.html")

@app.route('/submit/', methods=['POST'])
def submit():
	test()
	name=request.form['name']
	email=request.form['email']
	return render_template("form_submitted.html", name=name, email=email)

@app.route('/hello')
@app.route('/hello/<name>')
def hello_world(name=None):
    return 'Hello %s!' % name

if __name__ == '__main__':
	app.debug=True
	app.run()
