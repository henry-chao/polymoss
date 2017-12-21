from flask import Flask, render_template, url_for, request, redirect, session, jsonify
import requests
import configparser
import os
import sys
import errno
from datetime import datetime
import pycurl
import mosspy

app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')

config = configparser.ConfigParser()
config.read('config.ini')
app.secret_key = config['App']['key']

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
  token_req = {'grant_type': 'authorization_code',
               'client_id': config['Canvas']['client_id'],
               'client_secret': config['Canvas']['client_secret'],
               'redirect_uri': config['Canvas']['redirect_uri'],
               'code': request.args.get('code')
  }

  response = requests.post("https://{}/login/oauth2/token".format(config['Canvas']['canvas_instance']), json=token_req)
  access_token = response.json()['access_token']
  session['token'] = access_token
  return redirect(url_for('selection'))

@app.route("/selection")
def selection():
  return render_template('selection.jade',
    selectionjs = True
  )

@app.route("/getCourses")
def getCourses():
  URL = "https://{}/api/v1/courses?page=2".format(config['Canvas']['canvas_instance'])
  course_list = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
  return jsonify(course_list.json())

@app.route("/getAssignments")
def getAssignments():
  URL = "https://{}/api/v1/courses/{}/assignments".format(
    config['Canvas']['canvas_instance'],
    request.args.get('id'))
  assignments_list = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
  return jsonify(assignments_list.json())

@app.route("/getSubmissions")
def getSubmissions():
  URL = "https://{}/api/v1/courses/{}/assignments/{}/submissions".format(
    config['Canvas']['canvas_instance'],
    request.args.get('course_id'),
    request.args.get('assignment_id'))
  submissions_list = requests.get(URL, headers={'Authorization':'Bearer {}'.format(session['token'])})
  return jsonify(submissions_list.json())

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

  # Files are all downloaded, now submit to moss
  m = mosspy.Moss(request.args.get('moss_id'),"python")
  m.setDirectoryMode(1)
  m.addFilesByWildcard("{}/*/*".format(submission_dir))
  moss_report_url = m.send()

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

