from .errors import CheckerError


class ScopeChecker:
    """블록 하나(스코프)의 변수 선언 오류를 검사한다."""

    def __init__(self, expr_name_finder, errors, parent=None):
        self.declared_names = []
        self.imported_paths = []
        self.expr_name_finder = expr_name_finder
        self.errors = errors
        self.parent = parent

    def check_var_decl(self, statement):
        """변수 선언문(var a = ...;) 하나를 검사한다."""
        name_token = statement.name
        if name_token is None:
            return

        name = name_token.lexeme

        initializer_uses_name = (
            statement.initializer is not None
            and self.expr_name_finder.uses_name(statement.initializer, name)
        )
        if initializer_uses_name:
            self._record_error("Can't read local variable in initializer.", name_token)

        self.declare_name(name, name_token)

    def check_import(self, statement):
        """import문 하나를 검사한다. 같은 파일 재import와 alias 이름 충돌을 잡는다."""
        path = statement.path.literal
        if path in self.imported_paths:
            self._record_error("Already imported this file in this scope.", statement.keyword)
        elif self._is_imported_in_ancestor(path):
            self._record_error("Already imported this file in an enclosing scope.", statement.keyword)
        else:
            self.imported_paths.append(path)

        self.declare_name(statement.alias.lexeme, statement.alias)

    def _is_imported_in_ancestor(self, path):
        ancestor = self.parent
        while ancestor is not None:
            if path in ancestor.imported_paths:
                return True
            ancestor = ancestor.parent
        return False

    def declare_name(self, name, token):
        """이 스코프에 이름 하나를 선언한다. 이미 있으면 중복 오류를 기록한다."""
        if name in self.declared_names:
            self._record_error("Already a variable with this name in this scope.", token)
        else:
            self.declared_names.append(name)

    def _record_error(self, message, token):
        self.errors.append(CheckerError(message, token))
