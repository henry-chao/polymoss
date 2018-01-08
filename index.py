from flask import Flask, render_template, url_for, request, redirect, session, g
import requests
import configparser
import os
import sys
import errno
from datetime import datetime
import pycurl
import mosspy
import shutil
import json
import zipfile
import re
import logging
from logging.handlers import RotatingFileHandler
from time import strftime
import sqlite3

app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')

config = configparser.ConfigParser()
config.read('config.ini')
app.secret_key = config['App']['key']

database = config['Database']['path']

ts = strftime(config['Logging']['time_format'])
logfile_location = config['Logging']['log_file_location']

handler = RotatingFileHandler(logfile_location, maxBytes=10000, backupCount=3)
logger = logging.getLogger('__name__')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

@app.route("/")
def index():
  return render_template('index.jade',
    title = "PolyMOSS",
    canvas_instance = config['Canvas']['canvas_instance'],
    client_id = config['Canvas']['client_id'],
    redirect_uri = config['Canvas']['redirect_uri']
  )

@app.route("/oauth")
def ouath():
  if request.args.get('error') is not None:
    return render_template('canvas_error.jade')
  else:
    if 'token' in session:
      # Delete all existing tokens on Canvas, and request a new one
      URL = "https://{}/login/oauth2/token".format(config['Canvas']['canvas_instance'])
      del_token_res = requests.delete(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
  
    token_req = {'grant_type': 'authorization_code',
                 'client_id': config['Canvas']['client_id'],
                 'client_secret': config['Canvas']['client_secret'],
                 'redirect_uri': config['Canvas']['redirect_uri'],
                 'code': request.args.get('code')
    }
  
    response = requests.post("https://{}/login/oauth2/token".format(config['Canvas']['canvas_instance']), json=token_req)
    access_token = response.json()['access_token']
    session['name'] = response.json()['user']['name']
    logger.info('{} Canvas auth token received for user: {}'.format(ts, session['name']))
    session['token'] = access_token
    return redirect(url_for('selection'))

@app.route("/selection")
def selection():
  return render_template('selection.jade',
    selectionjs = True
  )

@app.route("/getCourses", methods=['POST','GET'])
def getCourses():
  URL = ""
  json_data = json.loads(request.get_json())
  if not(json_data['url'] == "undefined"):
    URL = json_data['url']
  else:
    URL = "https://{}/api/v1/courses?per_page=12".format(config['Canvas']['canvas_instance'])
  response = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
  links_list = response.headers['Link'].split(",")
  page_list = {}
  for link in links_list:
    if "prev" in link:
      sublink = link.split(";")
      page_list['prev'] = sublink[0][1:-1]
    elif "next" in link:
      sublink = link.split(";")
      page_list['next'] = sublink[0][1:-1]
  course_list = response.json()
  return render_template('courses.jade',
    response_obj = {'links':page_list,'course_list':course_list}
  )

@app.route("/getAssignments")
def getAssignments():
  URL = "https://{}/api/v1/courses/{}/assignments".format(
    config['Canvas']['canvas_instance'],
    request.args.get('id'))
  logger.info('{} {} Pulling all assignments for course ID: {}'.format(ts, session['name'], request.args.get('id')))
  assignments_list = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])}).json()
  for assignment in assignments_list:
    if assignment['description'] is not None:
      assignment['description'] = re.compile(r'<[^>]+>').sub('',assignment['description'])
  return render_template('assignments.jade',
    assignments = assignments_list
  )

@app.route("/getSubmissions")
def getSubmissions():
  URL = "https://{}/api/v1/courses/{}/assignments/{}/submissions".format(
    config['Canvas']['canvas_instance'],
    request.args.get('course_id'),
    request.args.get('assignment_id'))
  logger.info('{} {} Getting submission count for course {} assignment {}'.format(ts, session['name'], request.args.get('course_id'), request.args.get('assignment_id')))
  submissions_response = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])}).json()
  return render_template('submission.jade',
    submissions = submissions_response,
    course_id = request.args.get('course_id'),
    assignment_id = request.args.get('assignment_id'),
    moss_languages = mosspy.Moss(0).getLanguages()
  )

@app.route("/submitToMoss")
def submitToMoss():
  course_id = request.args.get('course_id')
  assignment_id = request.args.get('assignment_id')
  URL = "https://{}/api/v1/courses/{}/assignments/{}/submissions".format(
    config['Canvas']['canvas_instance'],
    course_id,
    assignment_id)
  submissions_list = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})

  ## Begin building out directory locations to download submissions
  # First determine user's home directory
  user_home = os.path.expanduser("~")

  # Create directories for course and assignments
  course_dir = "{}/moss_submissions/{}".format(user_home,course_id)
  make_dir(course_dir)

  assignment_dir = "{}/{}".format(course_dir,assignment_id)
  make_dir(assignment_dir)

  report_time = datetime.now().strftime('%Y%m%d%H%M%S')
  submission_dir = "{}/{}".format(assignment_dir,report_time)
  make_dir(submission_dir)

  submissions = submissions_list.json()

  submissions_to_send_to_moss = []
  for submission in submissions:
    student_id = submission['user_id']
    URL = "https://{}/api/v1/users/{}/profile".format(
      config['Canvas']['canvas_instance'],
      student_id
    )
    student_json = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
    student_name = student_json.json()['name']
    student_submission_dir = "{}/{}".format(submission_dir,student_name)
    make_dir(student_submission_dir)
    for attachment in submission['attachments']:
      full_file_path = '{}/{}-{}'.format(student_submission_dir,student_name,attachment['filename'])
      save_file(attachment['url'], full_file_path)
      if (attachment['content-type'] == 'application/x-zip-compressed'):
        with zipfile.ZipFile(full_file_path,"r") as zip_ref:
          zip_ref.extractall(student_submission_dir)
          for extracted_file in zip_ref.namelist():
            submissions_to_send_to_moss.append("{}/{}".format(student_submission_dir,extracted_file))
        os.remove(full_file_path)
      else:
        submissions_to_send_to_moss.append(full_file_path)

  # Files are all downloaded, now submit to moss
  m = mosspy.Moss(request.args.get('moss_id'), str(request.args.get('code_type')))
  #m.setDirectoryMode(1)
  for moss_file in submissions_to_send_to_moss:
    logger.info('{} {} Submitting to moss: {}'.format(ts, session['name'], moss_file))
    m.addFile(moss_file)
  moss_report_url = m.send()

  # Moss report returned, so delete files in staging area
  shutil.rmtree(submission_dir)

  return moss_report_url

def make_dir(location):
  if not os.path.exists(location):
    try:
      os.makedirs(location)
    except OSError as e:
      if e.errno != e.EEXIST:
        raise

def save_file(URL, file_location):
  api = pycurl.Curl()
  api.setopt(pycurl.URL, URL)
  api.setopt(pycurl.FOLLOWLOCATION, True)
  with open(file_location, 'wb') as f:
    api.setopt(pycurl.WRITEFUNCTION, f.write)
    api.perform()
  api.close()

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

