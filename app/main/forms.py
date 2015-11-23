from flask.ext.wtf import Form
from wtforms import StringField, BooleanField, SelectField,SubmitField
from wtforms.validators import Required, Length, Email
from wtforms import ValidationError
from ..models import Role, User


class EditProfileForm(Form):
    first_name = StringField('First Name', validators=[Length(1, 64)])
    last_name = StringField('Last Name', validators=[Length(0, 64)])
    submit = SubmitField('Submit')


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    first_name = StringField('First Name', validators=[Length(1, 64)])
    last_name = StringField('Last Name', validators=[Length(0, 64)])
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')