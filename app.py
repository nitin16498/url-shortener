from flask import Flask, request, redirect, render_template, url_for
import redis
import base64
import hashlib
import os
import validators

app = Flask(__name__)

# Configure Redis connection using environment variables
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None),
)


def generate_short_code(long_url):
    # Generate a unique short code using SHA-256 hash
    hash_object = hashlib.sha256(long_url.encode())
    hash_digest = hash_object.digest()
    # Use base64 encoding and remove padding characters
    short_code = base64.urlsafe_b64encode(hash_digest[:6]).decode("utf-8").rstrip("=")
    return short_code


def save_url_mapping(short_code, long_url):
    if r.exists(short_code):
        return False
    r.set(short_code, long_url)
    return True


def get_long_url(short_code):
    long_url = r.get(short_code)
    if long_url:
        # Increment click count
        r.incr(f"clicks:{short_code}")
        return long_url.decode("utf-8")
    else:
        return None


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        long_url = request.form["long_url"]
        custom_code = request.form.get("custom_code", "").strip()

        # Validate the long URL
        if not validators.url(long_url):
            error = "Invalid URL. Please enter a valid URL."
            return render_template("home.html", error=error)

        if custom_code:
            short_code = custom_code
            # Check if custom code already exists
            if r.exists(short_code):
                error = "Custom short code already exists. Please choose another one."
                return render_template("home.html", error=error)
        else:
            short_code = generate_short_code(long_url)
            # Ensure uniqueness in case of collision
            while r.exists(short_code):
                long_url += "1"
                short_code = generate_short_code(long_url)

        if not save_url_mapping(short_code, long_url):
            error = "Short code already exists. Please try a different one."
            return render_template("home.html", error=error)

        short_url = request.host_url + short_code
        return render_template("shortened.html", short_url=short_url)
    else:
        return render_template("home.html")


@app.route("/<short_code>")
def redirect_short_url(short_code):
    long_url = get_long_url(short_code)
    if long_url:
        return redirect(long_url)
    else:
        return render_template("404.html"), 404


@app.route("/stats/<short_code>")
def stats(short_code):
    if r.exists(short_code):
        long_url = r.get(short_code).decode("utf-8")
        clicks = r.get(f"clicks:{short_code}") or 0
        return render_template(
            "stats.html", short_code=short_code, long_url=long_url, clicks=int(clicks)
        )
    else:
        return render_template("404.html"), 404


if __name__ == "__main__":
    app.run()
