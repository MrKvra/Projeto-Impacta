from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy

# código que fiz para testar a configuração do flask alchemy com SQL server.

app = Flask (__name__, template_folder='templates')

connection_string = "mssql+pyodbc://DESKTOP-TFIS1IE\\SQLEXPRESS/ProjetoImpacta?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Users(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.Integer, unique=False, nullable=True)
 

@app.route('/')
def serve_index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def handle_form():

    data = request.get_json()
       
    new_contact = Users(
        name=data['name'],
        email=data['email'],
        phone=data['phone']
    )

    db.session.add(new_contact)
    db.session.commit()

    return(new_contact)

@app.route('/contacts')
def get_contacts():
    contacts = Users.query.order_by(Users.user_id).all()
    return render_template('contacts.html', contacts=contacts)



if __name__ == '__main__':
    app.run(debug=True)
