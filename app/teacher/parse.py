import fractions
import re

class ParseError(Exception):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(ParseError, self).__init__(message)


class PolynomialExpression(object):
    def __init__(self, coefficients):
        self.coefficients = tuple(coefficients)
        self.degree = len(self.coefficients) - 1

    def add(self, polyexp):
        if self.degree > polyexp.degree:
            summed_coefficients = list(self.coefficients)
            for i, coef in enumerate(polyexp.coefficients):
                summed_coefficients[i] += coef
        else:
            summed_coefficients = list(polyexp.coefficients)
            for i, coef in enumerate(self.coefficients):
                summed_coefficients[i] += coef

        return PolynomialExpression(summed_coefficients)

    def scale(self, number):
        return PolynomialExpression(coef * number for coef in self.coefficients)

    def mult(self, polyexp):
        multiplied_coefficients = [0] * (self.degree + polyexp.degree + 1)
        for i, coef_1 in enumerate(self.coefficients):
            for j, coef_2 in enumerate(polyexp.coefficients):
                multiplied_coefficients[i + j] += coef_1 * coef_2
        return PolynomialExpression(multiplied_coefficients)

    def __repr__(self):
        result = ''
        for i, coef in enumerate(self.coefficients):
            if result:
                result += ' + '
            result += str(coef) + 'x^' + str(i)
        return result


def parse_equation(equation):
    eq_no_white_space = ''.join(equation.split())
    variable = None
    for char in eq_no_white_space:
        if char.isalpha():
            if variable is None:
                variable = char
            elif variable != char:
                raise ParseError('Equation may only contain one type of variable, ' +
                                 'but contained {0} and {1}'.format(variable, char))
            elif not (char.isalpha() or char.isdigit()
                      or char in ['+', '-', '*', '=', '(', ')']):
                raise ParseError('Equation contains an illegal character: {}'\
                                 .format(char))
    sides = eq_no_white_space.split('=')
    if len(sides) < 2:
        raise ParseError('Equation must contain an equals sign')
    if len(sides) > 2:
        raise ParseError('Equation can only contain one equals sign')
    left_side, right_side = sides
    if len(left_side) == 0:
        raise ParseError('Left side of equation has no content')
    if len(right_side) == 0:
        raise ParseError('Right side of equation has no content')

    try:
        left_expression = parse_expression(left_side)
    except ParseError as e:
        raise ParseError('Left Side: ' + e.message)
    try:
        right_expression = parse_expression(right_side)
    except ParseError as e:
        raise ParseError('Right Side: ' + e.message)
    if left_expression.degree > 1:
        raise ParseError('Left side of equation is not linear. ' +
                         'The exponent of the variable is greater than 1.')
    elif right_expression.degree > 1:
        raise ParseError('Right side of equation is not linear. ' +
                         'The exponent of the variable is greater than 1.')

    if left_expression.degree == 1:
        left_coefficient = left_expression.coefficients[1]
    else:
        left_coefficient = 0
    left_constant = left_expression.coefficients[0]
    if right_expression.degree == 1:
        right_coefficient = right_expression.coefficients[1]
    else:
        right_coefficient = 0
    right_constant = right_expression.coefficients[0]

    solution_numerator = right_constant - left_constant
    solution_denominator = left_coefficient - right_coefficient
    solution_gcd = fractions.gcd(solution_numerator, solution_denominator)
    if solution_gcd * solution_denominator < 0:
        solution_gcd *= -1
    solution_numerator /= solution_gcd
    solution_denominator /= solution_gcd
    left_side_numerator = left_coefficient * solution_numerator + left_constant * solution_denominator
    left_side_denominator = solution_denominator
    left_side_gcd = fractions.gcd(left_side_numerator, left_side_denominator)
    if left_side_gcd * left_side_denominator < 0:
        left_side_gcd *= -1
    left_side_numerator /= left_side_gcd
    left_side_denominator /= left_side_gcd

    return {'text': equation,
            'left_coefficient': left_coefficient,
            'left_constant': left_constant,
            'right_coefficient': right_coefficient,
            'right_constant': right_constant,
            'solution_numerator': solution_numerator,
            'solution_denominator': solution_denominator,
            'left_side_numerator': left_side_numerator,
            'left_side_denominator': left_side_denominator
            }


def parse_expression(expression):
    pattern = re.compile(r'^[A-Za-z0-9+*()-]')
    if not pattern.match(expression):
        raise ParseError('Expression contains illegal characters. Only digits, ' +
                         'variables, and + - * ( )')
    zero = PolynomialExpression([0])
    one = PolynomialExpression([1])
    x = PolynomialExpression([0, 1])
    current_sum = zero
    stashed_sums = []
    current_product = one
    stashed_products = []
    num_unbalanced_left_parens = 0
    digit_location = None
    previous_char = None
    for i, char in enumerate(expression):
        if previous_char is None:
            if char in [')', '+', '*']:
                raise ParseError("Can't start an expression with " + char)
            if char == '-':
                current_product = current_product.scale(-1)
            previous_char = char
            continue
        if char == '(':
            num_unbalanced_left_parens += 1
            stashed_sums.append(current_sum)
            current_sum = zero
            if previous_char.isalpha():
                current_product = current_product.mult(x)
            elif previous_char.isdigit():
                current_product = current_product.scale(int(expression[digit_location:i]))
                digit_location = None
            stashed_products.append(current_product)
            current_product = one
            last_unprocessed_char = i + 1
        elif char == ')':
            num_unbalanced_left_parens -= 1
            if num_unbalanced_left_parens < 0:
                raise ParseError('The parentheses are not balanced')
            if previous_char in ['+', '-', '*', '(']:
                raise ParseError('Illegal character sequence: ' + previous_char + char)
            if previous_char.isalpha():
                current_product = current_product.mult(x)
            elif previous_char.isdigit():
                current_product = current_product.scale(int(expression[digit_location:i]))
                digit_location = None
            current_sum = current_sum.add(current_product)
            current_product = stashed_products.pop().mult(current_sum)
            current_sum = stashed_sums.pop()
        elif char == '+':
            if previous_char in ['(', '+', '-', '*']:
                raise ParseError('Illegal character sequence: ' + previous_char + char)
            if previous_char.isalpha():
                current_product = current_product.mult(x)
            elif previous_char.isdigit():
                current_product = current_product.scale(int(expression[digit_location:i]))
                digit_location = None
            current_sum = current_sum.add(current_product)
            current_product = one
        elif char == '-':
            if previous_char.isalpha():
                current_product = current_product.mult(x)
                current_sum = current_sum.add(current_product)
                current_product = one.scale(-1)
            elif previous_char.isdigit():
                current_product = current_product.scale(int(expression[digit_location:i]))
                digit_location = None
                current_sum = current_sum.add(current_product)
                current_product = one.scale(-1)
            elif previous_char == ')':
                current_sum = current_sum.add(current_product)
                current_product = one.scale(-1)
            elif previous_char in ['-', '+', '(', '*']:
                current_product = current_product.scale(-1)
        elif char == '*':
            if previous_char in ['+', '*', '-', '(']:
                raise ParseError('Illegal character sequence: ' + previous_char + char)
            elif previous_char.isalpha():
                current_product = current_product.mult(x)
            elif previous_char.isdigit():
                current_product = current_product.scale(int(expression[digit_location:i]))
                digit_location = None
        elif char.isalpha():
            if previous_char == ')':
                raise ParseError('Illegal character sequence: ' + previous_char + char)
            if previous_char.isalpha():
                current_product = current_product.mult(x)
            elif previous_char.isdigit():
                current_product = current_product.scale(int(expression[digit_location:i]))
                digit_location = None
        elif char.isdigit():
            if previous_char == ')' or previous_char.isalpha():
                raise ParseError('Illegal character sequence: ' + previous_char + char)
            if digit_location is None:
                digit_location = i
#         print 'prev char: %s' % previous_char
#         print 'cs: %s' % current_sum
#         print 'cp: %s' % current_product
#         print 'ss: %s' % stashed_sums
#         print 'sp: %s' % stashed_products
        previous_char = char
    if previous_char.isalpha():
        current_product = current_product.mult(x)
    elif previous_char.isdigit():
        current_product = current_product.scale(int(expression[digit_location:]))
    elif previous_char in ['+', '-', '*', '(']:
        raise ParseError("Can't end an expression with " + previous_char)
    if num_unbalanced_left_parens != 0:
        raise ParseError('The parentheses are not balanced')
    current_sum = current_sum.add(current_product)
    return current_sum