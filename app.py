from flask import Flask, g, render_template, flash, redirect, url_for, session, request, logging, abort, send_from_directory
import sqlite3
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename
import os
import GenerateCPCMap
import SpatialAnalysis
import pandas
from dateutil.parser import parse
import datetime as dt
import json

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

#Set subdomain...
#If running locally (or index is the domain) set to blank, i.e. subd=""
#If index is a subdomain, set as appropriate *including* leading slash, e.g. subd="/living-lab"
subd=""

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

#Assertion error handling (flash error message, stay on uploads page)
@app.errorhandler(AssertionError)
def handle_errors(err):
    flash('Error: '+str(err), 'danger')
    return redirect(subd+'/uploads')

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
@app.route('/')
def index():
    colorProfile = 'gr'
    latest = query_db('SELECT * FROM CPCFiles ORDER BY start_date DESC', one=True)

    if latest is not None:
        try:
            settings = MapSettings(colorProfile)
            mapClass = MapData(latest['id'])
            settings.addData(mapClass)
            settings.getMeanLatLng()
        except Exception as e:
            flash('Error generating map: ' + str(e), 'danger')
            return redirect(subd + '/error')
        return render_template('home.html', subd=subd, settings=json.dumps(settings.toJSON(), cls=ComplexEncoder))
    else:
        return render_template('home.html', subd=subd, settings=False)

#average
@app.route('/average')
def average():
    colorProfile = 'gr'
    latest = query_db('SELECT * FROM CPCFiles ORDER BY start_date DESC', one=True)

    if latest is not None:
        try:
            settings = MapSettings(colorProfile)
            results = query_db('SELECT * FROM CPCFiles')
            for result in results:
                settings.addData(MapData(result['id']))
            settings.getMeanLatLng()
            grid = Grid(settings.data)
        except Exception as e:
            flash('Error generating map: ' + str(e), 'danger')
            return redirect(subd + '/error')

        return render_template('average.html', subd=subd
                                , settings=json.dumps(settings.toJSON(), cls=ComplexEncoder)
                                , grid=json.dumps(grid.toJSON(), cls=ComplexEncoder)
                               )
    else:
        return render_template('average.html', subd=subd, settings=False)


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
@app.route('/register-a-new-user', methods=['GET', 'POST'])
def register():
    #Redirect if already logged in
    if 'logged_in' in session:
        flash('Log out first to register a new user', 'danger')
        return redirect(subd+'/')
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
            return redirect(subd+'/register-a-new-user')

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

        return redirect(subd+'/login')
    return render_template('register.html', form=form, subd=subd)


#User login
@app.route('/login', methods=['GET','POST'])
def login():
    #Redirect if already logged in
    if 'logged_in' in session:
        flash('You are already logged in', 'success')
        return redirect(subd+'/')
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
                return redirect(subd+'/')
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error, subd=subd)
        else:
            error = 'Username not found'
            return render_template('login.html', error=error, subd=subd)

    return render_template('login.html', subd=subd)


#Check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorised, please login', 'danger')
            return redirect(subd+'/login')
    return wrap


#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(subd+'/login')


#Uploads
@app.route('/uploads', methods=["GET","POST"])
def uploads():
    #If user tries to upload a file
    if request.method == 'POST':
        #No file part:
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(subd+'/uploads')
        #Get file info
        file = request.files['file']
        #No selected file
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(subd+'/uploads')
        #Else upload file (unless bad extension)
        if file and allowed_file(file.filename):
            try:
                CPCtext=file.read().decode("iso8859_15")
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
            CPCFile = open(CPC_DIR+'/CPC_'+str(lastID)+'.csv','w', encoding='iso8859_15')
            CPCFile.write(CPCtext)
            CPCFile.close()
            #save GPS dataframe
            GPSData.to_pickle(GPS_DIR+'/GPS_'+str(lastID)+'.pkl')
            #return
            flash('File uploaded', 'success')
            return redirect(subd+'/uploads')
        else:
            flash('Only .csv files allowed', 'danger')
            return redirect(subd+'/uploads')
    #If user just navigates to page
    AllCPCFiles = query_db('SELECT * FROM CPCFiles')
    if AllCPCFiles is not None:
        AllCPCFiles = reversed(AllCPCFiles)
        return render_template('uploads.html', AllCPCFiles=AllCPCFiles, LoggedIn=('logged_in' in session),subd=subd)
    else:
        return render_template('uploads.html',LoggedIn=('logged_in' in session),subd=subd)


#Maps
@app.route('/maps/<string:id>')
def maps(id):
    if not os.path.exists(GPS_DIR+'/GPS_'+id+'.pkl'):
        abort(404)

    type = request.args.get('type') if request.args.get('type') else 'single'
    colorProfile = request.args.get('color') if request.args.get('color') else 'gr'

    settings = MapSettings(colorProfile)
    mapClass = MapData(id)

    if type == "multi":
        startYMD = mapClass.parseYMD()
        results = query_db('SELECT * FROM CPCFiles WHERE start_date LIKE ?', (str(startYMD)+'%',))

        for result in results:
            settings.addData(MapData(result['id']))
    elif type == 'single':
        settings.addData(mapClass)
    else:
        abort(404)

    settings.getMeanLatLng()

    return render_template('maps/index.html', subd=subd, settings=json.dumps(settings.toJSON(), cls=ComplexEncoder))


#Delete CPC file
@app.route('/delete_CPCFile/<string:id>', methods=['POST'])
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

    flash('CPC file deleted', 'success')
    return redirect(subd+'/uploads')


#Download CPC file
@app.route('/download/<string:id>', methods=['POST'])
def download(id):
    filename = query_db('SELECT * FROM CPCFiles WHERE id = ?',(id,),one=True)['filename']
    if os.path.exists(CPC_DIR+'/CPC_'+id+'.csv'):
        return send_from_directory(CPC_DIR,'CPC_'+id+'.csv',as_attachment=True,attachment_filename=filename)
    else:
        abort(404)


class MapSettings:

    def __init__(self, colorProfile):
        self.colorbar = subd + '/static/colourbar_' + colorProfile + '.png'
        self.mapTitle = ""
        self.binLims = []
        self.colsHex = []
        self.midpoint = []
        self.data = {}

        self.setBinColor(colorProfile)

    def addData(self, mapData):
        self.data[mapData.id] = mapData
        if len(self.data) > 1:
            self.mapTitle = 'Concentration map for all walks on ' + str(mapData.parseYMD())
        else:
            self.mapTitle = 'Concentration map for walk commencing ' + mapData.startDate

    def setBinColor(self, colorProfile):
        self.binLims = GenerateCPCMap.CreateBins()
        self.colsHex = GenerateCPCMap.AssignColours(self.binLims, colorProfile)
        if not os.path.exists(self.colorbar):
            GenerateCPCMap.CreateColourBar(self.binLims, self.colsHex, colorProfile)

    def getMeanLatLng(self):
        meanLats = []
        meanLngs = []
        for key in self.data:
            meanLatLng = GenerateCPCMap.MeanLatLng(self.data[key].lats, self.data[key].lons)
            meanLats.append(meanLatLng[0])
            meanLngs.append(meanLatLng[1])
        self.midpoint = GenerateCPCMap.MeanLatLng(meanLats, meanLngs)

    def toJSON(self):
        return dict(
            colorbar=self.colorbar
            , mapTitle=self.mapTitle
            , binLims=self.binLims
            , colsHex=self.colsHex
            , midpoint=self.midpoint
            , data=self.data
        )


class MapData:

    def __init__(self, id):
        # if id not in query_db('SELECT * FROM CPCFiles', one=False)['id']:
        #     abort(404)

        self.id = id
        self.lats = []
        self.lons = []
        self.concs = []

        self.dbquery = query_db('SELECT * FROM CPCFiles WHERE id = ?',(id,),one=True)
        self.startDate = self.dbquery['start_date']
        self.getData()

    def parseYMD(self):
        parseDate = parse(self.startDate)
        return dt.date(parseDate.year, parseDate.month, parseDate.day)

    def getData(self):
        try:
            with open(CPC_DIR + '/CPC_' + str(self.id) + '.csv', 'r', encoding='iso8859_15') as CPCFile:
                CPCtext = CPCFile.read()
                CPCData, CPCdate, CPClen = GenerateCPCMap.ReadCPCFile(CPCtext)
            GPSData = pandas.read_pickle(GPS_DIR + '/GPS_' + str(self.id) + '.pkl')
            MergeData = GenerateCPCMap.NearestNghbr(CPCData, GPSData)
            self.lats = MergeData['lat']
            self.lons = MergeData['lon']
            self.concs = MergeData['conc']
        except Exception as e:
            flash('Error generating map: ' + str(e), 'danger')
            return redirect(subd + '/error')

    def toJSON(self):
        return dict(
            id=self.id
            , lats=self.lats.tolist()
            , lons=self.lons.tolist()
            , concs=self.concs.tolist()
            , startDate=self.startDate
        )

class Grid:

    def __init__(self, data):
        self.cells = []

        shpHexagons = SpatialAnalysis.ReadGeoJSON('static/hex.geojson')
        for shpHexagon in shpHexagons:
            hexagon = Hexagon(shpHexagon)
            self.cells.append(hexagon)

        for dataset in data:
            self.cells = SpatialAnalysis.SpatialJoin(data[dataset], self.cells)

        for cell in self.cells:
            cell.average()


    def toJSON(self):
        return dict(
            cells=self.cells
        )

class Hexagon:

    def __init__(self, hexagon):
        self.lats = []
        self.lons = []
        self.concs = []
        self.hexagon = hexagon
        self.centroid = []
        self.concMedian = 0
        for lat in hexagon.boundary.xy[0]:
            self.lats.append(lat)
        for lons in hexagon.boundary.xy[1]:
            self.lons.append(lons)
        self.centroid = [hexagon.centroid.x, hexagon.centroid.y]

    def average(self):
        if self.concs:
            self.concMedian = GenerateCPCMap.Median(self.concs)

    def toJSON(self):
        return dict(
            lats=self.lats
            ,lons=self.lons
            ,conc=self.concMedian
            ,centroid=self.centroid
        )


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'toJSON'):
            return obj.toJSON()
        else:
            return json.JSONEncoder.default(self, obj)


#Error
@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run()
