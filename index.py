from flask import Flask, render_template, url_for, request, redirect, session, jsonify
import requests
import configparser

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
