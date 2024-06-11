from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, send_from_directory,abort,session
from auth import bp as auth_bp, init_login_manager, check_rights
from flask_migrate import Migrate
from models import db, Book, Genre, Image, Review, AllBookVisits, LastBookVisits
from flask_login import login_required, current_user
from tools import ImageSaver, extract_params
import os
from reviews import bp as reviews_bp
# from visits import bp as visits_bp
from datetime import datetime, timedelta

app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

db.init_app(app)
migrate = Migrate(app, db)

init_login_manager(app)

app.register_blueprint(auth_bp)
app.register_blueprint(reviews_bp)
# app.register_blueprint(visits_bp)


def get_top_five():
    start = datetime.now() - timedelta(days=3 * 30)
    top_books = (db.session
                        .query(AllBookVisits.book_id, db.func.count(AllBookVisits.id))
                        .filter(start <= AllBookVisits.created_at)
                        .group_by(AllBookVisits.book_id)
                        .order_by(db.func.count(AllBookVisits.id).desc())
                        .limit(5).all())
    result = []
    for i, for_enum in enumerate(top_books):
        book = Book.query.get(top_books[i][0])
        result.append((book, top_books[i][1]))
    return result

def get_last_five():
    if current_user.is_authenticated:
        last_books = (LastBookVisits.query
                            .filter_by(user_id=current_user.id)
                            .order_by(LastBookVisits.created_at.desc())
                            .limit(5)
                            .all())
    else:
        last_books = session.get('last_books')
    result = []
    if current_user.is_authenticated:
        for book_visit in last_books:
            result.append(Book.query.get(book_visit.book_id))
    else:
        for book_visit in last_books:
            result.append(Book.query.get(book_visit))
    return result



@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    top_five_books = get_top_five()
    last_five_books = get_last_five()
    books = Book.query.order_by(Book.year_release.desc())
    pagination = books.paginate(page=page, per_page=app.config['PER_PAGE'])
    genres = Genre.query.all()
    books = pagination.items
    book = None
    return render_template("index.html", pagination=pagination, 
                           books=books, book=book, genres = genres,
                           top_books = top_five_books,
                           last_books = last_five_books)


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

def add_book_visit(book_id, user_id):
    try:
        visit_params = {
            'user_id' : user_id,
            'book_id' : book_id,
        }
        db.session.add(AllBookVisits(**visit_params))
        db.session.commit()
    except:
        db.session.rollback()

def last_visit_for_user(book_id, user_id):
    new_log = None
    
    last_log = LastBookVisits.query.filter_by(book_id=book_id).filter_by(user_id = current_user.id).first()
    if last_log:
        last_log.created_at = db.func.now()
    else:
        new_log = LastBookVisits(book_id = book_id, user_id = user_id)

        if new_log:
            try:
                db.session.add(new_log)
                db.session.commit()
            except:
                db.session.rollback()


def last_visit_for_anonim(book_id):
    data_from_cookies = session.get('last_books')
    if data_from_cookies:
        if book_id in data_from_cookies:
            data_from_cookies.remove(book_id)
            data_from_cookies.insert(0, book_id)
        else:
            data_from_cookies.insert(0, book_id)
    
    # Если логов не было
    if not data_from_cookies:
        data_from_cookies = [book_id]

    session['last_books'] = data_from_cookies

@app.before_request
def logger():
    if (request.endpoint == 'static'
        or request.endpoint == 'image'):
        return
    elif request.endpoint == 'show':
        user_id = getattr(current_user, 'id', None)
        book_id = request.view_args.get('book_id')

        if current_user.is_authenticated:
            last_visit_for_user(book_id, user_id)
        else:
            last_visit_for_anonim(book_id)

        start = datetime.now() - timedelta(days=1)
        this_day = AllBookVisits.query.filter_by(book_id = book_id).filter(AllBookVisits.created_at >= start)
        log_params = {
            'book_id': book_id,
            'user_id': user_id,
        }
        if current_user.is_authenticated:
            this_day = this_day.filter_by(
                user_id=current_user.get_id())
        else:
            this_day = this_day.filter(AllBookVisits.user_id.is_(None))
        
        if len(this_day.all()) < 10:
            db.session.add(AllBookVisits(**log_params))
            db.session.commit()
        else:
            db.session.rollback()