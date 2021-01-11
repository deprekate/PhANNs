import html
import time
import os
from flask import Flask, flash, request, redirect, url_for, render_template, Response
from werkzeug.utils import secure_filename
from flask import send_from_directory , Markup, send_file
import subprocess
import pickle
import ntpath
#import Phanns_f
import ann_config
from tensorflow.keras.models import load_model
import tensorflow as tf
from flask_socketio import SocketIO, emit
from random import *
import json
import sys
from flask import session

import random
import string


def randomStringDigits(stringLength=6):
    """Generate a random string of letters and digits """
    random.seed()
    lettersAndDigits = string.ascii_letters + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))

from Bio import SeqIO

ROOT_FOLDER = os.path.dirname(os.path.realpath(__file__)) 
UPLOAD_FOLDER = ROOT_FOLDER + '/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'faa', 'fasta', 'gif', 'fa'])
import urllib
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"   # see issue #152
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["KERAS_BACKEND"]="tensorflow"
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_4853rfgttr5!'
app.config['FASTA_SIZE_LIMIT']=5000

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config['APPLICATION_ROOT']='/adrian_net'
app.config['APPLICATION_ROOT']=ann_config.prefix
#app.config['APPLICATION_ROOT']=''
PREFIX=app.config['APPLICATION_ROOT'] 

def fix_url_for(path, **kwargs):
    return PREFIX + url_for(path, **kwargs)

@app.context_processor
def contex():
    return dict(fix_url_for = fix_url_for)

#add the sorable attribute to tables generated by pandas
@app.template_filter('sorttable')
def sorttable_filter(s):
    s= s.replace('table id=','table class="sortable" id=')
    return s


def prot_check(sequence):
    return (set(sequence.upper()).issubset("ABCDEFGHIJKLMNPQRSTVWXYZ*") and (len(sequence)>0))



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def bar(filename):
    return redirect(url_for('wait_page',filename=filename))
    
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
         #   return redirect()
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            #filename = secure_filename(file.filename)
            filename = randomStringDigits(15) + '.fasta' 
            file.save(os.path.join('temp_saves', filename))
            print("renamed file: " + file.filename + ' ---> ' + filename)
            #print( fix_url_for('bar',filename=filename))
            #print( url_for('bar',filename=filename))
            total_fasta=0
            all_fasta=0
            for record in SeqIO.parse(os.path.join('temp_saves', filename), "fasta"):
                all_fasta+=1
                if not prot_check(str(record.seq)):
                    #total_fasta+=1
                    return render_template('error.html',error_h="Invalid sequence" ,error_msg=record.id + ' is not a valid protein sequence')
            if all_fasta==0:
                return render_template('error.html',error_h="Not a fasta file" ,error_msg=file.filename + ' is not a fasta file')
            if all_fasta>app.config['FASTA_SIZE_LIMIT']:
                return render_template('error.html',error_h="Too many sequences" ,error_msg="{} has {:d} sequences while the limit is {:d}".format(file.filename,all_fasta,app.config['FASTA_SIZE_LIMIT']))
            os.rename(os.path.join('temp_saves', filename),os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('bar',filename=filename))

#    print( fix_url_for('upload_file'))
    return render_template('main.html')

@app.route('/about')
def about():
    return render_template('about.html', title='about')

@app.route('/test')
def test():
        return render_template('test.html', title='test')

@app.route('/saves/<filename>')
def show_file(filename):
    if not os.path.exists(os.path.join('saves', filename)):
        return render_template('error.html',error_h="File not found" ,error_msg="There is no file named " + filename +
        " in our server. Old files are deleted periodically from our server. Please upload again.")
    table_code_raw=pickle.load(open('saves/' + filename,"rb"))
    return render_template('index.html', table_code= table_code_raw, csv_table=os.path.splitext(ntpath.basename(filename))[0] + '.csv', filename_base=ntpath.basename(filename))

@app.route('/tmp/<filename>')
def wait_page(filename):
    if os.path.exists(os.path.join('saves',filename)):
        return redirect(url_for('show_file',filename=filename))
    elif not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        return render_template('error.html',error_h="File not found" ,error_msg="There is no file named " + filename +
                " in our server. Old files are deleted periodically from our server. Please upload again.")
    else:
        return render_template('wait.html', filename=filename )

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/downloads')
def downloads():
    return render_template('downloads.html')

@app.route('/download/<filename>')
def down_file(filename='none'):
    if (filename == "model.tar"):
        return send_file('deca_model/model.tar')
    elif (filename == 'PhANNs_test.fasta'):
        return send_file('deca_model/PhANNs_test.fasta')
    elif (filename == 'rawDB.tgz'):
        return send_file('deca_model/rawDB.tgz')
    elif (filename == 'curatedDB.tgz'):
        return send_file('deca_model/curatedDB.tgz')
    elif (filename == 'dereplicate40DB.tgz'):
        return send_file('deca_model/dereplicate40DB.tgz')
    elif (filename == 'expandedDB.tgz'):
        return send_file('deca_model/expandedDB.tgz')
    else:
        return redirect(url_for('upload_file'))

@app.route('/csv_saves/<filename>')
def return_csv(filename):
	try:
		return send_file('csv_saves/' + filename)
	except Exception as e:
		return str(e)

@app.route('/interpret')
def interpret():
    return render_template('interpret.html', title='how to' )        

@app.route('/change')
def change():
    return render_template('change.html', title='Changes' )


if __name__ == "__main__":
    #app.run(debug=True, host="0.0.0.0", port=8080)
    app.run(host="0.0.0.0", port=8080,threaded=False)
    #socketio.run(app,host="0.0.0.0", port=8080,ssl_context='adhoc')
    #socketio.run(app,host="0.0.0.0", port=8080,threaded=False)
    #socketio.run(app, debug=True)
