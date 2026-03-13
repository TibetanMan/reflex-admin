from pathlib import Path


ROOTS = ("services", "shared", "test_reflex")


def test_production_code_does_not_use_datetime_utcnow():
    offenders: list[str] = []
    for root in ROOTS:
        for path in Path(root).rglob("*.py"):
            if "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if "datetime.utcnow" in text:
                offenders.append(str(path))

    assert offenders == []
