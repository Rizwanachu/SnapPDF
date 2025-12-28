from app import app
import routes  # noqa: F401
import os

# Ensure directories exist for Vercel
os.makedirs(os.path.join('/tmp', 'uploads'), exist_ok=True)
os.makedirs(os.path.join('/tmp', 'processed'), exist_ok=True)

# Application object for Vercel
app = app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
