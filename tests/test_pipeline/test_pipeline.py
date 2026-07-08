from pipeline import Pipeline


def test_pipeline_runs_valid_code_and_prints_result(capsys):
    pipeline = Pipeline()

    errors = pipeline.run("var a = 1; print a + 2;")

    assert errors == []
    assert capsys.readouterr().out == "3\n"


def test_pipeline_keeps_storage_between_run_calls(capsys):
    # 같은 Pipeline 인스턴스를 여러 번 run()하면 변수 상태가 유지된다.
    pipeline = Pipeline()

    pipeline.run("var a = 1;")
    pipeline.run("print a;")

    assert capsys.readouterr().out == "1\n"


def test_pipeline_reports_assembler_error_and_does_not_execute(capsys):
    # 3 = 5; -> 대입 대상이 변수가 아니라서 Assembler 단계에서 실패한다.
    pipeline = Pipeline()

    errors = pipeline.run("3 = 5;")

    assert len(errors) == 1
    assert str(errors[0]) == "[Assembler] Line 1: Invalid assignment target"
    assert capsys.readouterr().out == ""


def test_pipeline_reports_checker_error_and_does_not_execute(capsys):
    # { var a = a; } -> 초기화식이 자기 자신을 참조해서 Checker 단계에서 실패한다.
    pipeline = Pipeline()

    errors = pipeline.run("{ var a = a; }")

    assert len(errors) == 1
    assert str(errors[0]) == "[Checker] Line 1: Can't read local variable in initializer."
    assert capsys.readouterr().out == ""


def test_pipeline_reports_executor_error():
    # print 1 / 0; -> Assembler/Checker는 통과하지만 실행 중 0으로 나눈다.
    pipeline = Pipeline()

    errors = pipeline.run("print 1 / 0;")

    assert len(errors) == 1
    assert str(errors[0]) == "[Executor] Line 1: 0으로 나눌 수 없습니다."
