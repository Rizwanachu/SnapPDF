from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(), 
        Length(min=2, max=50)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(), 
        Length(min=2, max=50)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Create Account')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    submit = SubmitField('Sign In')