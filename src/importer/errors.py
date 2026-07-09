from executor.errors import ExecutionError


class PipelineImportError(ExecutionError):
    """import 대상 모듈을 assemble/check하는 과정에서 나는 오류의 공통 베이스.

    ExecutionError를 상속해, Pipeline/Debugger가 실행 중 오류를 잡는
    except ExecutionError 절에 import 오류도 함께 걸리게 한다. import
    자체도 결국 "실행 중(import 문을 만났을 때) 발생하는 오류"이기 때문이다.
    """

    UNIT = "Import"


class ImportedFileNotFoundError(PipelineImportError):
    """import 대상 파일이 존재하지 않을 때."""


class CircularImportError(PipelineImportError):
    """import가 서로를 순환 참조할 때. 예: a.txt가 b.txt를, b.txt가 다시
    a.txt를 import하는 경우.
    """


class ModuleImportError(PipelineImportError):
    """import 대상 파일이 Assembler(문법) 또는 Checker(정적 검사)를
    통과하지 못했을 때. 두 단계 모두 "이 파일은 그대로 쓸 수 없다"는
    같은 의미라 하나의 오류 타입으로 합쳐서 알린다.

    errors에 실제로 발생한 오류 목록을 그대로 담아, 호출한 쪽(Executor)이
    무엇이 잘못됐는지 확인할 수 있게 한다. Assembler 단계에서 실패했다면
    그 AssemblerError(TokenizerError/MissingTokenError/UnexpectedTokenError
    등) 하나만 담긴 리스트가, Checker 단계에서 실패했다면 CheckerUnit이
    찾은 CheckerError 목록이 담긴다.

    AssemblerError/CheckerError를 그대로 흘려보내지 않고 감싸는 이유는,
    "import 대상 파일 자체의 오류"와 "최상위 프로그램 자체의 오류"를
    호출하는 쪽이 타입만으로 구분할 수 있어야 하기 때문이다.
    """

    def __init__(self, path, errors, keyword=None):
        super().__init__(f"Imported file failed to import: {path}", keyword)
        self.path = path
        self.errors = errors
