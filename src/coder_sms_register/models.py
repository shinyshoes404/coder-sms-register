import sqlalchemy as db

metadata_obj = db.MetaData()

users = db.Table(
        'users',
        metadata_obj,
        db.Column('hash_id', db.String, primary_key=True),
        db.Column('username', db.String, nullable=False),
        db.Column('create_stamp', db.String, nullable=False),
)