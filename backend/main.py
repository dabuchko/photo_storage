from flask import Flask, g, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import sqlite3
import re
import hashlib
import random
import os
from predict import ImageToTextPredict
import argparse
import zipfile
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="0.0.0.0", type=str, help="Host where API should be launched.")
parser.add_argument("--port", default=5000, type=int, help="Port where API should be launched.")
parser.add_argument("--path", default="/", type=str, help="Base path for all API endpoints.")
parser.add_argument("--https", default=False, action='store_true', help="Whether to server API using HTTPS or HTTP. True stands for using HTTPS.")
parser.add_argument("--debug", default=False, action='store_true', help="Whether to turn Flask debug mode on (True) or off (False).")
parser.add_argument("--database_path", default='database.db', type=str, help="Path to the SQLite3 database file.")
parser.add_argument("--secret_key", default="VERY_SECRET_KEY", type=str, help="Secret key to generate Authorization tokens.")
parser.add_argument("--token_exp", default=86400, type=int, help="The maximum time in seconds for which authorization token will remain valid.")
parser.add_argument("--model_path", default="model.pt", type=str, help="Path to the saved model of the ImageToTextModel class.")
parser.add_argument("--album_matching_threshold", default=0.15, type=float, help="The threshold of the maximum cosine distance to classify image to the album. Exceeding the provided distance for all of the albums will leave the image unclassified among the albums.")
parser.add_argument("--pred_batch_size", default=32, type=int, help="Batch size for prediction generation.")
args = parser.parse_args()

app = Flask(__name__, args.path)
SUPPORTED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif']
IMAGE_TO_TEXT_MODEL = ImageToTextPredict(args.model_path, args.album_matching_threshold, args.pred_batch_size)

serializer = URLSafeTimedSerializer(args.secret_key)

@app.after_request
def add_cors_headers(response):
    """Sets CORS policy to allow requests from any source."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, UPDATE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

def generate_auth_token(user_id):
    """Generates a signed token for the user."""
    return serializer.dumps(user_id)

def verify_auth_token(token):
    """Verifies the signed token and returns the user ID."""
    try:
        user_id = serializer.loads(token, max_age=args.token_exp)
        return user_id
    except (BadSignature, SignatureExpired):
        return None



def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(args.database_path)
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()



@app.errorhandler(404)
def not_found(error):
    """In case of a 404 error, return a JSON description of the error."""
    return jsonify({"error": "Not found."}), 404

def bad_request(error: str):
    """In case of a 400 error, return a JSON description of the error."""
    return jsonify({"error": error}), 400

def not_authorized(valid: bool):
    """In case of a 401 error, return a JSON description of the error with authentication status."""
    return jsonify({"error": "You do not have permission to perform this operation.", "authenticated": valid}), 401

@app.before_request
def check_authentication():
    """Checks if the user is authenticated by verifying the token."""
    
    if request.method=="OPTIONS":
        # allow any OPTIONS request
        return

    if request.path in ['/user/signup', '/user/login']:
        # Skip authentication for signup and login endpoints
        return
    
    # Check for the Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return not_authorized(False)
    
    # Verify the token
    id = verify_auth_token(auth_header)
    if id is None:
        return not_authorized(False)
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    if cursor.fetchone() is None:
        return not_authorized(False)
    
    # Store the user ID in the global context for later use
    g.user_id = id
    
    

@app.route("/user/signup", methods=["POST"])
def signup():
    """Endpoint for user registration."""
    # get data from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "username" in data:
        username = data["username"]
    else:
        return bad_request("Username is missing.")
    if "password" in data:
        password = data["password"]
    else:
        return bad_request("Password is missing.")

    # check if username in right format
    if re.fullmatch(r'[a-z0-9_]+', username) is None:
        return bad_request("Username must only contain lowercase letters, numbers, and underscores.")

    # check if password is strong enough
    if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
        return bad_request("Password must be at least 8 characters long and contain uppercase letters, lowercase letters, and numbers.")

    # check if username is free
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone() is not None:
        return bad_request("Username is already taken.")

    # register a user, hash the password (it is i BLOB format in the database)
    password = hashlib.md5(password.encode()).digest()
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    get_db().commit()

    # generate bearer token
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()['id']
    auth_token = generate_auth_token(user_id)
    if auth_token is None:
        return bad_request("Failed to generate authentication token.")
    
    # create a default albums for the user. The album with name "" is expected to
    # remain unmodified and keep all photos that was not assigned to neither of the
    # remaining albums
    cursor.execute("INSERT INTO albums (name, user) VALUES (?, ?)", ("", user_id))
    cursor.execute("INSERT INTO albums (name, user) VALUES (?, ?)", ("Album 1", user_id))
    get_db().commit()

    return jsonify({'auth_token': auth_token}), 200

@app.route("/user/login", methods=["POST"])
def login():
    """Endpoint for user login."""
    # get data from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "username" in data:
        username = data["username"]
    else:
        return bad_request("Username is missing.")
    if "password" in data:
        password = data["password"]
    else:
        return bad_request("Password is missing.")

    # get id if user exists
    cursor = get_db().cursor()
    password = hashlib.md5(password.encode()).digest()
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    if user is None:
        return not_authorized(False)
    else:
        user_id = user['id']

    # generate bearer token
    auth_token = generate_auth_token(user_id)
    if auth_token is None:
        return bad_request("Failed to generate authentication token.")

    return jsonify({'auth_token': auth_token}), 200

@app.route("/user", methods=["UPDATE"])
def update_user():
    """Endpoint for updating user information."""
    # get data from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "username" in data:
        username = data["username"]
    else:
        return bad_request("Username is missing.")
    if "password" in data:
        password = data["password"]
    else:
        return bad_request("Password is missing.")
    
    # get current username
    cursor = get_db().cursor()
    cursor.execute("SELECT username FROM users WHERE id = ?", (g.user_id,))
    current_username = cursor.fetchone()
    if current_username is None:
        return not_authorized(False)
    current_username = current_username['username']
    
    if username != "" and username != current_username:
        # check if username is free
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone() is not None:
            return bad_request("Username is already taken.")
        
        # check if username in right format
        if re.fullmatch(r'[a-z0-9_]+', username) is None:
            return bad_request("Username must only contain lowercase letters, numbers, and underscores.")
        current_username = username
    
    if password!="":
        # check if password is strong enough
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
            return bad_request("Password must be at least 8 characters long and contain uppercase letters, lowercase letters, and numbers.")
        # hash the password
        password = hashlib.md5(password.encode()).digest()
        # update user information
        cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = ?", (current_username, password, g.user_id))
    else:
        # update user information without changing password
        cursor.execute("UPDATE users SET username = ? WHERE id = ?", (current_username, g.user_id))
    get_db().commit()

    # generate bearer token
    auth_token = generate_auth_token(g.user_id)
    if auth_token is None:
        return bad_request("Failed to generate authentication token.")
    
    return jsonify({'auth_token': auth_token}), 200

@app.route("/user", methods=["DELETE"])
def delete_user():
    """Endpoint for deleting user account."""
    cursor = get_db().cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (g.user_id,))
    get_db().commit()
    if cursor.rowcount == 0:
        return bad_request("User not found or already deleted.")
    return jsonify({"message": "User account deleted successfully."}), 200

@app.route("/albums", methods=["GET"])
def get_albums():
    """Endpoint for getting all albums of the current user."""
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM albums WHERE user = ?", (g.user_id,))
    albums = cursor.fetchall()
    
    return jsonify([{
        "id": album["id"],
        "name": album["name"],
    } for album in albums]), 200


@app.route("/album", methods=["PUT"])
def create_album():
    """Endpoint for creating a new album."""
    # get album name from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "name" in data:
        name = data["name"]
    else:
        return bad_request("Album name is missing.")
    
    # check if album name is in right format
    if len(name)==0:
        return bad_request("Album name cannot be empty.")
    if re.fullmatch(r'[a-zA-Z0-9_ ]+', name) is None:
        return bad_request("Album name must only contain latin letters, numbers, underscores, and spaces.")
    
    # check if album name is free
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM albums WHERE name = ? AND user = ?", (name, g.user_id))
    if cursor.fetchone() is not None:
        return bad_request("Album name is already taken.")
    
    # create a new album and return its ID
    cursor.execute("INSERT INTO albums (name, user) VALUES (?, ?)", (name, g.user_id))
    get_db().commit()
    album_id = cursor.lastrowid
    return jsonify({"id": album_id}), 200

@app.route("/album", methods=["UPDATE"])
def update_album():
    """Endpoint for updating an album name."""
    # get data from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "id" in data:
        album_id = data["id"]
    else:
        return bad_request("Album ID is missing.")
    if "name" in data:
        name = data["name"]
    else:
        return bad_request("Album name is missing.")
    
    # check if album name is in right format
    if len(name)==0:
        return bad_request("Album name cannot be empty.")
    if re.fullmatch(r'[a-zA-Z0-9_ ]+', name) is None:
        return bad_request("Album name must only contain latin letters, numbers, underscores, and spaces.")
    
    # check if album exists
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM albums WHERE id = ? AND user = ?", (album_id, g.user_id))
    album = cursor.fetchone()
    if album is None:
        return bad_request("Album not found.")
    
    # check if album name is free
    cursor.execute("SELECT * FROM albums WHERE name = ? AND user = ? AND id != ?", (name, g.user_id, album_id))
    if cursor.fetchone() is not None:
        return bad_request("Album name is already taken.")
    
    # update album name
    cursor.execute("UPDATE albums SET name = ? WHERE id = ?", (name, album_id))
    get_db().commit()
    
    return jsonify({"message": "Album updated successfully."}), 200

@app.route("/album", methods=["DELETE"])
def delete_album():
    """Endpoint for deleting an album."""
    # get album ID from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "id" in data:
        album_id = data["id"]
    else:
        return bad_request("Album ID is missing.")
    
    # check if album exists
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM albums WHERE id = ? AND user = ?", (album_id, g.user_id))
    album = cursor.fetchone()
    if album is None:
        return bad_request("Album not found.")
    
    # delete album and its photos
    cursor.execute("DELETE FROM albums WHERE id = ?", (album_id,))
    get_db().commit()
    
    return jsonify({"message": "Album deleted successfully."}), 200

@app.route("/photo", methods=["GET"])
def get_photos():
    """Endpoint for getting 50 photos from an album."""
    id = request.args.get("id")
    offset = request.args.get("offset")
    if offset == None:
        return bad_request("The 'offset' argument in query is expected.")
    offset = int(offset)
    cursor = get_db().cursor()
    if id is not None:
        id = int(id)
        cursor.execute("SELECT * FROM albums WHERE id = ? AND user = ?", (id, g.user_id))
        album = cursor.fetchone()
        if album is None:
            return bad_request("Album not found.")
        
        cursor.execute("SELECT * FROM photos WHERE album = ? LIMIT 50 OFFSET ?", (album["id"], offset))
        photos = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM photos WHERE album IN (SELECT id FROM albums WHERE user = ?) LIMIT 50 OFFSET ?", (g.user_id, offset))
        photos = cursor.fetchall()
    
    return jsonify([{
        "id": photo["id"],
        "caption": photo["caption"],
        "album": photo["album"],
        "date": photo["date"],
        "name": photo["name"]
    } for photo in photos]), 200

@app.route("/photo", methods=["POST"])
def get_photo_metadata():
    """Endpoint for getting metadata of an array of photos or for the specified album."""
    # get photo IDs from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "ids" in data:
        ids = data["ids"]
        if ids=="*":
            # extract metadata of all photos of the current user
            cursor = get_db().cursor()
            cursor.execute(f"SELECT photos.id, photos.caption, photos.date, albums.name AS album_name, photos.name AS photo_name FROM photos LEFT JOIN albums ON photos.album==albums.id WHERE photos.album IN (SELECT id FROM albums WHERE user = ? )", (g.user_id,))
            photos = cursor.fetchall()
        else:
            # check if all IDs are integers
            if not isinstance(ids, list) or not all(isinstance(id, int) for id in ids):
                return bad_request("Photo IDs must be a list of integers.")

            # extract metadata for the given photo IDs
            cursor = get_db().cursor()
            photo_ids_str = ",".join(map(str,ids))
            cursor.execute(f"SELECT photos.id, photos.caption, photos.date, albums.name AS album_name, photos.name AS photo_name FROM photos LEFT JOIN albums ON photos.album==albums.id WHERE photos.id IN ({photo_ids_str}) AND photos.album IN (SELECT id FROM albums WHERE user = ?)", (g.user_id,))
            photos = cursor.fetchall()
    elif "album" in data:
        album = int(data["album"])
        cursor = get_db().cursor()
        cursor.execute(f"SELECT photos.id, photos.caption, photos.date, albums.name AS album_name, photos.name AS photo_name FROM photos LEFT JOIN albums ON photos.album==albums.id WHERE photos.album IN (SELECT id FROM albums WHERE user = ? AND id = ? )", (g.user_id, album))
        photos = cursor.fetchall()

    else:
        return bad_request("Photo IDs are missing.")
    
    

    return jsonify([{
        "id": photo["id"],
        "caption": photo["caption"],
        "date": photo["date"],
        "album": photo["album_name"],
        "filename": photo["photo_name"]
    } for photo in photos]), 200

@app.route("/photo", methods=["PUT"])
def upload_photo():
    """Endpoint for uploading photos and zip files with photos."""
    # check if file is provided
    if 'file[]' not in request.files:
        return bad_request("No file part in the request.")
    
    
    init_files = request.files.getlist("file[]")
    processed_files = []
    original_filenames = []

    if not os.path.exists("images"):
        os.makedirs("images")
    if not os.path.exists("thumbnails"):
        os.makedirs("thumbnails")

    for file in init_files:
        # check if file is empty
        if file.filename == '':
            return bad_request("No selected file.")
    
        # check if file has a valid extension
        extension = file.filename.rsplit('.', 1)[1].lower()
        if extension!="zip" and extension not in SUPPORTED_EXTENSIONS:
            return bad_request("File type is not supported. Supported types are: zip, " + ", ".join(SUPPORTED_EXTENSIONS))
    

        # save files to the server
        def generate_new_filename(old_filename):
            extension = old_filename.rsplit('.', 1)[1].lower()
            new_filename = f"{hashlib.md5(old_filename.encode()).hexdigest()}_{random.randint(1000, 9999)}.{extension}"
            while os.path.exists(f"images/{new_filename}"):
                new_filename = f"{hashlib.md5(old_filename.encode()).hexdigest()}_{random.random()}.{extension}"
            return new_filename
    
        file_path = generate_new_filename(file.filename)
        

        if extension=="zip":
            file.save(file_path)
            file.close()
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                for f in zip_ref.filelist:
                    if not f.is_dir() and f.filename.rsplit('.', 1)[1].lower() in SUPPORTED_EXTENSIONS:
                        try:
                            f.filename = generate_new_filename(f.filename)
                            zip_ref.extract(f, "images")
                            img = Image.open("images/" + f.filename)
                            img.thumbnail((700, 100), Image.Resampling.LANCZOS)
                            img.save("thumbnails/" + f.filename)
                            processed_files.append(f.filename)
                            original_filenames.append(f.orig_filename.replace('/', '_'))
                        except:
                            if os.path.exists("images/" + f.filename):
                                os.remove("images/" + f.filename)
            os.remove(file_path)
        else:
            try:
                file.save("images/" + file_path)
                file.close()
                img = Image.open("images/" + file_path)
                img.thumbnail((700, 100), Image.Resampling.LANCZOS)
                img.save("thumbnails/" + file_path)
            except:
                if os.path.exists("images/" + file_path):
                    os.remove("images/" + file_path)
                return bad_request("Invalid image file")
            processed_files.append(file_path)
            original_filenames.append(file.filename)

    # get a list of albums for the user
    cursor = get_db().cursor()
    cursor.execute("SELECT id, name FROM albums WHERE user = ?", (g.user_id,))
    albums = cursor.fetchall()
    if len(albums) == 0:
        # create a default album if it doesn't exist
        cursor.execute("INSERT INTO albums (name, user) VALUES (?, ?)", ("", g.user_id))
        get_db().commit()
        cursor.execute("SELECT name FROM albums WHERE user = ?", (g.user_id,))
        albums = cursor.fetchall()
    
    albums = {album['name']: album['id'] for album in albums}
    albums_keys = list(albums.keys())

    preds = IMAGE_TO_TEXT_MODEL.predict(list(map(lambda x: "images/"+x, processed_files)), albums_keys)
    predicted_captions = []
    predicted_album_ids = []
    for (caption, album_local_id) in preds:
        predicted_captions.append(caption)
        predicted_album_ids.append(albums[albums_keys[album_local_id]])

    photo_ids = []
    for i in range(len(processed_files)):
        cursor.execute("INSERT INTO photos (album, image, caption, name) VALUES (?, ?, ?, ?) RETURNING id", (predicted_album_ids[i], processed_files[i], predicted_captions[i], original_filenames[i]))
        photo_ids.append(cursor.fetchone()[0])
    get_db().commit()
    
    if photo_ids is None:
        return bad_request("Failed to save photo to the database.")

    return jsonify([{"id": photo_ids[i], "album": predicted_album_ids[i], "caption": predicted_captions[i]} for i in range(len(processed_files))]), 200

@app.route("/photo", methods=["UPDATE"])
def update_photo():
    """Endpoint for updating a photo's caption and/or album."""
    # get data from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "id" in data:
        photo_id = data["id"]
    else:
        return bad_request("Photo ID is missing.")
    if "caption" in data:
        caption = data["caption"]
    else:
        return bad_request("Caption is missing.")
    if "album" in data:
        album_id = data["album"]
    else:
        return bad_request("Album ID is missing.")
    
    # check if photo exists
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM photos WHERE id = ? AND album IN (SELECT id FROM albums WHERE user = ?)", (photo_id, g.user_id))
    photo = cursor.fetchone()
    if photo is None:
        return bad_request("Photo not found.")
    
    # check if album exists
    cursor.execute("SELECT * FROM albums WHERE id = ? AND user = ?", (album_id, g.user_id))
    album = cursor.fetchone()
    if album is None:
        return bad_request("Album not found.")
    
    # update photo caption and album
    cursor.execute("UPDATE photos SET caption = ?, album = ? WHERE id = ?", (caption, album_id, photo_id))
    get_db().commit()

    return jsonify({"message": "Photo updated successfully."}), 200

@app.route("/photo", methods=["DELETE"])
def delete_photo():
    """Endpoint for deleting a photo."""
    # get photo ID from request
    data = request.get_json()
    if not data:
        return bad_request("No data provided in the request.")
    if "id" in data:
        photo_id = data["id"]
    else:
        return bad_request("Photo ID is missing.")
    
    # check if photo exists
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM photos WHERE id = ? AND album IN (SELECT id FROM albums WHERE user = ?)", (photo_id, g.user_id))
    photo = cursor.fetchone()
    location = photo["image"]
    if photo is None:
        return bad_request("Photo not found.")
    
    # delete photo
    cursor.execute("DELETE FROM photos WHERE id = ? AND album IN (SELECT id FROM albums WHERE user = ?)", (photo_id, g.user_id))
    os.remove(location)
    get_db().commit()

    return jsonify({"message": "Photo deleted successfully."}), 200

@app.route("/image/<int:id>", methods=["GET"])
def get_image(id):
    """Endpoint for retrieving image content by ID. If "thumbnail" GET parameter
    is set, then a downscaled thumbnail is returned instead of the original image.
    """

    is_thumbnail = request.args.get("thumbnail") != None

    cursor = get_db().cursor()
    cursor.execute("SELECT image FROM photos WHERE id = ? AND album IN (SELECT id FROM albums WHERE user = ?)", (id, g.user_id))
    image = cursor.fetchone()
    if image is None:
        return bad_request("Image not found.")

    image_path = "thumbnails/" + image['image'] if is_thumbnail else "images/" + image['image']
    if not os.path.exists(image_path):
        return bad_request("Image file does not exist.")
    
    with open(image_path, 'rb') as img_file:
        img_data = img_file.read()
    
    ext = image_path[-image_path[::-1].index('.'):]
    return img_data, 200, {'Content-Disposition': f'attachment; filename="{os.path.basename(image_path)}"', 'Content-Type': f"image/{ext}"}

@app.route("/search/<query>", methods=["GET"])
def search_photos(query):
    """Endpoint for searching top 50 photos by caption with the given offset."""
    cursor = get_db().cursor()
    offset = request.args.get("offset")
    if offset is None:
        offset = 0
    else:
        offset = int(offset)
    cursor.execute("SELECT * FROM photos WHERE caption LIKE ? AND album IN (SELECT id FROM albums WHERE user = ?) LIMIT 50 OFFSET ?", (f"%{query}%", g.user_id, offset))
    photos = cursor.fetchall()
    return jsonify([{
        "id": photo["id"],
        "caption": photo["caption"],
        "album": photo["album"],
        "date": photo["date"],
        "name": photo["name"]
    } for photo in photos]), 200

if __name__ == "__main__":
    if not os.path.exists("images"):
        os.makedirs("images")
    if args.https or args.debug:
        # launch a development server
        if args.https:
            app.run(args.host, args.port, args.debug, ssl_context='adhoc')
        else:
            app.run(args.host, args.port, args.debug)
    else:
        # launch non development server
        from waitress import serve
        serve(app, host=args.host, port=args.port)
