import operator
from typing import Any, Callable, Dict, Type

from nodes import (
    AssignExpr,
    BinaryExpr,
    CallExpr,
    Expr,
    FieldGetExpr,
    FieldSetExpr,
    GroupingExpr,
    IndexGetExpr,
    IndexSetExpr,
    InstanceOfExpr,
    LiteralExpr,
    LogicalExpr,
    SuperExpr,
    ThisExpr,
    UnaryExpr,
    VariableExpr,
)
from nodes.token_type import TokenType
from ._storage import Storage
from ._callable import LoxCallable
from ._array import FabArray, _parse_integer_value
from ._class import LoxClass, LoxInstance
from ._namespace import LoxNamespace
from .errors import (
    ArityMismatchError,
    DivideByZeroError,
    ExecutionError,
    IndexOutOfRangeError,
    InvalidIndexTypeError,
    NotAClassError,
    NotAnArrayError,
    NotAnInstanceError,
    NotCallableError,
    StackOverflowError,
    TypeMismatchError,
    UndefinedPropertyError,
    UndefinedVariableError,
)


def _is_number(value: Any) -> bool:
    # bool은 int의 서브클래스라서 True/False가 숫자로 오인되지 않도록 따로 걸러낸다.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_number_operand(value: Any, token) -> None:
    if not _is_number(value):
        raise TypeMismatchError("피연산자는 반드시 숫자여야 합니다.", token)


def _check_number_operands(left: Any, right: Any, token) -> None:
    if not _is_number(left) or not _is_number(right):
        raise TypeMismatchError("피연산자는 반드시 숫자여야 합니다.", token)


def _is_string(value: Any) -> bool:
    return isinstance(value, str)


def _evaluate_literal(expr: LiteralExpr, storage: Storage) -> Any:
    return expr.value


def _evaluate_variable(expr: VariableExpr, storage: Storage) -> Any:
    try:
        return storage.get_resolved(expr, expr.name.lexeme)
    except UndefinedVariableError as e:
        e.token = expr.name
        raise


def _evaluate_assign(expr: AssignExpr, storage: Storage) -> Any:
    value = evaluate(expr.value, storage)
    try:
        storage.set_resolved(expr, expr.name.lexeme, value)
    except UndefinedVariableError as e:
        e.token = expr.name
        raise
    return value


def _evaluate_grouping(expr: GroupingExpr, storage: Storage) -> Any:
    return evaluate(expr.expression, storage)


def _evaluate_unary(expr: UnaryExpr, storage: Storage) -> Any:
    right = evaluate(expr.right, storage)
    if expr.operator.type == TokenType.MINUS:
        _check_number_operand(right, expr.operator)
        return -right
    if expr.operator.type == TokenType.PLUS:
        _check_number_operand(right, expr.operator)
        return right
    if expr.operator.type == TokenType.BANG:
        return not right
    raise TypeMismatchError(f"지원하지 않는 단항 연산자 '{expr.operator.lexeme}'", expr.operator)


def _evaluate_logical(expr: LogicalExpr, storage: Storage) -> Any:
    left = evaluate(expr.left, storage)
    if expr.operator.type == TokenType.OR:
        if left:
            return left
        return evaluate(expr.right, storage)
    # AND: 왼쪽이 falsy면 오른쪽을 평가하지 않고 그대로 반환한다 (단축 평가).
    if not left:
        return left
    return evaluate(expr.right, storage)


# SLASH/PERCENT는 0으로 나누기 검사가 별도로 필요해서 이 dict에는 넣지 않고 따로 처리한다.
# EQUAL_EQUAL/BANG_EQUAL도 숫자 여부와 무관하게 항상 비교 가능해야 하므로 따로 처리한다.
_NUMERIC_BINARY_OPS: Dict[TokenType, Callable[[Any, Any], Any]] = {
    TokenType.PLUS: operator.add,
    TokenType.MINUS: operator.sub,
    TokenType.STAR: operator.mul,
    TokenType.GREATER: operator.gt,
    TokenType.LESS: operator.lt,
    TokenType.GREATER_EQUAL: operator.ge,
    TokenType.LESS_EQUAL: operator.le,
    # EQUAL_GREATER("=>")/EQUAL_LESS("=<")는 GREATER_EQUAL/LESS_EQUAL과 의미가 같은 별칭 토큰이다.
    TokenType.EQUAL_GREATER: operator.ge,
    TokenType.EQUAL_LESS: operator.le,
}

_EQUALITY_OPS: Dict[TokenType, Callable[[Any, Any], Any]] = {
    TokenType.EQUAL_EQUAL: operator.eq,
    TokenType.BANG_EQUAL: operator.ne,
}


def _evaluate_binary(expr: BinaryExpr, storage: Storage) -> Any:
    left = evaluate(expr.left, storage)
    right = evaluate(expr.right, storage)
    op = expr.operator.type

    if op == TokenType.SLASH:
        _check_number_operands(left, right, expr.operator)
        if right == 0:
            raise DivideByZeroError("0으로 나눌 수 없습니다.", expr.operator)
        return left / right

    if op == TokenType.PERCENT:
        _check_number_operands(left, right, expr.operator)
        if right == 0:
            raise DivideByZeroError("0으로 나눈 나머지를 구할 수 없습니다.", expr.operator)
        return left % right

    if op == TokenType.PLUS and _is_string(left) and _is_string(right):
        return left + right

    equality_op = _EQUALITY_OPS.get(op)
    if equality_op is not None:
        return equality_op(left, right)

    numeric_op = _NUMERIC_BINARY_OPS.get(op)
    if numeric_op is None:
        raise TypeMismatchError(f"지원하지 않는 이항 연산자 '{expr.operator.lexeme}'", expr.operator)
    _check_number_operands(left, right, expr.operator)
    return numeric_op(left, right)


def _evaluate_call(expr: CallExpr, storage: Storage) -> Any:
    # 호출 대상이 Function이든 이후 추가될 class의 생성자/메서드든, Callable
    # 인터페이스(arity/call)만 보고 처리한다 (Command/Strategy 패턴).
    callee = evaluate(expr.callee, storage)
    if not isinstance(callee, LoxCallable):
        raise NotCallableError(expr.paren)

    arguments = [evaluate(argument, storage) for argument in expr.arguments]
    if len(arguments) != callee.arity():
        raise ArityMismatchError(callee.arity(), len(arguments), expr.paren)

    try:
        return callee.call(storage, arguments)
    except ExecutionError as e:
        if e.token is None:
            e.token = expr.paren
        raise
    except RecursionError:
        raise StackOverflowError(expr.paren) from None


def _check_integer_index(value: Any, token) -> int:
    """배열 인덱스 값이 정수 숫자인지 검사하고 int로 변환한다."""
    return _parse_integer_value(value, "인덱스", InvalidIndexTypeError, token)


def _evaluate_this(expr: ThisExpr, storage: Storage) -> Any:
    try:
        return storage.get("this")
    except UndefinedVariableError as e:
        e.token = expr.keyword
        raise


def _evaluate_field_get(expr: FieldGetExpr, storage: Storage) -> Any:
    obj = evaluate(expr.object, storage)
    if not isinstance(obj, (LoxInstance, LoxNamespace)):
        raise NotAnInstanceError(expr.name)
    return obj.get(expr.name)


def _evaluate_field_set(expr: FieldSetExpr, storage: Storage) -> Any:
    obj = evaluate(expr.object, storage)
    if not isinstance(obj, LoxInstance):
        raise NotAnInstanceError(expr.name)
    value = evaluate(expr.value, storage)
    obj.set(expr.name, value)
    return value


def _evaluate_super(expr: SuperExpr, storage: Storage) -> Any:
    # __class__는 Function.call()이 메서드 호출 시 심어주는 owner_class다.
    # 다단계 상속에서도 정의된 클래스 기준으로 부모를 찾아야 하므로
    # 인스턴스 런타임 타입이 아니라 __class__.superclass를 기준으로 한다.
    try:
        owner_class = storage.get("__class__")
    except UndefinedVariableError as e:
        e.token = expr.keyword
        raise
    this = storage.get("this")
    superclass = owner_class.superclass
    if superclass is None:
        raise UndefinedPropertyError(expr.method.lexeme, expr.keyword)
    method = superclass.find_method(expr.method.lexeme)
    if method is None:
        raise UndefinedPropertyError(expr.method.lexeme, expr.method)
    return method.bind(this)


def _evaluate_instanceof(expr: InstanceOfExpr, storage: Storage) -> bool:
    obj = evaluate(expr.object, storage)
    klass = evaluate(expr.class_name, storage)
    if not isinstance(klass, LoxClass):
        raise NotAClassError(expr.keyword)
    if not isinstance(obj, LoxInstance):
        return False
    # 상속 체인을 따라 올라가며 일치하는 클래스를 찾는다 (Chain of Responsibility 패턴).
    current = obj.klass
    while current is not None:
        if current is klass:
            return True
        current = current.superclass
    return False


def _resolve_array_access(obj: Any, idx_val: Any, bracket) -> tuple:
    """배열 타입·인덱스 타입·범위를 한 번에 검사하고 (FabArray, int)를 반환한다."""
    if not isinstance(obj, FabArray):
        raise NotAnArrayError(
            f"[] 연산은 배열에만 사용할 수 있습니다. (받은 값: {obj!r})", bracket
        )
    idx = _check_integer_index(idx_val, bracket)
    if idx < 0 or idx >= len(obj):
        raise IndexOutOfRangeError(
            f"인덱스 {idx}는 배열 범위(0~{len(obj) - 1})를 벗어났습니다.", bracket
        )
    return obj, idx


def _evaluate_index_get(expr: IndexGetExpr, storage: Storage) -> Any:
    obj, idx = _resolve_array_access(
        evaluate(expr.object, storage),
        evaluate(expr.index, storage),
        expr.bracket,
    )
    return obj.get(idx)


def _evaluate_index_set(expr: IndexSetExpr, storage: Storage) -> Any:
    obj, idx = _resolve_array_access(
        evaluate(expr.object, storage),
        evaluate(expr.index, storage),
        expr.bracket,
    )
    value = evaluate(expr.value, storage)
    obj.set(idx, value)
    return value


_EXPR_EVALUATORS: Dict[Type[Expr], Callable[[Any, Storage], Any]] = {
    LiteralExpr: _evaluate_literal,
    VariableExpr: _evaluate_variable,
    AssignExpr: _evaluate_assign,
    GroupingExpr: _evaluate_grouping,
    UnaryExpr: _evaluate_unary,
    LogicalExpr: _evaluate_logical,
    BinaryExpr: _evaluate_binary,
    CallExpr: _evaluate_call,
    ThisExpr: _evaluate_this,
    FieldGetExpr: _evaluate_field_get,
    FieldSetExpr: _evaluate_field_set,
    SuperExpr: _evaluate_super,
    InstanceOfExpr: _evaluate_instanceof,
    IndexGetExpr: _evaluate_index_get,
    IndexSetExpr: _evaluate_index_set,
}


def evaluate(expr: Expr, storage: Storage) -> Any:
    """Expr 트리를 재귀적으로 평가해 값 하나를 반환한다."""
    handler = _EXPR_EVALUATORS.get(type(expr))
    if handler is None:
        raise NotImplementedError(f"{type(expr).__name__} 평가는 아직 구현되지 않았습니다.")
    return handler(expr, storage)


def stringify(value: Any) -> str:
    """print 출력 / 오류 메시지에 쓸 문자열 표현을 만든다.

    정수 값을 갖는 float(예: 5.0)은 "5.0"이 아닌 "5"로 표시한다.
    (PDF p.77 실행 예시 "print(5) 출력" 참고)
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, FabArray):
        items = ", ".join(stringify(value.get(i)) for i in range(len(value)))
        return f"[{items}]"
    return str(value)
