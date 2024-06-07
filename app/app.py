from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, send_from_directory,abort
from auth import bp as auth_bp, init_login_manager, check_rights
from flask_migrate import Migrate
from models import db, Book, Genre, Image
from flask_login import login_required
from tools import ImageSaver, extract_params


app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

db.init_app(app)
migrate = Migrate(app, db)

init_login_manager(app)

app.register_blueprint(auth_bp)



@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    books = Book.query.order_by(Book.id.desc())
    pagination = books.paginate(page=page, per_page=app.config['PER_PAGE'])
    genres = Genre.query.all()
    books = pagination.items
    book = None
    return render_template("index.html", pagination=pagination, books=books, book=book, genres = genres)


@app.route('/images/<image_id>')
def image(image_id):
    img = Image.query.get(image_id)
    if img is None:
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               img.file_name)

BOOKS_PARAMS = [
    'name', 'author', 'publisher', 'year_release', 'pages_volume',
    'short_desc',
]


@app.route('/new', methods=["POST", "GET"])
@login_required
@check_rights('create')
def new():
    if request.method == "POST":
        f = request.files.get('background_img')
        if f and f.filename:
            img = ImageSaver(f).save()
            params = extract_params(BOOKS_PARAMS)
            params['year_release'] = int(params['year_release'])
            params['pages_volume'] = int(params['pages_volume'])
            genres = request.form.getlist('genres')
            genres_list = []
            for i in genres:
                genre = Genre.query.filter_by(id=i).first()
                if genre:
                    genres_list.append(genre)
                else:
                    flash(f'Жанр с id {i} не найден', 'danger')

            book = Book(**params, image_id=img.id)
            book.prepare_to_save() 
            book.genres = genres_list
            try:
                db.session.add(book)
                db.session.commit()
                flash('Книга успешно добавлена', 'success')
                return redirect(url_for('new'))
            except Exception as e:
                db.session.rollback()
                flash(f'При сохранении данных возникла ошибка: {e}', 'danger')
        else:
            flash('У книги должна быть обложка', 'danger')
    
    genres = Genre.query.all()
    return render_template('books/new_edit.html',
                           action_category='create',
                           genres=genres,
                           book={})