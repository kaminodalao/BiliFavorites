import datetime
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base

engine = sqlalchemy.create_engine("sqlite:///database.sqlite3")

Base = declarative_base()


def to_dict(self):
    return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


Base.to_dict = to_dict

Session = sqlalchemy.orm.sessionmaker(bind=engine)
session = Session()


class VideoCategory(Base):
    __tablename__ = "video_category"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    cid = sqlalchemy.Column(sqlalchemy.Integer)
    title = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    status = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    updated = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())


class VideoList(Base):
    __tablename__ = "video_list"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    category = sqlalchemy.Column(sqlalchemy.Integer)
    vid = sqlalchemy.Column(sqlalchemy.Integer)
    bvid = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    title = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    intro = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    cover = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    upid = sqlalchemy.Column(sqlalchemy.Integer)
    upname = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    upface = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    pubtime = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    status = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    updated = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now())


class Assets(Base):
    __tablename__ = "assets"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    type = sqlalchemy.Column(sqlalchemy.String(255))
    source = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    backup = sqlalchemy.Column(sqlalchemy.Text, nullable=True)


def init_db():
    Base.metadata.create_all(engine)


def drop_db():
    Base.metadata.drop_all(engine)
