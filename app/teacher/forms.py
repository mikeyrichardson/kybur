from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import Required, Length, Regexp
from wtforms import ValidationError
import parse


class AddLessonForm(Form):
    name = StringField('Lesson Name', validators=[Required(), Length(1, 128)])
    submit = SubmitField('Add Lesson')


class AddProblemForm(Form):
    text = StringField('Equation', validators=[Required(), Length(3, 128),
                                               Regexp('^[ A-Za-z0-9+*()=-]+$', 0,
                                                      'Equation can only contain one type of variable, ' +
                                                      'integers, and the symbols + - * ( ) =')])
    submit = SubmitField('Add Problem')

    def validate_text(self, field):
        try:
            parse.parse_equation(field.data)
        except parse.ParseError as e:
            raise ValidationError(e.message)