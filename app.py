from flask import Flask, g, render_template, flash, redirect, url_for, session, request, logging, abort, send_from_directory
import sqlite3
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename
import os
import GenerateCPCMap
import pandas
from dateutil.parser import parse
import datetime as dt

app = Flask(__name__)
assert os.path.exists('AppSecretKey.txt'), "Unable to locate app secret key"
with open('AppSecretKey.txt','r') as f:
    key=f.read()
app.secret_key=key
CPC_DIR = 'CPCFiles'
GPS_DIR = 'GPSFiles'
MAP_DIR = 'templates/maps'
DEL_DIR = 'deleted'
CPC_DEL_DIR = DEL_DIR+'/'+CPC_DIR
GPS_DEL_DIR = DEL_DIR+'/'+GPS_DIR
ALLOWED_EXTENSIONS = set(['csv'])
DATABASE = 'LivingLabDataApp.db'
assert os.path.exists(DATABASE), "Unable to locate database"
assert os.path.exists('StravaTokens.txt'), "Unable to locate Strava tokens"

#Create directories if needed:
if not os.path.isdir(CPC_DIR):
    os.mkdir(CPC_DIR)
if not os.path.isdir(MAP_DIR):
    os.mkdir(MAP_DIR)
if not os.path.isdir(GPS_DIR):
    os.mkdir(GPS_DIR)
if not os.path.isdir(DEL_DIR):
    os.mkdir(DEL_DIR)
if not os.path.isdir(CPC_DEL_DIR):
    os.mkdir(CPC_DEL_DIR)
if not os.path.isdir(GPS_DEL_DIR):
    os.mkdir(GPS_DEL_DIR)

#Error handling (flash error message, stay on current page)
@app.errorhandler(AssertionError)
def handle_errors(err):
    flash('Error: '+str(err), 'danger')
    return redirect(url_for(str(request.url_rule)[1:]))

#Allowed extensions for file uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Connect to DB
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

#Close DB if app stops
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

#Query DB
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else (rv if rv else None)

#Index
@app.route('/living-lab')
def index():
    if os.path.exists(MAP_DIR+'/latest.html'):
        return render_template('home.html',latest=True)
    else:
        return render_template('home.html',latest=False)

#Register form class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username',[validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do no match')
    ])
    confirm = PasswordField('Confirm Password')

#User register
@app.route('/living-lab/register-a-new-user', methods=['GET', 'POST'])
def register():
    #Redirect if already logged in
    if 'logged_in' in session:
        flash('Log out first to register a new user', 'danger')
        return redirect(url_for('index'))
    #Otherwise...
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        #Check username is unique
        result = query_db('SELECT * FROM users WHERE username = ?', [username])
        if result is not None:
            flash('Username already exists', 'danger')
            return redirect(url_for('register-a-new-user'))

        #Create cursor
        db = get_db()
        cur = db.cursor()
        #Execute query:
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(?, ?, ?, ?)", (name, email, username, password))
        #Commit to DB
        db.commit()
        #Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)

#User login
@app.route('/living-lab/login', methods=['GET','POST'])
def login():
    #Redirect if already logged in
    if 'logged_in' in session:
        flash('You are already logged in', 'success')
        return redirect(url_for('index'))
    if request.method == 'POST':
        #Get form fields
        username = request.form['username']
        password_candidate = request.form['password']
        result = query_db('SELECT * FROM users WHERE username = ?', [username])
        if result is not None:
            data = query_db('SELECT * FROM users WHERE username = ?', [username], one=True)
            password = data['password']
            #Compare passwords
            if sha256_crypt.verify(password_candidate, password):
                #Passed
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in', 'success')
                return redirect(url_for('index'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

#Check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorised, please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/living-lab/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

#Uploads
@app.route('/living-lab/uploads', methods=["GET","POST"])
def uploads():
    #If user tries to upload a file
    if request.method == 'POST':
        #No file part:
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('uploads'))
        #Get file info
        file = request.files['file']
        #No selected file
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('uploads'))
        #Else upload file (unless bad extension)
        if file and allowed_file(file.filename):
            try:
                CPCtext=file.read().decode("utf-8")
                CPCData,CPCdate,CPClen = GenerateCPCMap.ReadCPCFile(CPCtext)
                GPSData = GenerateCPCMap.FetchGPSData('StravaTokens.txt',CPCdate,CPClen)
                MergeData = GenerateCPCMap.NearestNghbr(CPCData,GPSData)
            except Exception:
                raise
            #Add entry to CPCFiles DB
            #Create cursor
            db = get_db()
            cur = db.cursor()
            #Execute query:
            cur.execute("INSERT INTO CPCFiles(filename, username, start_date) VALUES(?, ?, ?)", (secure_filename(file.filename), session['username'], CPCdate))
            #Commit to DB
            db.commit()
            #Close connection
            cur.close()
            #Save CPC file, renaming based on DB ID
            lastID = query_db('SELECT * FROM CPCFiles ORDER BY id DESC LIMIT 1',one=True)['id']
            CPCFile = open(CPC_DIR+'/CPC_'+str(lastID)+'.csv','w', encoding='utf-8')
            CPCFile.write(CPCtext)
            CPCFile.close()
            #save GPS dataframe
            GPSData.to_pickle(GPS_DIR+'/GPS_'+str(lastID)+'.pkl')
            #Save map as latest if applicable
            latestDate = parse(query_db('SELECT * FROM CPCFiles ORDER BY start_date DESC LIMIT 1',one=True)['start_date'])
            if CPCdate >= latestDate:
                mapFileIn = GenerateCPCMap.CreateMap(MergeData,str(lastID),MAP_DIR)
                mapTitle = 'Concentration map for walk commencing '+str(CPCdate)
                mapFileOut = GenerateCPCMap.BuildMap(MAP_DIR,str(lastID),mapFileIn,mapTitle)
                os.remove(MAP_DIR+'/'+mapFileIn)
                if os.path.exists(MAP_DIR+'/latest.html'):
                    os.remove(MAP_DIR+'/latest.html')
                os.rename(MAP_DIR+'/'+mapFileOut,MAP_DIR+'/latest.html')
            #return
            flash('File uploaded', 'success')
            return redirect(url_for('uploads'))
        else:
            flash('Only .csv files allowed', 'danger')
            return redirect(url_for('uploads'))
    #If user just navigates to page
    AllCPCFiles = query_db('SELECT * FROM CPCFiles')
    if AllCPCFiles is not None:
        AllCPCFiles = reversed(AllCPCFiles)
        return render_template('uploads.html', AllCPCFiles=AllCPCFiles, LoggedIn=('logged_in' in session))
    else:
        return render_template('uploads.html',LoggedIn=('logged_in' in session))

#Maps
@app.route('/living-lab/maps/<string:id>/<string:mapType>')
def maps(id,mapType):
    if not os.path.exists(GPS_DIR+'/GPS_'+id+'.pkl'):
        abort(404)
    start_date = query_db('SELECT * FROM CPCFiles WHERE id = ?',(id,),one=True)['start_date']
    parseDate = parse(start_date)
    startYMD = dt.date(parseDate.year,parseDate.month,parseDate.day)
    AllCPCFiles = query_db('SELECT * FROM CPCFiles')
    numCPCFiles = len(AllCPCFiles)
    allDates = [parse(x['start_date']) for x in AllCPCFiles]
    YMD = []
    for date in allDates:
        YMD.append(dt.date(date.year,date.month,date.day))
    if mapType == "multi" and YMD.count(startYMD) > 1:
        ids=[]
        for i,date in enumerate(YMD):
            if(date==startYMD):
                ids.append(AllCPCFiles[i]['id'])
        MergeDataAll=[]
        try:
            for idx in ids:
                with open(CPC_DIR+'/CPC_'+str(idx)+'.csv','r', encoding='utf-8') as CPCFile:
                    CPCtext = CPCFile.read()
                    CPCData,CPCdate,CPClen = GenerateCPCMap.ReadCPCFile(CPCtext)
                GPSData = pandas.read_pickle(GPS_DIR+'/GPS_'+str(idx)+'.pkl')
                MergeData = GenerateCPCMap.NearestNghbr(CPCData,GPSData)
                MergeDataAll.append(MergeData)
            MergeDataConcat = pandas.concat(MergeDataAll)
            mapFileIn = GenerateCPCMap.CreateMap(MergeDataConcat,id,MAP_DIR,addMarkers=False)
        except Exception as e:
            flash('Error generating map: '+str(e), 'danger')
            return redirect(url_for('error'))
        mapTitle = 'Concentration map for all walks on '+str(startYMD)
    elif mapType == "single" or (mapType == "multi" and YMD.count(startYMD) == 1):
        try:
            with open(CPC_DIR+'/CPC_'+id+'.csv','r', encoding='utf-8') as CPCFile:
                CPCtext = CPCFile.read()
                CPCData,CPCdate,CPClen = GenerateCPCMap.ReadCPCFile(CPCtext)
            GPSData = pandas.read_pickle(GPS_DIR+'/GPS_'+id+'.pkl')
            MergeData = GenerateCPCMap.NearestNghbr(CPCData,GPSData)
            mapFileIn = GenerateCPCMap.CreateMap(MergeData,id,MAP_DIR)
        except Exception as e:
            flash('Error generating map: '+str(e), 'danger')
            return redirect(url_for('error'))
        mapTitle = 'Concentration map for walk commencing '+start_date
    else:
        abort(404)
    mapFileOut = GenerateCPCMap.BuildMap(MAP_DIR,id,mapFileIn,mapTitle)
    with open(MAP_DIR+'/'+mapFileOut) as f:
        mapText = f.read()
    os.remove(MAP_DIR+'/'+mapFileIn)
    os.remove(MAP_DIR+'/'+mapFileOut)
    return mapText


#Latest map
@app.route('/living-lab/latest')
def latest():
    return render_template('maps/latest.html')

#Delete CPC file
@app.route('/living-lab/delete_CPCFile/<string:id>', methods=['POST'])
@is_logged_in
def delete_CPCFile(id):
    #Get start date of entry to be deleted
    delDate = parse(query_db('SELECT * FROM CPCFiles WHERE id = ?',(id,),one=True)['start_date'])

    #Create cursor
    db = get_db()
    cur = db.cursor()
    #Execute query:
    cur.execute("DELETE FROM CPCFiles WHERE id = ?", [id])
    #Commit to DB
    db.commit()
    #Close connection
    cur.close()

    #Move associated files to a 'deleted' directory
    if os.path.exists(CPC_DIR+'/CPC_'+id+'.csv'):
        os.rename(CPC_DIR+'/CPC_'+id+'.csv',CPC_DEL_DIR+'/CPC_'+id+'.csv')
    if os.path.exists(GPS_DIR+'/GPS_'+id+'.pkl'):
        os.rename(GPS_DIR+'/GPS_'+id+'.pkl',GPS_DEL_DIR+'/GPS_'+id+'.pkl')

    #Delete and update latest map if this was it:
    latestByDate = query_db('SELECT * FROM CPCFiles ORDER BY start_date DESC LIMIT 1',one=True)
    if latestByDate is not None:
        latestDate = parse(latestByDate['start_date'])
        latestID = latestByDate['id']
        if delDate > latestDate:
            if os.path.exists(MAP_DIR+'/latest.html'):
                os.remove(MAP_DIR+'/latest.html')
            try:
                with open(CPC_DIR+'/CPC_'+str(latestID)+'.csv','r', encoding='utf-8') as CPCFile:
                    CPCtext = CPCFile.read()
                    CPCData,CPCdate,CPClen = GenerateCPCMap.ReadCPCFile(CPCtext)
                GPSData = pandas.read_pickle(GPS_DIR+'/GPS_'+str(latestID)+'.pkl')
                MergeData = GenerateCPCMap.NearestNghbr(CPCData,GPSData)
                mapFileIn = GenerateCPCMap.CreateMap(MergeData,str(latestID),MAP_DIR)
                mapTitle = 'Concentration map for walk commencing '+str(CPCdate)
                mapFileOut = GenerateCPCMap.BuildMap(MAP_DIR,str(latestID),mapFileIn,mapTitle)
                os.remove(MAP_DIR+'/'+mapFileIn)
                os.rename(MAP_DIR+'/'+mapFileOut,MAP_DIR+'/latest.html')
            except:
                raise
    else:
        if os.path.exists(MAP_DIR+'/latest.html'):
            os.remove(MAP_DIR+'/latest.html')

    flash('CPC file deleted', 'success')
    return redirect(url_for('uploads'))

#Download CPC file
@app.route('/living-lab/download/<string:id>', methods=['POST'])
def download(id):
    filename = query_db('SELECT * FROM CPCFiles WHERE id = ?',(id,),one=True)['filename']
    if os.path.exists(CPC_DIR+'/CPC_'+id+'.csv'):
        return send_from_directory(CPC_DIR,'CPC_'+id+'.csv',as_attachment=True,attachment_filename=filename)
    else:
        abort(404)

#Error
@app.route('/living-lab/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run()
