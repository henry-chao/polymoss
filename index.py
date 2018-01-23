from flask import Flask, render_template, url_for, request, redirect, session, g
import requests
import configparser
import os
import sys
import pycurl
import mosspy
import mossum
import shutil
import json
import zipfile
import re
import logging
from logging.handlers import RotatingFileHandler
from time import strftime
import sqlite3
import validators
from werkzeug.utils import secure_filename

import pdb

app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')

config = configparser.ConfigParser()
config.read('config.ini')
app.secret_key = config['App']['key']

database = config['Database']['path']

ts = strftime(config['Logging']['time_format'])
logfile_location = config['Logging']['log_file_location']

upload_directory = config['Uploads']['path']
upload_allowed_extensions = config['Uploads']['extensions']

handler = RotatingFileHandler(logfile_location, maxBytes=10000, backupCount=3)
logger = logging.getLogger('__name__')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

@app.route("/")
def index():
  try:
    link = ""
    if 'token' in session:
      token_req = {'grant_type': 'refresh_token',
                   'client_id': config['Canvas']['client_id'],
                   'client_secret': config['Canvas']['client_secret'],
                   'refresh_token': session['refresh_token']
      }

      response = requests.post("https://{}/login/oauth2/token".format(config['Canvas']['canvas_instance']), json=token_req)
      session['token'] = response.json()['access_token']

      link = url_for('selection')
    else:
      link = "https://{}/login/oauth2/auth?client_id={}&purpose=polymoss&response_type=code&redirect_uri={}".format(
        config['Canvas']['canvas_instance'],
        config['Canvas']['client_id'],
        config['Canvas']['redirect_uri']
      )
    return render_template('index.jade',
      title = "PolyMOSS",
      link = link
    )
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

@app.route("/logout")
def logout():
  try:
    URL = "https://{}/login/oauth2/token".format(config['Canvas']['canvas_instance'])
    del_token_res = requests.delete(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
    session.pop('token', None)
    session.pop('refresh_token', None)
    return redirect(url_for('index'))
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

@app.route("/oauth")
def ouath():
  try:
    if request.args.get('error') is not None:
      return render_template('canvas_error.jade')
    else:
      token_req = {'grant_type': 'authorization_code',
                   'client_id': config['Canvas']['client_id'],
                   'client_secret': config['Canvas']['client_secret'],
                   'redirect_uri': config['Canvas']['redirect_uri'],
                   'code': request.args.get('code')
      }
    
      response = requests.post("https://{}/login/oauth2/token".format(config['Canvas']['canvas_instance']), json=token_req)
      response_json = response.json()
      username = response_json['user']['name']
      access_token = response_json['access_token']
      refresh_token = response_json['refresh_token']

      session['name'] = username
      session['token'] = access_token
      session['refresh_token'] = refresh_token

      logger.info('{} Canvas auth token received for user: {}'.format(ts, session['name']))
      return redirect(url_for('selection'))
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

@app.route("/selection")
def selection():
  try:
    # Query database for user information
    user = query_db('select * from Users where USER_NAME = ?', [session['name']], one=True)
    logger.info('{} Found user {}'.format(ts, user))
 
    return render_template('selection.jade',
      selectionjs = True,
      user_name = user[1],
      moss_id = user[0],
      moss_languages = sorted(mosspy.Moss(0).getLanguages()),
      extensions = upload_allowed_extensions
    )
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

@app.route("/getCourses", methods=['POST','GET'])
def getCourses():
  try:
    URL = "https://{}/api/v1/courses?per_page=12".format(config['Canvas']['canvas_instance'])
  
    # If part of multiple courses, pagination will occur. This will redirect to another page of courses for the request
    json_data = json.loads(request.get_json())

    if not(json_data['url'] == "undefined"):
      if validators.url(json_data['url']):
        URL = json_data['url']
  
    response = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
    course_list = response.json()

    prev_link = None
    next_link = None

    if 'Link' not in response.headers:
      return render_template('timeout.jade')

    links_list = response.headers['Link'].split(",")
    for link in links_list:
      if "prev" in link:
        sublink = link.split(";")
        prev_link = sublink[0][1:-1]
      elif "next" in link:
        sublink = link.split(";")
        next_link = sublink[0][1:-1]
    return render_template('courses.jade',
      response_obj = {'prev_link':prev_link,'next_link':next_link,'course_list':course_list}
    )
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

@app.route("/getAssignments")
def getAssignments():
  try:
    course_id = request.args.get('id', type=int)
    URL = "https://{}/api/v1/courses/{}/assignments".format(
      config['Canvas']['canvas_instance'],
      course_id)
    logger.info('{} {} Pulling all assignments for course ID: {}'.format(ts, session['name'], course_id))
    assignments_list = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])}).json()
    for assignment in assignments_list:
      if assignment['description'] is not None:
        assignment['description'] = re.compile(r'<[^>]+>').sub('',assignment['description'])
    return render_template('assignments.jade',
      assignments = assignments_list
    )
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

@app.route("/uploadBaseFile", methods=['POST'])
def uploadBaseFile():
  try:
    if 'base_file' in request.files:
      return ','.join(get_base_files(request.files['base_file'], upload_directory))
    else:
      return ""
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

@app.route("/submitToMoss", methods=['POST'])
def submitToMoss():
  try:
    request_json = request.get_json()

    # Files are all downloaded, now submit to moss
    moss_query = query_db('select MOSS_ID from Users where USER_NAME = ?', [session['name']], one=True)
    moss_id = moss_query[0]

    # Validate code type input
    moss_code_type = request_json['code_type']
    if moss_code_type not in mosspy.Moss(0).getLanguages():
      moss_code_type = 'python'

    # Initialize moss connection
    m = mosspy.Moss(moss_id, moss_code_type)
    #m.setDirectoryMode(1)

    for key in request_json['submissions']:
      submission = request_json['submissions'][key]
      course_id = submission['course_id']
      assignment_id = submission['assignment_id']
      URL = "https://{}/api/v1/courses/{}/assignments/{}/submissions".format(
        config['Canvas']['canvas_instance'],
        course_id,
        assignment_id)

      submissions_list = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
      (submissions_to_send_to_moss, submission_dir) = download_submissions_for_moss(submissions_list.json(), course_id, assignment_id)
      
      for moss_file in submissions_to_send_to_moss:
        logger.info('{} {} Submitting to moss: {}'.format(ts, session['name'], moss_file))
        m.addFile(os.path.join(submission_dir, moss_file),moss_file)

    if 'base_files' in request_json:
      list_of_base_files = request_json['base_files'][0].split(",")
      for base_file in list_of_base_files:
        m.addBaseFile(base_file)

    # Submit moss report and delete staging files
    moss_report_url = m.send()
    shutil.rmtree(submission_dir)
  
    query_db('INSERT INTO Submissions (MOSS_ID, SUBMISSION_TIME, COURSE_ID, ASSIGNMENT_ID, URL) VALUES(?, ?, ?, ?, ?)',
      [int(moss_id),strftime('%Y-%m-%d %H:%M:%S.000'),int(course_id),int(assignment_id),moss_report_url], insert=True)
  
    return moss_report_url
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

def download_submissions_for_moss(submissions_list, course_id, assignment_id):
  try:
    ## Begin building out directory locations to download submissions
    # First determine user's home directory
    user_home = os.path.expanduser("~")
    
    # Define directories
    course_dir = os.path.join(user_home, "moss_submissions", str(course_id))
    assignment_dir = os.path.join(course_dir, str(assignment_id))
    report_time = strftime('%Y%m%d%H%M%S')
    submission_dir = os.path.join(assignment_dir, report_time)

    # Make directories
    make_dir(submission_dir)
    
    submissions_to_send_to_moss = []
    for submission in submissions_list:
      if submission['workflow_state'] == 'submitted':
        student_name = get_student_name(submission['user_id'])
        student_submission_dir = os.path.join(submission_dir, student_name)
        make_dir(student_submission_dir)
        for attachment in submission['attachments']:
          filename = attachment['filename'].replace(" ","_")
          full_file_path = os.path.join(student_submission_dir, filename)
          save_file(attachment['url'], full_file_path)
          if (attachment['content-type'] == 'application/x-zip-compressed'):
            file_list = extract_zip_and_get_list(full_file_path, student_submission_dir)
            for each_file in file_list:
              submissions_to_send_to_moss.append(os.path.join(student_name, each_file))
          else:
            submissions_to_send_to_moss.append(os.path.join(student_name, filename))
  
    return (submissions_to_send_to_moss, submission_dir)
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

def get_student_name(student_id):
  try:
    URL = "https://{}/api/v1/users/{}/profile".format(
      config['Canvas']['canvas_instance'],
      student_id
    )
    student_json = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
    return student_json.json()['name'].replace(" ","_")
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

def make_dir(location):
  if not os.path.exists(location):
    try:
      os.makedirs(location)
    except:
      logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
      raise

def save_file(URL, file_location):
  try:
    api = pycurl.Curl()
    api.setopt(pycurl.URL, URL)
    api.setopt(pycurl.FOLLOWLOCATION, True)
    with open(file_location, 'wb') as f:
      api.setopt(pycurl.WRITEFUNCTION, f.write)
      api.perform()
    api.close()
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = g._database = sqlite3.connect(database)
  return db

@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()

def query_db(query, args=(), one=False, insert=False):
  try:
    logger.info('{} Executing query:\n{}\nWith arguments:\n{}'.format(ts, query, args))
    cur = get_db().execute(query, args)
    if insert:
      get_db().commit()
      cur.close()
    else:
      resultset = cur.fetchall()
      cur.close()
      return (resultset[0] if resultset else None) if one else resultset
  except:
    logger.error('{} An error has occured:\n{}'.format(ts, sys.exc_info()[0]))
    raise

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.',1)[1].lower() in upload_allowed_extensions

def extract_zip_and_get_list(zip_file, location):
  list_of_zip_extracts = []
  with zipfile.ZipFile(zip_file,"r") as zip_ref:
    zip_ref.extractall(location)
  os.remove(zip_file)
  for dirpath, subdirname, files_in_path in os.walk(location):
    original_path = dirpath
    new_path = dirpath.replace(" ","_")
    os.rename(original_path, new_path)
    if len(files_in_path) > 0:
      for the_file in files_in_path:
        original_name = the_file
        new_name = the_file.replace(" ","_")
        subpath = new_path[len(location)+1:]
        os.rename(os.path.join(new_path,original_name),
                  os.path.join(new_path,new_name))
        list_of_zip_extracts.append(os.path.join(subpath,new_name))
  return list_of_zip_extracts

def get_base_files(base_file, base_file_dir):
  if base_file.filename != '' and allowed_file(base_file.filename):
    base_filename = secure_filename(base_file.filename)
    make_dir(base_file_dir)
    base_file_location = os.path.join(base_file_dir, base_filename)
    base_file.save(base_file_location)
    base_files_to_send_to_moss = []
    if zipfile.is_zipfile(base_file_location):
      file_list = extract_zip_and_get_list(base_file_location, base_file_dir)
      for each_file in file_list:
        base_files_to_send_to_moss.append(os.path.join(base_file_dir, each_file))
    else:
      base_files_to_send_to_moss.append(base_file_location)
    return base_files_to_send_to_moss

