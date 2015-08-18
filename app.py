
import os
from flask import Flask, render_template, request, url_for, send_from_directory
from werkzeug import secure_filename
from splice import *
from PIL import Image
from io import BytesIO
import base64
from contextlib import closing
import random
import string
import time


# constants
IMAGES_FOLDER = 'images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])



# config
app = Flask(__name__, static_url_path="")
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB
app.config.from_object(__name__)
db = {}



# routes
@app.route('/')
def index():
	db.clear()
	print "filename_split: ", construct_random_filename('test.jpg')
	return render_template("step1.html")


@app.route('/submit_source', methods=['POST'])
def submit_source():
	if request.method == 'POST' and 'source' in request.files:
		source = request.files['source']
		db['source_filename'] = construct_random_filename(secure_filename(source.filename))
		source.save(os.path.join(app.config['IMAGES_FOLDER'], db['source_filename']))

		return render_template("step2.html", source_filename=db['source_filename'])


@app.route('/submit_mask', methods=['POST'])
def submit_mask():
	if request.method == 'POST':
		img_data = request.values['imgData']
		img_data = img_data[22:] # strips out the data:image/png;base64, part of the string

		maskImg = Image.open(BytesIO(img_data.decode('base64')))
		db['mask_filename'] = construct_random_filename('mask.png')
		maskImg.save(os.path.join(app.config['IMAGES_FOLDER'], db['mask_filename']))

		return render_template("step3.html")


@app.route('/submit_target', methods=['POST'])
def submit_target():
	if request.method == 'POST':
		# upload target
		target = request.files['target']
		if target and allowed_file(target.filename):
			db['target_filename'] = construct_random_filename(secure_filename(target.filename))
			print "db keys: ", db.keys()
			target.save(os.path.join(app.config['IMAGES_FOLDER'], db['target_filename']))

			# do all the region math here and pass it into template
			target_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['target_filename']))
			source_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['source_filename']))
			
			db['mask'] = create_mask_from_image(Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['mask_filename'])))
			size_info = get_size_info(source_im, target_im, db['mask'])

			db.update(size_info) # sets db values

			return render_template("step4.html", target_filename=db['target_filename'],
												half_region_height=db['half_region_height'],
												half_region_width=db['half_region_width'],
												targeth=db['targeth'],
												targetw=db['targetw'])

@app.route('/submit_offset', methods=['POST'])
def submit_offset():
	print "db currently: ", db
	if request.method == 'POST':
		# get offsets
		offX = int(request.form['offX'])
		offY = int(request.form['offY'])

		# open images
		target_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['target_filename']))
		source_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['source_filename']))

		maskImg = Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['mask_filename']))

		result = splice(source_im, target_im, db['mask'], offY, offX, db)
		db['result_filename'] = construct_random_filename('result.png')
		result.save(os.path.join(app.config['IMAGES_FOLDER'], db['result_filename']))
		return render_template("result.html", result_filename=db['result_filename'])



# serving files
@app.route('/images/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['IMAGES_FOLDER'], filename)




# helper functions
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def construct_random_filename(filename):
	# returns filename_randomstring.ext
	filename_split = filename.split('.')
	result_filename = filename_split[0] + '_' + random_string() + '.' + filename_split[1]
	return result_filename

def random_string(N=6):
	return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))




# cron job: delete files older than 2 hours
def delete_files():
	# seconds * minutes
	three_hours_ago = time.time() - 60 * 120
	folder = app.config['IMAGES_FOLDER']
	os.chdir(folder)
	for f in os.listdir('.'):
		if os.path.getmtime(f) < three_hours_ago:
			print('remove %s'%f)
			os.unlink(f)
# to run on command line: python -c 'import app; app.delete_files()'



if __name__ == '__main__':
	app.debug=True
	app.run()