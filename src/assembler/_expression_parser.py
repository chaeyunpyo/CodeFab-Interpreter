from nodes.token_type import TokenType
from nodes import (
    AssignExpr,
    BinaryExpr,
    CallExpr,
    FieldGetExpr,
    FieldSetExpr,
    GroupingExpr,
    IndexGetExpr,
    IndexSetExpr,
    LiteralExpr,
    LogicalExpr,
    SuperExpr,
    ThisExpr,
    UnaryExpr,
    VariableExpr,
)

from .errors import InvalidAssignmentTargetError, UnexpectedTokenError


class ExpressionParser:
    """표현식 문법을 낮은 우선순위(대입)부터 높은 우선순위(primary)까지 순서대로 파싱한다.

    or/and/비교/항/인수 단계는 전부 "다음 우선순위를 먼저 파싱하고, 해당 단계의
    연산자가 나오는 동안 반복해서 묶는다"는 동일한 규칙(precedence climbing)을
    따른다. 그래서 각 단계를 별도 메서드로 나열하는 대신 느슨한 순서부터
    조여지는 순서로 _PRECEDENCE 표에 나열하고, _climb()이 그 표를 따라
    재귀적으로 다음 단계를 호출한다. 새 우선순위 단계가 필요하면 표에 한
    줄만 추가하면 되고, 기존 단계의 코드는 건드릴 필요가 없다.

    call()의 후위 연산자(`(`/`[`/`.`)와 assignment()의 대입 대상 변환도
    같은 원칙을 따른다 — "어떤 토큰/타입이 왔을 때 무엇을 할지"를 if/elif나
    isinstance 사슬 대신 표(_postfix_factories, _ASSIGNMENT_TARGET_FACTORIES)로
    표현해, 함수 호출/배열/필드 접근처럼 서로 다른 팀원이 손대는 문법이
    늘어나도 표에 한 줄만 추가하면 되게 한다(Strategy 패턴을 dict 기반
    조회로 적용한 것과 같다).
    """

    # (표현식 클래스, 그 단계의 연산자들). 앞쪽일수록 우선순위가 낮다(더 늦게 묶인다).
    _PRECEDENCE = (
        (LogicalExpr, (TokenType.OR,)),
        (LogicalExpr, (TokenType.AND,)),
        (
            BinaryExpr,
            (
                TokenType.GREATER,
                TokenType.LESS,
                TokenType.EQUAL_EQUAL,
                TokenType.BANG_EQUAL,
                TokenType.GREATER_EQUAL,
                TokenType.LESS_EQUAL,
                TokenType.EQUAL_LESS,
                TokenType.EQUAL_GREATER,
            ),
        ),
        (BinaryExpr, (TokenType.PLUS, TokenType.MINUS)),
        (BinaryExpr, (TokenType.STAR, TokenType.SLASH)),
    )
    _UNARY_OPERATORS = (TokenType.BANG, TokenType.MINUS, TokenType.PLUS)

    # 리터럴 토큰 -> LiteralExpr 생성 방법. 새 리터럴 타입이 추가되면 이 표에만 추가한다.
    _LITERAL_FACTORIES = {
        TokenType.NUMBER: lambda token: LiteralExpr(token.literal),
        TokenType.STRING: lambda token: LiteralExpr(token.literal),
        TokenType.TRUE: lambda token: LiteralExpr(True),
        TokenType.FALSE: lambda token: LiteralExpr(False),
    }

    # 대입 가능한(assignable) Expr 타입 -> 그 타입의 Get을 Set으로 바꾸는 방법.
    # 새로운 종류의 "읽기 Expr"가 대입 대상으로 추가되면 이 표에만 한 줄 추가하면 된다.
    _ASSIGNMENT_TARGET_FACTORIES = {
        VariableExpr: lambda expr, value: AssignExpr(name=expr.name, value=value),
        IndexGetExpr: lambda expr, value: IndexSetExpr(
            object=expr.object, bracket=expr.bracket, index=expr.index, value=value
        ),
        FieldGetExpr: lambda expr, value: FieldSetExpr(object=expr.object, name=expr.name, value=value),
    }

    def __init__(self, tokens):
        self.tokens = tokens
        # primary() 뒤에 붙는 후위 연산자 토큰 -> 그 연산자를 마저 파싱하는 메서드.
        # 새 후위 연산자(예: 클래스의 `(`/`[`/`.` 외 추가 문법)가 생기면 이 표에
        # 한 줄만 추가하면 되고, call()의 반복 로직은 건드릴 필요가 없다.
        self._postfix_factories = {
            TokenType.LEFT_PAREN: self._finish_call,
            TokenType.LEFT_BRACKET: self._finish_index,
            TokenType.DOT: self._finish_field_get,
        }

    def parse(self):
        """대입 표현식부터 시작해 표현식 전체를 파싱한다."""
        return self.assignment()

    def assignment(self):
        expr = self._climb()
        if not self.tokens.match(TokenType.EQUAL):
            return expr

        value = self.assignment()
        make_set_expr = self._ASSIGNMENT_TARGET_FACTORIES.get(type(expr))
        if make_set_expr is None:
            raise InvalidAssignmentTargetError("Invalid assignment target", self.tokens.previous())
        return make_set_expr(expr, value)

    def unary(self):
        if self.tokens.match(*self._UNARY_OPERATORS):
            operator = self.tokens.previous()
            right = self.unary()
            return UnaryExpr(operator=operator, right=right)
        return self.call()

    def call(self):
        """primary 뒤에 `(`/`[`/`.`가 반복해서 나오는 동안 함수 호출/인덱스 접근/필드 읽기로 묶는다.
        예: add(1, 2), get_fn()() (요구사항_정리/function.md), arr[0], arr[i][j]
        (요구사항_정리/정적배열.md), r.speed, r.move(5), r.move(5).report() (요구사항_정리/class.md)
        """
        expr = self.primary()
        while True:
            next_expr = self._match_postfix(expr)
            if next_expr is None:
                return expr
            expr = next_expr

    def _match_postfix(self, expr):
        """_postfix_factories에서 현재 토큰에 맞는 후위 연산자를 찾아 적용한다.
        맞는 연산자가 없으면 None을 반환해 call()이 반복을 멈추게 한다.
        """
        for token_type, finish in self._postfix_factories.items():
            if self.tokens.match(token_type):
                return finish(expr)
        return None

    def _finish_call(self, callee):
        paren = self.tokens.previous()
        arguments = []
        if not self.tokens.check(TokenType.RIGHT_PAREN):
            arguments.append(self.parse())
            while self.tokens.match(TokenType.COMMA):
                arguments.append(self.parse())
        self.tokens.consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments")
        return CallExpr(callee=callee, paren=paren, arguments=arguments)

    def _finish_index(self, object_):
        bracket = self.tokens.previous()
        index = self.parse()
        self.tokens.consume(TokenType.RIGHT_BRACKET, "Expected ']' after index")
        return IndexGetExpr(object=object_, bracket=bracket, index=index)

    def _finish_field_get(self, object_):
        name = self.tokens.consume(TokenType.IDENTIFIER, "Expected property name after '.'")
        return FieldGetExpr(object=object_, name=name)

    def primary(self):
        if self.tokens.match(*self._LITERAL_FACTORIES):
            token = self.tokens.previous()
            return self._LITERAL_FACTORIES[token.type](token)

        if self.tokens.match(TokenType.THIS):
            return ThisExpr(keyword=self.tokens.previous())

        if self.tokens.match(TokenType.SUPER):
            keyword = self.tokens.previous()
            self.tokens.consume(TokenType.DOT, "Expected '.' after 'super'")
            method = self.tokens.consume(TokenType.IDENTIFIER, "Expected superclass method name")
            return SuperExpr(keyword=keyword, method=method)

        if self.tokens.match(TokenType.IDENTIFIER):
            return VariableExpr(self.tokens.previous())

        if self.tokens.match(TokenType.LEFT_PAREN):
            expression = self.parse()
            self.tokens.consume(TokenType.RIGHT_PAREN, "Expected ')' after expression")
            return GroupingExpr(expression=expression)

        raise UnexpectedTokenError(f"Unexpected token: {self.tokens.current()}", self.tokens.current())

    # --- 공통 우선순위 규칙 ---

    def _climb(self, level=0):
        """_PRECEDENCE의 level 단계를 파싱한다. 표를 다 쓰면 unary()로 내려간다.

        각 단계는 자기보다 한 단계 조여진(level + 1) 표현식을 먼저 얻고,
        그 뒤로 자기 단계의 연산자가 반복해서 나오는 동안 좌결합으로 묶는다.
        """
        if level == len(self._PRECEDENCE):
            return self.unary()

        node_cls, operators = self._PRECEDENCE[level]
        expr = self._climb(level + 1)
        while self.tokens.match(*operators):
            operator = self.tokens.previous()
            right = self._climb(level + 1)
            expr = node_cls(left=expr, operator=operator, right=right)
        return expr
