from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required
from models import db, Book, User, Review
from auth import check_rights


bp = Blueprint('reviews', __name__, url_prefix='/reviews')


@bp.route('/<int:book_id>/new_review', methods=['GET', 'POST'])
@login_required
@check_rights('review')
def new_review(book_id):
    user_review = Review.query.filter_by(id = current_user.id).filter_by(book_id=book_id).all()
    if request.method == "POST":
        if not user_review:
            params = {
                    'book_id': book_id,
                    'user_id': current_user.id,
                    'rating': request.form.get('rating'),
                    'text': request.form.get('text'),
                }
            review = Review(**params)
            review.prepare_to_save()
            try:
                book = Book.query.filter_by(id = book_id).first()
                book.rating_num += 1
                book.rating_sum += int(params['rating'])
                db.session.add(book)
                db.session.add(review)
                db.session.commit()
                flash('Рецензия опубликована!', 'success')
            except:
                db.session.rollback()
                flash('Возникла ошибка при обращении к БД', 'warning')
                return render_template('reviews/new_edit.html', book_id = book_id)
        else:
            flash('Вы уже оставили рецензию к этой книге', 'warning')
            return redirect(url_for('show', book_id = book_id))

    return render_template('reviews/new_edit.html', book_id = book_id, user_review = user_review)


