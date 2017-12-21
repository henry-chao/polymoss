from flask import Flask, render_template, url_for, request, redirect
app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')

@app.route("/")
def index():
  return render_template('index.jade',
    title = "PolyMOSS"
  )

