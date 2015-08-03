
import os
from flask import Flask, render_template, request, url_for, send_from_directory
from werkzeug import secure_filename
from splice import *
from PIL import Image
from io import BytesIO
import base64

# constants
UPLOAD_FOLDER = 'images'
SCRIPT_FOLDER = 'scripts'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

# config
app = Flask(__name__, static_url_path="")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SCRIPT_FOLDER'] = SCRIPT_FOLDER


# routes
@app.route('/')
def index():
	return render_template("main.html")

@app.route('/create-mask')
def create_mask():
	return render_template("create-mask.html")


@app.route('/submit/', methods=['POST'])
def submit():
	if request.method == 'POST':
		source = request.files['source']
		if source and allowed_file(source.filename):
			filename = secure_filename(source.filename)
			source.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

		target = request.form['target']
		m = request.form['mask']
		result_filename = "result.png"

		source_im = Image.open(source.filename)
		target_im = Image.open(target)
		m_im = Image.open(m)

		result = splice(source_im, target_im, m_im, True)
		result.save(os.path.join(app.config['UPLOAD_FOLDER'], result_filename), "PNG")
		return render_template("form_submitted.html")

@app.route('/mask-send', methods=['GET', 'POST'])
def mask_send():
	if request.method == 'POST':
		result_filename = "result.png"
		source_im = Image.open("niccage.png")
		target_im = Image.open("apple.png")

		### START PROCESSING INPUT MASK
		imgData = request.values["imgData"]
		imgData = imgData[22:] # strips out the data:image/png;base64, part of the string
		print "imgData: ", imgData

		maskImg = Image.open(BytesIO(imgData.decode('base64')))

		"""
		fh = open("dynamicMask.png", "wb")
		fh.write(imgData.decode('base64'))
		fh.close()

		Image.open("dynamicMask.png").show()
		"""
		m_im = Image.open("download.png")
		### END PROCESSING INPUT MASK

		result = splice(source_im, target_im, maskImg, True)
		result.save(os.path.join(app.config['UPLOAD_FOLDER'], result_filename), "PNG")
		return render_template("form_submitted.html")
		
	if request.method == 'GET':
		return render_template("form_submitted.html")




# serving files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/scripts/<filename>')
def script_file(filename):
	return send_from_directory(app.config['SCRIPT_FOLDER'], filename)




# helper functions
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS



@app.route('/hello')
@app.route('/hello/<name>')
def hello_world(name=None):
	return 'Hello %s!' % name

if __name__ == '__main__':
	app.debug=True
	app.run()
