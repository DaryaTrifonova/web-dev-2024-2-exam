from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, send_from_directory,abort
from auth import bp as auth_bp, init_login_manager, check_rights
from flask_migrate import Migrate
from models import db, Book, Genre, Image, Review
from flask_login import login_required, current_user
from tools import ImageSaver, extract_params
import os
from reviews import bp as reviews_bp


app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

db.init_app(app)
migrate = Migrate(app, db)

init_login_manager(app)

app.register_blueprint(auth_bp)
app.register_blueprint(reviews_bp)



@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    books = Book.query.order_by(Book.year_release.desc())
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
                return redirect(url_for('show', book_id = book.id))
            except Exception as e:
                db.session.rollback()
                flash(f'При сохранении данных возникла ошибка: {e}', 'danger')
        else:
            flash('У книги должна быть обложка', 'danger')
    
    genres = Genre.query.all()
    return render_template('books/new_edit.html',
                           action='create',
                           genres=genres,
                           book={})

@app.route('/edit/<int:book_id>', methods=["POST", "GET"])
@login_required
@check_rights('edit')
def edit(book_id):
    if request.method == "POST":
        params = extract_params(BOOKS_PARAMS)
        params['year_release'] = int(params['year_release'])
        params['pages_volume'] = int(params['pages_volume'])
        genres = request.form.getlist('genres')
        genres_list = []
        book = Book.query.get(book_id)
        book.name = params['name']
        book.author = params['author']
        book.publisher = params['publisher']
        book.year_release = params['year_release']
        book.pages_volume = params['pages_volume']
        book.short_desc = params['short_desc']

        for i in genres:
            genre = Genre.query.filter_by(id=i).first()
            genres_list.append(genre)
        book.genres = genres_list

        try:
            db.session.add(book)
            db.session.commit()
            flash('Книга успешно отредактирована', 'success')
            return redirect(url_for('show', book_id = book.id))
        except Exception as e:
            db.session.rollback()
            flash(f'При сохранении данных возникла ошибка: {e}', 'danger')
    
    book = Book.query.get(book_id)
    genres = Genre.query.all()
    return render_template('books/new_edit.html',
                           action='edit',
                           genres=genres,
                           book=book)

@app.route('/delete/<int:book_id>', methods=["POST"])
@login_required
@check_rights('delete')
def delete(book_id):

    book = Book.query.get(book_id)
    books_with_img = len(Book.query.filter_by(image_id=book.image.id).all())
    try:
        db.session.delete(book)

        if books_with_img == 1:
                image = Image.query.get(book.image.id)
                delete_path = os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    image.file_name)
                db.session.delete(image)
                os.remove(delete_path)

        db.session.commit()
        flash('Удаление книги прошло успешно', 'success')
    except:
        db.session.rollback()
        flash('Во время удаления книги произошла ошибка', 'danger')

    return redirect(url_for('index'))


@app.route('/<int:book_id>')
def show(book_id):
    book = Book.query.get(book_id)
    book.prepare_to_html()

    reviews = Review.query.filter_by(book_id=book_id)
    user_review = None
    for review in reviews:
        review = review.prepare_to_html()
    if current_user.get_id():
        user_review = reviews.filter_by(user_id = current_user.id).first()
    reviews.all()

    return render_template('books/show.html',
                           book=book,
                           user_review = user_review,
                           reviews = reviews)

