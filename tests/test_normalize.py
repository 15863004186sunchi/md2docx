from md2docx.normalize import normalize_heading


def test_normalize_heading_with_number_prefix() -> None:
    assert normalize_heading("1.2.3   接口设计") == "接口设计"


def test_normalize_heading_with_cn_prefix() -> None:
    assert normalize_heading("（一）总体设计") == "总体设计"

