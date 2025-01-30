from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Date, ForeignKey
from datetime import datetime
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'


class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_login.db'
app.config['SQLALCHEMY_BINDS'] = {
    'db2': 'sqlite:///user_details.db'  # Secondary database URI for user details
}


db = SQLAlchemy(model_class=Base)
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    details = db.relationship('Details', backref='user', lazy=True)


class Details(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String(10000), nullable=True)
    status: Mapped[str] = mapped_column(String(1000), nullable=True)


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == "POST":
        email = request.form.get('email')
        result = db.session.execute(db.select(User).where(User.email == email))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        user = User(
            email=request.form.get('email'),
            password=hash_and_salted_password,
            name=request.form.get('name'),
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("home"))
        # return render_template('secrets.html', name=request.form.get('name'))
        # return render_template('secrets.html', nam=db.session.execute(db.select(User.name)).scalar())
    return render_template("signup.html")


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()

        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Check stored password hash against entered password hashed.
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('task'))
    return render_template('login.html')


@app.route('/task', methods=['GET', 'POST'])
@login_required
def task():
    return render_template('taskindex.html',logged_in=current_user.is_authenticated)


@app.route('/createtask', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        new_detail = Details(
            user_id=current_user.id,  # Associate with the current user
            title=request.form['title'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            description=request.form['description'],
            status=request.form['status']
        )
        db.session.add(new_detail)  # Add a new entry to the session
        db.session.commit()
        return redirect(url_for("task"))
    return render_template('create.html',logged_in=current_user.is_authenticated)


@app.route('/view', methods=['POST', 'GET'])
@login_required
def view():
    user_selected = User.query.get(current_user.id)
    user_details = Details.query.filter(Details.user_id == current_user.id).all()
    # if request.method == 'POST':
    #     return redirect(url_for('edit', id=user_details.id))
    return render_template('view.html', user=user_selected, det=user_details,logged_in=current_user.is_authenticated)


@app.route('/update', methods=['POST','GET'])
@login_required
def update():
    details_id = request.args.get('id')
    details_selected = Details.query.get(details_id)
    if request.method == "POST":  # Ensure "POST" is uppercase
        id = request.form['id']
        movie_to_update = db.get_or_404(Details, id)
        movie_to_update.title = request.form['title'] or movie_to_update.title
        movie_to_update.status = request.form['status'] or movie_to_update.status
        movie_to_update.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        movie_to_update.description = request.form['description'] or movie_to_update.description
        db.session.commit()
        return redirect(url_for('task'))
    return render_template('edit.html', selected=details_selected,logged_in=current_user.is_authenticated)


@app.route('/delete', methods=['POST','GET'])
def delete():
    details_id = request.args.get('id')  # Get the details_id from the URL
    details_selected = Details.query.get(details_id)  # Fetch the record by ID
        # Delete the record
    db.session.delete(details_selected)
    db.session.commit()  # Commit the deletion to the database

    return redirect(url_for('task'))  # Redirect to another page after deletion


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    logout_user()
    return redirect(url_for('home'))




if __name__ == '__main__':
    app.run(debug=True)