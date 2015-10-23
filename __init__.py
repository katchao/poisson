
import os
from flask import Flask, render_template, request, url_for, send_from_directory
from werkzeug import secure_filename
from splice import *
from PIL import Image
from io import BytesIO
import base64
import random
import string
import time
import settings

# shelve
from cPickle import HIGHEST_PROTOCOL
from contextlib import closing
import shelve




app = Flask(__name__, static_url_path="")


if(settings.PROD):
	class WebFactionMiddleware(object):
	    def __init__(self, app):
	        self.app = app
	    def __call__(self, environ, start_response):
	        environ['SCRIPT_NAME'] = '/imagestitch'
	        return self.app(environ, start_response)

	app.wsgi_app = WebFactionMiddleware(app.wsgi_app)


# constants
if(settings.PROD):
	IMAGES_FOLDER = '/images'
else:
	IMAGES_FOLDER = 'images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])



# config
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB
app.config['SHELVE_DB'] = 'shelve.db'
app.config.from_object(__name__)

#db = shelve.open(os.path.join(app.root_path, app.config['SHELVE_DB']), protocol=HIGHEST_PROTOCOL, writeback=True)
db = {}

# routes
@app.route('/')
def index():
	db.clear()
	return render_template("upload-images.html")


@app.route('/submit_images', methods=['POST'])
def submit_images():
	if request.method == 'POST' and 'source' in request.files and 'target' in request.files:
		source = request.files['source']
		db['source_filename'] = construct_random_filename(secure_filename(source.filename))
		source.save(os.path.join(app.config['IMAGES_FOLDER'], db['source_filename']))

		target = request.files['target']
		db['target_filename'] = construct_random_filename(secure_filename(target.filename))
		target.save(os.path.join(app.config['IMAGES_FOLDER'], db['target_filename']))

		return render_template("step2.html", source_filename=db['source_filename'])
	else:
		return "asdf"


@app.route('/submit_mask', methods=['POST'])
def submit_mask():
	if request.method == 'POST':
		img_data = request.values['imgData']
		img_data = img_data[22:] # strips out the data:image/png;base64, part of the string

		maskImg = Image.open(BytesIO(img_data.decode('base64')))
		db['mask_filename'] = construct_random_filename('mask.png')
		maskImg.save(os.path.join(app.config['IMAGES_FOLDER'], db['mask_filename']))

		# do all the region math here and pass it into template
		target_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['target_filename']))
		source_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['source_filename']))
		
		db['mask'] = create_mask_from_image(Image.open(os.path.join(app.config['IMAGES_FOLDER'], db['mask_filename'])))
		size_info = get_size_info(source_im, target_im, db['mask'])

		db.update(size_info) # sets db values

		print db.keys()

		return render_template("step4.html", target_filename=db['target_filename'],
											half_region_height=db['half_region_height'],
											half_region_width=db['half_region_width'],
											targeth=db['targeth'],
											targetw=db['targetw'])



@app.route('/submit_offset', methods=['POST'])
def submit_offset():
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
	app.debug = not settings.PROD
	app.run()