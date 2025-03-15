from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Book, Member, Rental
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

load_dotenv()


app = Flask(__name__)
connection_string = "mssql+pyodbc://DESKTOP-TFIS1IE\\SQLEXPRESS/ProjetoImpacta?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '1234'
db.init_app(app)

@app.template_filter('br_datetime')
def br_datetime(value):
    if value is None:
        return '-'
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return value.strftime('%d/%m/%Y %H:%M:%S')

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rentals', methods=['GET', 'POST'])
def rentals():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_rental':
            book_id = request.form['book_id']
            member_id = request.form['member_id']
            book = Book.query.get(book_id)
            member = Member.query.get(member_id)
            if not book or not member:
                flash('Livro ou membro não encontrado!')
            elif book.status != 'available':
                flash('Este livro já está alugado!')
            else:
                try:
                    rental = Rental(
                        book_id=book_id,
                        member_id=member_id,
                        rent_date=datetime.utcnow(),
                        return_date=datetime.utcnow() + timedelta(days=14)
                    )
                    book.status = 'rented'
                    db.session.add(rental)
                    db.session.commit()
                    flash('Livro alugado com sucesso!')
                except IntegrityError:
                    db.session.rollback()
                    flash('Erro ao alugar o livro: dados inválidos!')
        elif action == 'edit_rental':
            rental_id = request.form['rental_id']
            rental = Rental.query.get_or_404(rental_id)
            if rental.actual_return_date is None:
                new_return_date = datetime.strptime(request.form['return_date'], '%Y-%m-%d')
                today = datetime.utcnow().date()
                if new_return_date.date() < today:
                    flash('A nova data de devolução não pode ser anterior a hoje!')
                else:
                    rental.return_date = new_return_date
                    db.session.commit()
                    flash('Data de devolução do aluguel atualizada com sucesso!')
            else:
                flash('Não é possível editar um aluguel já devolvido!')
        elif action == 'return_rental':
            rental_id = request.form['rental_id']
            rental = Rental.query.get_or_404(rental_id)
            if rental.actual_return_date is None:
                rental.actual_return_date = datetime.utcnow()
                rental.fine_amount = rental.calculate_fine()
                rental.book.status = 'available'
                db.session.commit()
                flash(f'Livro devolvido. Multa: R$ {rental.fine_amount:.2f}'.replace('.', ','))
            else:
                flash('Este aluguel já foi devolvido!')
        return redirect(url_for('rentals', page=request.args.get('page', 1), per_page=request.args.get('per_page', 10)))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = min(max(per_page, 5), 20)
    ongoing_rentals_paginated = Rental.query.filter_by(actual_return_date=None).order_by(Rental.id).paginate(page=page, per_page=per_page, error_out=False)
    rentals_data = [
        {
            'id': rental.id,
            'book_title': rental.book.title,
            'member_name': rental.member.name,
            'rent_date': (rental.rent_date if isinstance(rental.rent_date, datetime)
                         else datetime.strptime(rental.rent_date, '%Y-%m-%d %H:%M:%S')).strftime('%d/%m/%Y %H:%M:%S'),
            'return_date': (rental.return_date if isinstance(rental.return_date, datetime)
                           else datetime.strptime(rental.return_date, '%Y-%m-%d')).strftime('%Y-%m-%d')
        }
        for rental in ongoing_rentals_paginated.items
    ]
    books = Book.query.filter_by(status='available').all()
    members = Member.query.all()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('rentals.html', rentals_data=rentals_data, books=books, members=members, today=today,
                           pagination=ongoing_rentals_paginated, per_page=per_page)

@app.route('/view_books', methods=['GET', 'POST'])
def view_books():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_book':
            isbn = request.form['isbn']
            if Book.query.filter_by(isbn=isbn).first():
                flash('Já existe um livro com este ISBN!')
            else:
                try:
                    book = Book(
                        title=request.form['title'],
                        author=request.form['author'],
                        isbn=isbn,
                        genero=request.form['genero']  # New field
                    )
                    db.session.add(book)
                    db.session.commit()
                    flash('Livro adicionado com sucesso!')
                except IntegrityError:
                    db.session.rollback()
                    flash('Erro ao adicionar livro: dados inválidos!')
        elif action == 'edit_book':
            book_id = request.form['book_id']
            book = Book.query.get_or_404(book_id)
            isbn = request.form['isbn']
            if isbn != book.isbn and Book.query.filter_by(isbn=isbn).first():
                flash('Já existe outro livro com este ISBN!')
            else:
                try:
                    book.title = request.form['title']
                    book.author = request.form['author']
                    book.isbn = isbn
                    book.genero = request.form['genero']  # New field
                    db.session.commit()
                    flash('Livro editado com sucesso!')
                except IntegrityError:
                    db.session.rollback()
                    flash('Erro ao editar livro: dados inválidos!')
        elif action == 'delete_book':
            book_id = request.form['book_id']
            book = Book.query.get_or_404(book_id)
            if book.status == 'rented':
                flash('Não é possível excluir um livro que está alugado!')
            else:
                db.session.delete(book)
                db.session.commit()
                flash('Livro excluído com sucesso! Todos os registros de aluguel associados foram removidos.')
        return redirect(url_for('view_books', page=request.args.get('page', 1), per_page=request.args.get('per_page', 10)))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = min(max(per_page, 5), 20)
    books_paginated = Book.query.order_by(Book.id).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('view_books.html', books=books_paginated.items, current_date=datetime.utcnow(),
                           pagination=books_paginated, per_page=per_page)

@app.route('/view_members', methods=['GET', 'POST'])
def view_members():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_member':
            email = request.form['email']
            if Member.query.filter_by(email=email).first():
                flash('Já existe um membro com este e-mail!')
            else:
                try:
                    member = Member(
                        name=request.form['name'],
                        email=email
                    )
                    db.session.add(member)
                    db.session.commit()
                    flash('Membro registrado com sucesso!')
                except IntegrityError:
                    db.session.rollback()
                    flash('Erro ao registrar membro: dados inválidos!')
        elif action == 'edit_member':
            member_id = request.form['member_id']
            member = Member.query.get_or_404(member_id)
            email = request.form['email']
            if email != member.email and Member.query.filter_by(email=email).first():
                flash('Já existe outro membro com este e-mail!')
            else:
                try:
                    member.name = request.form['name']
                    member.email = email
                    db.session.commit()
                    flash('Membro editado com sucesso!')
                except IntegrityError:
                    db.session.rollback()
                    flash('Erro ao editar membro: dados inválidos!')
        elif action == 'delete_member':
            member_id = request.form['member_id']
            member = Member.query.get_or_404(member_id)
            db.session.delete(member)
            db.session.commit()
            flash('Membro excluído com sucesso! Todos os registros de aluguel associados foram removidos.')
        return redirect(url_for('view_members', page=request.args.get('page', 1), per_page=request.args.get('per_page', 10)))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = min(max(per_page, 5), 20)
    members_paginated = Member.query.order_by(Member.id).paginate(page=page, per_page=per_page, error_out=False)
    members_data = [
        {
            'id': member.id,
            'name': member.name,
            'email': member.email,
            'has_active_rentals': any(rental.actual_return_date is None for rental in member.rentals)
        }
        for member in members_paginated.items
    ]
    return render_template('view_members.html', members_data=members_data, pagination=members_paginated, per_page=per_page)

@app.route('/rental_history')
def rental_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = min(max(per_page, 5), 20)
    rentals_paginated = Rental.query.order_by(Rental.id).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('rental_history.html', rentals=rentals_paginated.items, pagination=rentals_paginated, per_page=per_page)

if __name__ == '__main__':
    app.run(debug=True)