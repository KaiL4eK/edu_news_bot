from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
DB_CONNECT = os.environ.get('DB_CONNECT')

engine = create_engine(DB_CONNECT)
Session = sessionmaker(bind=engine)

Base = declarative_base()
