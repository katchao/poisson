
import os
from flask import Flask, render_template, request, url_for, send_from_directory
from werkzeug import secure_filename
from splice import *
from PIL import Image
from io import BytesIO
import base64
import shelve
from cPickle import HIGHEST_PROTOCOL
from contextlib import closing


# constants
UPLOAD_FOLDER = 'images'
SCRIPT_FOLDER = 'scripts'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
SHELVE_DB = 'shelve.db'



# config
app = Flask(__name__, static_url_path="")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SCRIPT_FOLDER'] = SCRIPT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB
app.config.from_object(__name__)
db = shelve



# routes
@app.route('/')
def index():
	return render_template("step1.html")


@app.route('/submit_source', methods=['POST'])
def submit_source():
	if request.method == 'POST' and 'source' in request.files:
		source = request.files['source']
		db['source_filename'] = secure_filename(source.filename)
		source.save(os.path.join(app.config['UPLOAD_FOLDER'], db['source_filename']))

		return render_template("step2.html", source_filename=db['source_filename'])


@app.route('/submit_mask', methods=['POST'])
def submit_mask():
	if request.method == 'POST':
		img_data = request.values['imgData']
		img_data = img_data[22:] # strips out the data:image/png;base64, part of the string

		maskImg = Image.open(BytesIO(img_data.decode('base64')))
		maskImg.save(os.path.join(app.config['UPLOAD_FOLDER'], "mask.png"))

		return render_template("step3.html")


@app.route('/submit_target', methods=['POST'])
def submit_target():
	if request.method == 'POST':
		# upload target
		target = request.files['target']
		if target and allowed_file(target.filename):
			db['target_filename'] = secure_filename(target.filename)
			target.save(os.path.join(app.config['UPLOAD_FOLDER'], db['target_filename']))

			# do all the region math here and pass it into template
			target_im = Image.open(db['target_filename'])
			source_im = Image.open(db['source_filename'])
			mask = create_mask_from_image(Image.open(os.path.join(app.config['UPLOAD_FOLDER'], "mask.png")))
			size_info = get_size_info(source_im, target_im, mask)

			targeth = size_info["targeth"]
			targetw = size_info["targetw"]
			half_region_height = size_info["half_region_height"]
			half_region_width = size_info["half_region_width"]

		return render_template("step4.html", target_filename=db['target_filename'],
												half_region_height=half_region_height,
												half_region_width=half_region_width,
												targeth=targeth,
												targetw=targetw)


@app.route('/submit_offset', methods=['POST'])
def submit_offset():
	if request.method == 'POST':
		# get offsets
		offX = int(request.form['offX'])
		offY = int(request.form['offY'])

		# open images
		target_im = Image.open(db['target_filename'])
		source_im = Image.open(db['source_filename'])
		maskImg = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], "mask.png"))

		# process the images
		result = splice(source_im, target_im, maskImg, offY, offX, True)
		result.save(os.path.join(app.config['UPLOAD_FOLDER'], 'result.png'), "PNG")

		print "keys: ", db.keys()
		db.close()
		return render_template("result.html")



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

if __name__ == '__main__':
	app.debug=True
	db = shelve.open(os.path.join(app.root_path, app.config['SHELVE_DB']), protocol=HIGHEST_PROTOCOL, writeback=False)
	app.run()