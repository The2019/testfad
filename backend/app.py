# Flask application setup code here
from flask import Flask
app = Flask(__name__)

# Include SQLAlchemy models and API routes here
if __name__ == '__main__':
    app.run()