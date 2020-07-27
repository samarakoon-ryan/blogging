from flask import Flask, render_template, request, redirect, flash, session
from flask_bcrypt import Bcrypt
from mysqlconnection import connectToMySQL
import re
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
PASSWORD_REGEX = re.compile(r'(?=^.{8,}$)((?=.*\d)|(?=.*\W+))(?![.\n])(?=.*[A-Z])(?=.*[a-z]).*$')
app = Flask(__name__)
app.secret_key = "boobear"
bcrypt = Bcrypt(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def home_page():
    if 'user_id' not in session:
        return redirect('/')

    query = "SELECT first_name FROM users WHERE id = %(id)s"
    data = {
        'id': session['user_id']
    }
    mysql = connectToMySQL('registrations')
    result = mysql.query_db(query, data)
    if result:
        query = "SELECT tweets.id, tweets.content, tweets.author, users.first_name, users.last_name FROM users JOIN tweets ON users.id = tweets.author"
        mysql = connectToMySQL('registrations')
        tweets = mysql.query_db(query)

        query = "SELECT liked_tweets.tweet_id FROM liked_tweets WHERE liked_tweets.user_id = %(u_id)s"
        data = {
            'u_id': session['user_id']
        }
        mysql = connectToMySQL('registrations')
        tweetids_loggedin_user_likes = mysql.query_db(query, data)

        l_t_i = [tweet['tweet_id'] for tweet in tweetids_loggedin_user_likes]

        return render_template("dashboard.html", user_data = result[0], tweets = tweets, l_t_i = l_t_i)
    else:
        flash("ERROR")
        return redirect("/")

@app.route("/user_tweet", methods=['POST'])
def tweet():
    is_valid = True
    tweet_content = request.form['tweet_content']

    if len(tweet_content) < 1:
        is_valid = False
        flash("Tweets must be at least 1 character long!")
    
    if len(tweet_content) > 255:
        is_valid = False
        flash("Tweets cannot be over 255 characters!")
    
    if is_valid:
        query = "INSERT INTO tweets (content, author, created_at, updated_at) VALUES (%(tweet)s, %(author)s, NOW(), NOW());"
        data = {
            'tweet': request.form['tweet_content'],
            'author': session['user_id']
        }
        mysql = connectToMySQL("registrations")
        mysql.query_db(query, data)
        
    return redirect("/dashboard")

@app.route("/on_delete/<tweet_id>")
def on_delete(tweet_id):
    if 'user_id' not in session:
        return redirect("/")

    query = "DELETE FROM tweets WHERE tweets.id = %(tweet_id)s;"
    data = {
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL("registrations")
    mysql.query_db(query, data)

    return redirect("/dashboard")

@app.route("/on_edit/<tweet_id>")
def on_edit(tweet_id):
    query = "SELECT tweets.id, tweets.content FROM tweets WHERE tweets.id = %(tweet_id)s"
    data = {
        'tweet_id': tweet_id,
    }
    mysql = connectToMySQL("registrations")
    tweet = mysql.query_db(query, data)
    if tweet:
        return render_template("post_edit.html", tweet_data = tweet[0])
    
    return redirect("/dashboard")

@app.route("/like/<tweet_id>")
def like(tweet_id):
    query = "INSERT INTO liked_tweets (user_id, tweet_id) VALUES (%(u_id)s, %(t_id)s)"
    data = {
        'u_id': session['user_id'],
        't_id': tweet_id
    }
    mysql = connectToMySQL("registrations")
    tweet_data = mysql.query_db(query, data)
    print(tweet_data)

    return redirect("/dashboard")

@app.route("/unlike/<tweet_id>")
def unlike_tweet(tweet_id):
    query = "DELETE FROM liked_tweets WHERE user_id = %(u_id)s AND tweet_id = %(t_id)s"
    data = {
        'u_id': session['user_id'],
        't_id': tweet_id
    }
    mysql = connectToMySQL("registrations")
    mysql.query_db(query, data)
    
    return redirect("/dashboard")


@app.route("/details/<tweet_id>")
def tweet_details(tweet_id):
    query = "SELECT users.first_name, users.last_name, tweets.created_at, tweets.content FROM users JOIN tweets ON users.id = tweets.author WHERE tweets.id = %(t_id)s"
    data = {
        't_id': tweet_id
    }
    mysql = connectToMySQL("registrations")
    tweet_data = mysql.query_db(query, data)
    if tweet_data:
        tweet_data = tweet_data[0]


    query = "SELECT users.first_name, users.last_name FROM liked_tweets JOIN users ON users.id = liked_tweets.user_id WHERE liked_tweets.tweet_id = %(t_id)s"
    data = {
        't_id': tweet_id
    }
    mysql = connectToMySQL("registrations")
    like_data = mysql.query_db(query, data)
    
    return render_template("details.html", tweet_data = tweet_data, like_data = like_data)

@app.route("/editor/<tweet_id>", methods=['POST'])
def editor(tweet_id):
    is_valid = True
    query = "UPDATE tweets SET tweets.content = %(tweet)s WHERE tweets.id = %(tweet_id)s"
    data = {
        'tweet': request.form['tweet_edit'],
        'tweet_id': tweet_id
    }
    mysql = connectToMySQL("registrations")
    result = mysql.query_db(query, data)
    
    if is_valid:
        return redirect("/tweets")

@app.route("/cancel")
def cancel():
    return redirect("/dashboard")

@app.route("/register", methods=['POST'])
def register_user():
    is_valid = True
    if len(request.form['fn']) < 1:
        is_valid = False
        flash("First name is a required field")
    if not request.form['fn'].isalpha():
        is_valid = False
        flash("First name can only contain alphabetic characters")
    
    if len(request.form['ln']) < 1:
        is_valid = False
        flash("Last name is a required field")
    if not request.form['ln'].isalpha():
        is_valid = False
        flash("Last name can only contain alphabetic characters")

    if not PASSWORD_REGEX.match(request.form['pw']):
        is_valid = False
        flash("Password must meet requirements!")
    if request.form['pw'] != request.form['cpw']:
        is_valid = False
        flash("Passwords must match")

    db = connectToMySQL('registrations')
    email_query = 'SELECT id FROM users WHERE email=%(em)s;'
    email_data = {
        'em': request.form['em']
    }
    existing_users = db.query_db(email_query, email_data)

    if existing_users:
        flash("Email already in use")
        is_valid = False
    
    if is_valid:
        pw_hash = bcrypt.generate_password_hash(request.form['pw'])

        query = "INSERT INTO users (first_name, last_name, email, password, created_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW());"
        data = {
            "fn": request.form['fn'],
            "ln": request.form['ln'],
            "em": request.form['em'],
            "pw": pw_hash
        }
        mysql = connectToMySQL('registrations')
        user_id = mysql.query_db(query, data)
        print(user_id)

        if user_id:
            session['user_id'] = user_id
            return redirect('/tweets')
    
    return redirect("/")


@app.route("/login", methods=['POST'])
def login():
    is_valid = True

    if not EMAIL_REGEX.match(request.form['em']):
        is_valid = False
        flash("Invalid email address!")

    if is_valid:
        query = "SELECT id, password FROM users WHERE email = %(em)s"
        data = {
            'em': request.form['em']
        }
        mysql = connectToMySQL('registrations')
        result = mysql.query_db(query, data)

        if result:
            if not bcrypt.check_password_hash(result[0]['password'], request.form['pw']):
                flash("incorrect password")
                return redirect("/")
            else:
                session['user_id'] = result[0]['id']
                return redirect("/tweets")
        else:
            flash("email is not valid")
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)