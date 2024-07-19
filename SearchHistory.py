from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(80), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=1)
