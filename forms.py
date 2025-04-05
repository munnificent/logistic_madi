"""
forms.py

Хранит определения форм для валидации вводимых данных (Flask-WTF / WTForms).
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField, IntegerField, HiddenField
)
from wtforms.validators import DataRequired, Email, Length, Optional

# ----------------------
# ФОРМЫ
# ----------------------

class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(message="Введите логин")])
    password = PasswordField("Пароль", validators=[DataRequired(message="Введите пароль")])
    submit = SubmitField("Войти")

class TrainForm(FlaskForm):
    train_id = HiddenField()  # скрытое поле, если редактируем
    name = StringField("Название (№ поезда)", validators=[DataRequired(), Length(max=100)])
    departure_station = StringField("Начальная станция", validators=[Optional()])
    arrival_station = StringField("Конечная станция", validators=[Optional()])
    departure_time = StringField("Время отправления", validators=[Optional()]) 
    arrival_time = StringField("Время прибытия", validators=[Optional()])
    last_operation_station = StringField("Станция последней операции", validators=[Optional()])
    last_operation_time = StringField("Время последней операции", validators=[Optional()])
    distance_to_arrival = IntegerField("Расстояние до конечной станции (км)", validators=[Optional()])
    operation_desc = StringField("Описание операции (прибытие/отправление и т.д.)", validators=[Optional()])
    submit = SubmitField("Сохранить")

class CargoForm(FlaskForm):
    cargo_id = HiddenField()
    cargo_type = StringField("Тип груза", validators=[DataRequired(), Length(max=100)])
    train_id = IntegerField("ID поезда", validators=[Optional()])
    current_station = StringField("Текущая станция", validators=[Optional()])
    status = StringField("Статус", validators=[Optional()])
    last_stop_time = StringField("Время последней остановки", validators=[Optional()])
    next_station = StringField("Следующая станция", validators=[Optional()])
    distance_to_arrival = IntegerField("Расстояние до конечной (км)", validators=[Optional()])
    last_operation = StringField("Последняя операция", validators=[Optional()])
    submit = SubmitField("Сохранить")

class ContactForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(message="Введите ваше имя")])
    email = StringField("E-mail", validators=[DataRequired(), Email(message="Неверный формат email")])
    message = TextAreaField("Сообщение", validators=[DataRequired(message="Введите текст сообщения")])
    submit = SubmitField("Отправить")
