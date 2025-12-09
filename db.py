from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

ssl_args = {
    "ssl": {
        "ca": "certs/server-ca.pem",
        "cert": "certs/client-cert.pem",
        "key": "certs/client-key.pem",
    }
}

engine = create_engine(DATABASE_URL, connect_args=ssl_args, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
