import os
from flask import Flask, jsonify, g, redirect, request, url_for, render_template, send_from_directory
from werkzeug import secure_filename

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
UPLOAD_FOLDER = 'uploads'
SCRIPT_FOLDER = 'scripts'

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SCRIPT_FOLDER'] = SCRIPT_FOLDER


# serving static files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
	
@app.route('/scripts/<filename>')
def script_file(filename):
	return send_from_directory(app.config['SCRIPT_FOLDER'], filename)
	


@app.route('/_add_numbers')
def add_numbers():
	print request.args
	a = request.args.get('a', 0, type=int)
	b = request.args.get('b', 0, type=int)
	return jsonify(result=a + b)
	
@app.route('/process_image', methods=['GET', 'POST'])
def process_image():
	if request.method == 'POST':
		file = request.files['file']
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			print file.filename
			return jsonify(result=file.filename)
	return file

@app.route('/')
def index():
	return render_template('index.html')


@app.route('/step1')
def step1():
	return render_template('step1.html')
	
@app.route('/step2', methods=['GET', 'POST'])
def step2():
	if request.method == 'POST':
		file = request.files['file']
		if file and allowed_file(file.filename):
				filename = secure_filename(file.filename)
				file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
				return render_template('step2.html', filename=filename)

@app.route('/result', methods=['GET', 'POST'])
def result():
	return render_template('result.html', filename=filename)

if __name__ == '__main__':
	app.run(debug=True)