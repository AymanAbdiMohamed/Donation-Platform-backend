"""
Flask run entry point.
"""
from app import app
from db import Base, engine

# Create all tables
Base.metadata.create_all(engine)

print("Server running")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
