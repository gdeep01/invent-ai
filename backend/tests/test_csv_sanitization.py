from app.services.csv_upload import sanitize_column_name


def test_sanitize_column_name_strips_special_characters():
    assert sanitize_column_name(" Product Name (%) ") == "product_name"


def test_sanitize_column_name_falls_back_to_column():
    assert sanitize_column_name("###") == "column"
