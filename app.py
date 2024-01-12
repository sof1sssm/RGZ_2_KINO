from flask import Flask,  render_template, request

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')


@app.route('/result', methods=['GET', 'POST'])
def result():
    x = request.form.get('x')
    y = request.form.get('y')
    z = request.form.get('z')
    result = 2*int(x) + 8*int(y) + 7*int(z) 
    return render_template('zadanie.html', result=result)
