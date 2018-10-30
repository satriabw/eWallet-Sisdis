import os

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_migrate import Migrate
from constant import (
    BERHASIL, GAGAL_DATABASE,
    GAGAL_QUORUM, HOST_GAGAL,
    TIDAK_TERDEFINISI,
    USER_ID_TIDAK_ADA
)

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)



# DB model for account
class Account(db.Model):
    user_id = db.Column(db.String, primary_key=True)
    nama    = db.Column(db.String)
    amount  = db.Column(db.Integer)

    def __repr__(self):
        return '<Account {0} {1} {2}>'.format(self.user_id, self.nama, self.amount)

@app.route('/ping',  methods=["POST"])
def ping():
    pong = BERHASIL
    return jsonify(pong)

@app.route('/getSaldo',  methods=["POST"])
def getSaldo():
    return 'Hello, World!'

@app.route('/getTotalSaldo',  methods=["POST"])
def getTotalSaldo():
    return 'Hello, World!'

@app.route('/register',  methods=["POST"])
def register():
    status_register = BERHASIL
    try:
        data = request.json
        exist = Account.query.filter_by(user_id=data["user_id"]).first()
        if not exist:
            newAccount = Account(user_id=data["user_id"], nama=data["nama"], amount=1000000000)
            db.session.add(newAccount)
            db.session.commit()
        status_register = GAGAL_DATABASE
        return jsonify(status_register)
    except Exception:
        status_register = TIDAK_TERDEFINISI
        return jsonify(status_register)

@app.route('/transfer',  methods=["POST"])
def transfer():
    return 'Hello, World!'


if __name__ == "__main__":
    app.run()