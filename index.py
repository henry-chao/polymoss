from flask import Flask, render_template, url_for, request, redirect
import configparser

app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')

config = configparser.ConfigParser()
config.read('config.ini')

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

  return render_template('selection.jade')
