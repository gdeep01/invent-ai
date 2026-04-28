from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.models import Base, SalesTransaction, User
from app.services.csv_upload import CSVUploadService, validate_csv_columns, validate_mapped_column


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    return session


def test_validate_mapped_column_rejects_numeric_date_column():
    import pandas as pd

    df = pd.DataFrame({"sale_date": [12345, 67890]})

    assert validate_mapped_column(df, "sale_date", "date") is False


def test_validate_csv_columns_reports_invalid_date_mapping():
    csv_content = "sku,date,qty\nSKU-1,12345,10\nSKU-2,67890,12\n"

    is_valid, _, errors = validate_csv_columns(csv_content)

    assert is_valid is False
    assert any("matched to 'date'" in error for error in errors)


def test_process_csv_rejects_invalid_auto_mapped_date_column():
    session = _build_session()
    user = User(email="test@example.com", google_sub="sub-123", name="Tester")
    session.add(user)
    session.commit()
    session.refresh(user)

    service = CSVUploadService(session)
    csv_content = "sku,date,qty\nSKU-1,12345,10\nSKU-2,67890,12\n"

    response = service.process_csv(csv_content, user)

    assert response.success is False
    assert response.rows_processed == 0
    assert any("matched to 'date'" in error for error in response.errors)
    assert session.query(SalesTransaction).count() == 0
