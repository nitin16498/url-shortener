from flask import Flask, request, redirect, render_template_string
import redis
import base64
import hashlib
import os

app = Flask(__name__)

# Configure Redis connection using environment variables
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None),
)


def generate_short_code(long_url):
    hash_object = hashlib.sha256(long_url.encode())
    hash_digest = hash_object.digest()
    short_code = base64.urlsafe_b64encode(hash_digest[:6]).decode("utf-8")
    return short_code


def save_url_mapping(short_code, long_url):
    r.set(short_code, long_url)


def get_long_url(short_code):
    long_url = r.get(short_code)
    if long_url:
        return long_url.decode("utf-8")
    else:
        return None


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        long_url = request.form["long_url"]
        short_code = generate_short_code(long_url)
        save_url_mapping(short_code, long_url)
        short_url = request.host_url + short_code
        return render_template_string(
            """
            <p>Short URL: <a href="{{ short_url }}">{{ short_url }}</a></p>
            <p><a href="/">Shorten another URL</a></p>
        """,
            short_url=short_url,
        )
    return render_template_string(
        """
        <h1>URL Shortener</h1>
        <form method="post">
            <input type="url" name="long_url" placeholder="Enter the long URL" required>
            <input type="submit" value="Shorten">
        </form>
    """
    )


@app.route("/<short_code>")
def redirect_short_url(short_code):
    long_url = get_long_url(short_code)
    if long_url:
        return redirect(long_url)
    else:
        return (
            render_template_string(
                """
            <h1>URL not found</h1>
            <p>The short URL does not exist.</p>
            <p><a href="/">Go back to home</a></p>
        """
            ),
            404,
        )


if __name__ == "__main__":
    app.run()
