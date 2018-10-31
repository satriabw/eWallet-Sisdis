import os
import requests
import math
import sys

from flask import Flask, request, jsonify, Blueprint
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from config import Config, quorum, init_quorum
from flask_migrate import Migrate
from constant import (
    BERHASIL, GAGAL_DATABASE,
    GAGAL_QUORUM, HOST_GAGAL,
    TIDAK_TERDEFINISI,
    USER_ID_TIDAK_ADA,
    SYARAT_TRANSFER_GAGAL
)
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
quorum_list = os.getenv("QUORUM").split(",")
host = os.getenv("HOST")
hostname = os.getenv("HOST_NAME")

bp = Blueprint('ewallet', __name__, url_prefix='/ewallet')

threshold_high  = len(quorum_list)
threshold_mid = math.floor(len(quorum_list)/2) + 1

# DB model for account
class Account(db.Model):
    user_id    = db.Column(db.String, primary_key=True)
    nama       = db.Column(db.String)
    amount     = db.Column(db.Integer)
    is_host    = db.Column(db.Boolean)

    def __repr__(self):
        return '<Account {0} {1} {2}>'.format(self.user_id, self.nama, self.amount)

def init_account():
    account = Account.query.filter_by(user_id=host).first()
    if not account:
        newAccount = Account(user_id=host, nama=hostname, amount=1000000000, is_host=True)
        db.session.add(newAccount)
        db.session.commit()


db.create_all()
db.session.commit()

init_quorum()
init_account()

print(quorum)
print("\nHOST:", host, "\n")

def checkQuorum(threshold, ret_name):
    def decoratorCheckQuorum(func):
        @wraps(func)
        def wrapperCheckQuorum(*args, **kwargs):
            t = 0
            value = jsonify({ret_name: GAGAL_QUORUM})
            for q in quorum_list:
                try:
                    url = "http://{}/ewallet/ping".format(quorum[q])
                    r = requests.post(url, json={})
                    if r.json()["pingReturn"] == 1:
                        t += 1
                    if t >= threshold:
                        value = func(*args, **kwargs)
                        break
                except requests.ConnectionError:
                    continue
            print("\nt:", t," threshold:", threshold, "\n")
            return value
        return wrapperCheckQuorum
    return decoratorCheckQuorum

@bp.route('/ping',  methods=["POST"])
def ping():
    pong = BERHASIL
    return jsonify({"pingReturn":pong})

@bp.route('/getSaldo',  methods=["POST"])
@checkQuorum(threshold_mid, "saldo")
def getSaldo():
    data = request.json
    status_saldo = BERHASIL
    try:
        account = Account.query.filter_by(user_id=data["user_id"]).first()
        if not account:
            status_saldo = USER_ID_TIDAK_ADA
            return jsonify({"saldo": status_saldo})
        saldo = account.amount
        return jsonify({"saldo": saldo})
    except exc.SQLAlchemyError:
        status_saldo = GAGAL_DATABASE
        return jsonify({"saldo": status_saldo})
    except Exception:
        status_saldo = TIDAK_TERDEFINISI
        return jsonify({"saldo": status_saldo})

@bp.route('/getTotalSaldo',  methods=["POST"])
@checkQuorum(threshold_high, "saldo")
def getTotalSaldo():
    data = request.json
    status_total = BERHASIL
    
    try:
        account = Account.query.filter_by(user_id=data["user_id"]).first()
        if not account:
            status_total = USER_ID_TIDAK_ADA
            return jsonify({"saldo": status_total})
        if not account.is_host:
            url = "http://{}/ewallet/getTotalSaldo".format(quorum[account.user_id])
            r = requests.post(url, json={"user_id": account.user_id})
            return jsonify(r.json())
        
        saldo = 0
        for q in quorum_list:
            url = "http://{}/ewallet/getSaldo".format(quorum[q])
            r = requests.post(url, json={"user_id":account.user_id})
            print(r.json()["saldo"])
            if r.json()["saldo"] >= 0:
                saldo += r.json()["saldo"]
            elif r.json()["saldo"] == -1:
                regis_url = "http://{}/ewallet/register".format(quorum[q])
                r_regis = requests.post(regis_url, json={"user_id":account.user_id, "nama": account.nama})
                continue
            elif r.json()["saldo"] < -1:
                status_saldo = HOST_GAGAL
                return jsonify({"saldo": status_saldo})

        return jsonify({"saldo": saldo})

    except requests.ConnectionError:
        status_saldo = HOST_GAGAL
        return jsonify({"registerReturn":status_saldo})

    except Exception:
        status_saldo = TIDAK_TERDEFINISI
        return jsonify({"registerReturn":status_saldo})

@bp.route('/register',  methods=["POST"])
@checkQuorum(threshold_mid, "registerReturn")
def register():
    data = request.json
    status_register = BERHASIL
    try:
        if data["user_id"] not in quorum:
            raise ValueError("Tidak boleh mendaftar kalau bukan di quorum")
        newAccount = Account(user_id=data["user_id"], nama=data["nama"], amount=0, is_host=False)
        db.session.add(newAccount)
        db.session.commit()
        return jsonify({"registerReturn":status_register})
    except exc.SQLAlchemyError as e:
        status_register = GAGAL_DATABASE
        return jsonify({"registerReturn":status_register})
    except Exception:
        status_register = TIDAK_TERDEFINISI
        return jsonify({"registerReturn":status_register})

@bp.route('/transfer',  methods=["POST"])
@checkQuorum(threshold_mid, "transferReturn")
def transfer():
    data =  request.json
    status_transfer = BERHASIL
    try:
        account = Account.query.filter_by(user_id=data["user_id"]).first()
        if not account:
            status_transfer = USER_ID_TIDAK_ADA
            return jsonify({"transferReturn": status_transfer})

        if data["nilai"] < 0 or data["nilai"] > 1000000000:
            status_transfer = SYARAT_TRANSFER_GAGAL
            return jsonify({"transferReturn": status_transfer})

        account.amount += data["nilai"]
        db.session.commit()

        return jsonify({"transferReturn": status_transfer})
    except exc.SQLAlchemyError:
        status_transfer = GAGAL_DATABASE
        return jsonify({"transferReturn": status_transfer})
    except Exception:
        status_transfer = TIDAK_TERDEFINISI
        return jsonify({"transferReturn": status_transfer})


@app.route('/substractSaldo', methods=["POST"])
def substractSaldo():
    try:
        data = request.json
        account = Account.query.filter_by(user_id=data["user_id"]).first()
        if not account:
            return jsonify({"substractReturn": -1})
        account.amount -= data["nilai"]
        db.session.commit()

        return jsonify({"substractReturn": 1})
    except Exception:
        return jsonify({"substractReturn": -99})

if __name__ == "__main__":
    app.register_blueprint(bp)
    app.run(host=str(sys.argv[1]), port=int(sys.argv[2]))