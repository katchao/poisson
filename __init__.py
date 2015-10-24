
import os
from flask import Flask, session, render_template, request, url_for, send_from_directory

from werkzeug import secure_filename

from splice import *
from PIL import Image
from io import BytesIO
import base64
import random
import string
import time
import settings
import sqlite3
import json
import numpy as np



from flask.sessions import SessionInterface, SessionMixin
from redis import Redis
from uuid import uuid4
import pickle
from werkzeug.datastructures import CallbackDict
from datetime import timedelta




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

class RedisSession(CallbackDict, SessionMixin):

    def __init__(self, initial=None, sid=None, new=False):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class RedisSessionInterface(SessionInterface):
    serializer = pickle
    session_class = RedisSession

    def __init__(self, redis=None, prefix='session:'):
        if redis is None:
            redis = Redis()
        self.redis = redis
        self.prefix = prefix

    def generate_sid(self):
        return str(uuid4())

    def get_redis_expiration_time(self, app, session):
        if session.permanent:
            return app.permanent_session_lifetime
        return timedelta(days=1)

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if not sid:
            sid = self.generate_sid()
            return self.session_class(sid=sid, new=True)
        val = self.redis.get(self.prefix + sid)
        if val is not None:
            data = self.serializer.loads(val)
            return self.session_class(data, sid=sid)
        return self.session_class(sid=sid, new=True)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        if not session:
            self.redis.delete(self.prefix + session.sid)
            if session.modified:
                response.delete_cookie(app.session_cookie_name,
                                       domain=domain)
            return
        redis_exp = self.get_redis_expiration_time(app, session)
        cookie_exp = self.get_expiration_time(app, session)
        val = self.serializer.dumps(dict(session))
        self.redis.setex(self.prefix + session.sid, val,
                         int(redis_exp.total_seconds()))
        response.set_cookie(app.session_cookie_name, session.sid,
                            expires=cookie_exp, httponly=True,
                            domain=domain)

# config
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB
app.config.from_object(__name__)
app.secret_key = "A0Zr98j/3yX R~XHH!jmN]LWX/,?RT"
app.session_interface = RedisSessionInterface()

class NumpyEncoder(json.JSONEncoder):

    def default(self, obj):
        """If input object is an ndarray it will be converted into a dict 
        holding dtype, shape and the data, base64 encoded.
        """
        if isinstance(obj, np.ndarray):
            if obj.flags['C_CONTIGUOUS']:
                obj_data = obj.data
            else:
                cont_obj = np.ascontiguousarray(obj)
                assert(cont_obj.flags['C_CONTIGUOUS'])
                obj_data = cont_obj.data
            data_b64 = base64.b64encode(obj_data)
            return dict(__ndarray__=data_b64,
                        dtype=str(obj.dtype),
                        shape=obj.shape)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder(self, obj)


def json_numpy_obj_hook(dct):
    """Decodes a previously encoded numpy ndarray with proper shape and dtype.

    :param dct: (dict) json encoded ndarray
    :return: (ndarray) if input was an encoded ndarray
    """
    if isinstance(dct, dict) and '__ndarray__' in dct:
        data = base64.b64decode(dct['__ndarray__'])
        return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])
    return dct

# REDDIS TESTING

@app.route('/test1')
def test1():
	session['test1']=1
	return render_template("test.html", session=session)

@app.route('/test2')
def test2():
	session['test2']=2

	return render_template("test.html", session=session)

@app.route('/test3')
def test3():
	session['test3']=3
	print session.keys()
	return render_template("test.html", session=session)

@app.route('/clear')
def clear():
	session.clear()
	return render_template("test.html", session=session)


#################


# routes
@app.route('/')
def index():
	print "session keys 1: ", session.keys()
	return render_template("upload-images.html")


@app.route('/submit_images', methods=['POST'])
def submit_images():
	if request.method == 'POST' and 'source' in request.files and 'target' in request.files:
		source = request.files['source']
		session['source_filename'] = construct_random_filename(secure_filename(source.filename))
		source.save(os.path.join(app.config['IMAGES_FOLDER'], session['source_filename']))

		target = request.files['target']
		session['target_filename'] = construct_random_filename(secure_filename(target.filename))
		target.save(os.path.join(app.config['IMAGES_FOLDER'], session['target_filename']))

		session.modified = True
		print "session keys 2: ", session.keys()
		return render_template("step2.html", source_filename=session['source_filename'])
	else:
		return "asdf"


@app.route('/submit_mask', methods=['POST'])
def submit_mask():
	if request.method == 'POST':
		img_data = request.values['imgData']
		img_data = img_data[22:] # strips out the data:image/png;base64, part of the string

		maskImg = Image.open(BytesIO(img_data.decode('base64')))
		session['mask_filename'] = construct_random_filename('mask.png')

		maskImg.save(os.path.join(app.config['IMAGES_FOLDER'], session['mask_filename']))

		# do all the region math here and pass it into template
		target_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], session['target_filename']))
		source_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], session['source_filename']))
		
		# create the mask
		mask_array = create_mask_from_image(Image.open(os.path.join(app.config['IMAGES_FOLDER'], session['mask_filename'])))
		session['mask'] = json.dumps(mask_array, cls=NumpyEncoder)

		# do math
		size_info = get_size_info(source_im, target_im, mask_array)

		session['startX'] = size_info['startX']
		session['startY'] = size_info['startY']
		session['targeth'] = size_info['targeth']
		session['targetw'] = size_info['targetw']
		session['sourcew'] = size_info['sourcew']
		session['sourceh'] = size_info['sourceh']
		session['half_region_width'] = size_info['half_region_width']
		session['half_region_height'] = size_info['half_region_height']
		session['region_width'] = size_info['region_width']
		session['region_height'] = size_info['region_height']
		session['endY'] = size_info['endY']
		session['endX'] = size_info['endX']
		session['yNon'] = json.dumps(size_info['yNon'], cls=NumpyEncoder)
		session['xNon'] = json.dumps(size_info['xNon'], cls=NumpyEncoder)

		session.modified = True

		print "Session keys3: ", session.keys()

		return render_template("step4.html", target_filename=session['target_filename'],
											half_region_height=session['half_region_height'],
											half_region_width=session['half_region_width'],
											targeth=session['targeth'],
											targetw=session['targetw'])



@app.route('/submit_offset', methods=['POST'])
def submit_offset():
	if request.method == 'POST':
		# get offsets
		offX = int(request.form['offX'])
		offY = int(request.form['offY'])

		print "Session keys4: ", session.keys()

		# open images
		target_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], session['target_filename']))
		source_im = Image.open(os.path.join(app.config['IMAGES_FOLDER'], session['source_filename']))
		maskImg = Image.open(os.path.join(app.config['IMAGES_FOLDER'], session['mask_filename']))


		jsonMaskToNp = json.loads(session['mask'], object_hook=json_numpy_obj_hook)
		jsonMaskToNp.setflags(write=True)
		
		# rebuild dictionary to pass into function
		bounds = {}
		bounds['startX'] = session['startX']
		bounds['startY'] = session['startY']
		bounds['targeth'] = session['targeth']
		bounds['targetw'] = session['targetw']
		bounds['sourcew'] = session['sourcew']
		bounds['sourceh'] = session['sourceh']
		bounds['half_region_width'] = session['half_region_width']
		bounds['half_region_height'] = session['half_region_height']
		bounds['region_width'] = session['region_width']
		bounds['region_height'] = session['region_height']
		bounds['endY'] = session['endY']
		bounds['endX'] = session['endX']
		bounds['yNon'] = json.loads(session['yNon'], object_hook=json_numpy_obj_hook)
		bounds['xNon'] = json.loads(session['xNon'], object_hook=json_numpy_obj_hook)

		result = splice(source_im, target_im, jsonMaskToNp, offY, offX, bounds)


		session['result_filename'] = construct_random_filename('result.png')
		result.save(os.path.join(app.config['IMAGES_FOLDER'], session['result_filename']))
		
		return render_template("result.html", result_filename=session['result_filename'])



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