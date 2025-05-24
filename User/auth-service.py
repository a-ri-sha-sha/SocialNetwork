from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@db:5432/users_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret') 
db = SQLAlchemy(app)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    birth_date = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if Users.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400

    hashed_password = generate_password_hash(data['password'])
    new_user = Users(
        username=data['username'], email=data['email'], password_hash=hashed_password
    )
    token = jwt.encode({'username': new_user.username}, app.config['SECRET_KEY'], algorithm='HS256')
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Users registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = Users.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = jwt.encode({'username': user.username}, app.config['SECRET_KEY'], algorithm='HS256')
    response = make_response(jsonify({"message": "User registered successfully"}), 200)
    response.set_cookie("jwt", token)
    return response

@app.route('/profile', methods=['GET'])
def profile():
    token = request.cookies.get("jwt")
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = Users.query.filter_by(username=data['username']).first()
        if not user:
            return jsonify({'error': 'Users not found'}), 404
        return jsonify({
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'birth_date': user.birth_date,
            'phone': user.phone,
            'created_at': user.created_at,
            'updated_at': user.updated_at
        })
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    
    except jwt.InvalidTokenError:
        # return jsonify({'error': 'Invalid token'}), 401
        pass

@app.route('/profile', methods=['PUT'])
def update_profile():
    token = request.cookies.get("jwt")
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = Users.query.filter_by(username=data['username']).first()
        if not user:
            return jsonify({'error': 'Users not found'}), 404
        
        update_data = request.get_json()
        user.first_name = update_data.get('first_name', user.first_name)
        user.last_name = update_data.get('last_name', user.last_name)
        user.birth_date = update_data.get('birth_date', user.birth_date)
        user.phone = update_data.get('phone', user.phone)
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
