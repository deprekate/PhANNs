import html
import time
import os
from flask import Flask, flash, request, redirect, url_for, render_template, Response
from werkzeug.utils import secure_filename
from flask import send_from_directory , Markup, send_file
import subprocess
import pickle
from redis import Redis
import rq
import ntpath
ROOT_FOLDER = os.path.dirname(os.path.realpath(__file__)) 
UPLOAD_FOLDER = ROOT_FOLDER + '/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'faa', 'fasta', 'gif', 'fa'])
import urllib

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config['APPLICATION_ROOT']='/adrian_net'
#app.config['APPLICATION_ROOT']='/phannies'
app.config['APPLICATION_ROOT']=''
PREFIX=app.config['APPLICATION_ROOT'] 

def fix_url_for(path, **kwargs):
    return PREFIX + url_for(path, **kwargs)
#    return url_for(path, **kwargs)

#make fix_url_for available in tamplates
@app.context_processor
def contex():
    return dict(fix_url_for = fix_url_for)

#add the sorable attribute to tables generated by pandas
@app.template_filter('sorttable')
def sorttable_filter(s):
    s= s.replace('table id=','table class="sortable" id=')
    return s


def return_html_table(filename):
    cmd = ["python" , "run_tri_model.py" , app.config['UPLOAD_FOLDER'] + '/' + filename]
    p = subprocess.Popen(cmd, stdout = subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE)
    out,err = p.communicate()
    print(err)
    return out


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#@app.route('/bar/<filename>')
@app.route('/uploads/<filename>')
def bar(filename):
#    if os.path.exists('saves/'+filename):
#        return redirect(fix_url_for('show_file',filename=filename))
#    else:
        print(filename)
        return render_template('loading.html',filename=filename)


@app.route('/progress/<filename>')
def progress(filename):
    #yield "data:0" + "\n\n"
    #yield "event:url" + "\n" + "data:'http://0.0.0.0:8080/upload'" + "\n\n"
    
    
    #yield "event: url\ndata: {\"url\":\"http://0.0.0.0:8080/upload\"}\n\n"
    queue = rq.Queue('microblog-tasks', connection=Redis.from_url('redis://'))
    job = queue.enqueue('run_tri_model_app.entrypoint','uploads/'+filename,job_timeout=3000000)
    
    def generate():
        data=1
        seq_total=1
        while data < 100:
            job.refresh()
            try:
                seq_total=job.meta['total']
            except:
                seq_total=1
            try:
                seq_current=job.meta['current']
            except:
                seq_current=0
            data=(seq_current/seq_total) * 100
            yield "event: update\ndata:" + str(data) + "\n\n"
            time.sleep(0.2)
            print(data)
        table_string=None
        model_is_running=None
        while model_is_running is None:
            try:
                job.refresh()
                model_is_running=job.meta['running']
            except:
                time.sleep(0.5)
            else:
                yield "event: running\ndata:" + str(model_is_running) + "\n\n"
        while not job.is_finished:
            time.sleep(1)
#        yield "event: url\ndata: {\"url\":\"http://0.0.0.0:8080/saves" + '/' + filename + "\"}\n\n"
        with app.app_context(), app.test_request_context():
            yield "event: url\ndata: {\"url\":\"" + url_for('show_file',filename=filename) +"\"}\n\n"
#        with app.app_context(), app.test_request_context():
#            print("data:" + fix_url_for('show_file',filename=filename)  + "\n\n")
    
    return Response(generate(), mimetype= 'text/event-stream')

@app.route('/test')
def test_template():
    return "mira un salmon"

@app.route('/', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
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
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print( fix_url_for('bar',filename=filename))
            return redirect(url_for('bar',filename=filename))
    print( fix_url_for('upload_file'))
    return render_template('main.html')

@app.route('/about')
def about():
    return render_template('about.html', title='about')

#@app.route('/uploads/<filename>')
def uploaded_file(filename):
    table_code_raw= Markup(return_html_table(filename).decode('utf8'))
    table=render_template('index.html', table_code= table_code_raw)
    pickle.dump(table_code_raw,open('saves/' + filename,"wb"))
    return table

@app.route('/saves/<filename>')
def show_file(filename):
    table_code_raw=pickle.load(open('saves/' + filename,"rb"))
    return render_template('index.html', table_code= table_code_raw, csv_table=os.path.splitext(ntpath.basename(filename))[0] + '.csv', filename_base=ntpath.basename(filename))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/tri_p.h5')
def model_file():
    return send_file('tri_p_model/tri_p.h5')


@app.route('/csv_saves/<filename>')
def return_csv(filename):
	try:
		return send_file('csv_saves/' + filename)
	except Exception as e:
		return str(e)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
    #app.run(host="0.0.0.0", port=8080)
