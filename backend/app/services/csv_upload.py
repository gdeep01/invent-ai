import re
from io import StringIO
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.security import decrypt_value
from app.models import SKU, SalesTransaction, Store, User, UserSettings
from app.schemas import CSVMappingSuggestion, CSVPreviewResponse, CSVUploadResponse, SalesRowSchema, UploadAnomaly

COLUMN_ALIASES: Dict[str, List[str]] = {
    "store_id": [
        "store_id", "store", "storecode", "shop_id", "branch_id", "branch",
        "location", "city", "outlet", "outlet_id", "shop", "site", "site_id",
        "store_name", "region", "area",
    ],
    "sku_id": [
        "sku_id", "sku", "product_id", "item_id", "barcode", "invoice_id",
        "invoice", "transaction_id", "order_id", "receipt_id", "bill_no",
        "product_code", "item_code", "code", "id", "pid",
    ],
    "sku_name": [
        "sku_name", "product_name", "item_name", "name", "description",
        "product_description", "item_description", "title", "product_title",
        "item_title", "goods_name", "article_name", "label",
    ],
    "date": [
        "date", "sale_date", "transaction_date", "invoice_date", "order_date",
        "purchase_date", "bill_date", "created_at", "created_date", "datetime",
        "sold_date", "entry_date", "txn_date",
    ],
    "units_sold": [
        "units_sold", "units", "quantity", "qty", "sold", "sales_qty",
        "amount_sold", "count", "no_of_units", "num_units", "pieces",
        "pcs", "volume", "sales_volume", "qty_sold",
    ],
    "price": [
        "price", "unit_price", "selling_price", "rate", "mrp", "sp",
        "sale_price", "retail_price", "cost", "amount", "value",
        "gross_sales", "revenue", "sales_amount", "total_amount",
    ],
    "discount": [
        "discount", "discount_pct", "offer", "discount_amount",
        "discount_percent", "rebate", "markdown", "tax_5", "tax",
    ],
    "category": [
        "category", "type", "product_category", "product_line", "product line",
        "department", "section", "segment", "class", "sub_category",
        "subcategory", "product_type", "item_type", "product_group",
    ],
}

REQUIRED_COLUMNS = ["store_id", "sku_id", "date", "units_sold"]
OPTIONAL_COLUMNS = ["sku_name", "price", "discount", "category"]
DEFAULTABLE_COLUMNS = ["store_id", "sku_name"]
COLUMN_EXPECTED_TYPES: Dict[str, str] = {
    "date": "date",
    "units_sold": "numeric",
    "price": "numeric",
    "discount": "numeric",
}


def sanitize_column_name(column_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]+", "_", column_name.strip().lower())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "column"


def normalize_headers(columns: List[str]) -> List[str]:
    return [sanitize_column_name(column) for column in columns]


def find_column_match(columns: List[str], target: str) -> Optional[str]:
    normalized_map = {sanitize_column_name(column): column for column in columns}
    for alias in COLUMN_ALIASES.get(target, [target]):
        sanitized_alias = sanitize_column_name(alias)
        if sanitized_alias in normalized_map:
            return normalized_map[sanitized_alias]
    return None


def validate_mapped_column(df: pd.DataFrame, column_name: str, expected_type: str) -> bool:
    if column_name not in df.columns:
        return False

    sample = df[column_name].dropna().head(100)
    if sample.empty:
        return True

    if expected_type == "date":
        if pd.api.types.is_numeric_dtype(sample):
            return False
        parsed = pd.to_datetime(sample, errors="coerce")
        return bool(parsed.notna().all())

    if expected_type == "numeric":
        parsed = pd.to_numeric(sample, errors="coerce")
        return bool(parsed.notna().all())

    return True


def map_columns(df: pd.DataFrame, explicit_mapping: Optional[dict[str, str]] = None) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    mapping: Dict[str, str] = {}
    original_columns = list(df.columns)
    already_used_sources: set = set()

    if explicit_mapping:
        for original, standard in explicit_mapping.items():
            if original in original_columns:
                mapping[original] = standard
                already_used_sources.add(original)

    for target in REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
        if target in mapping.values():
            continue
        original = find_column_match(original_columns, target)
        if original and original not in already_used_sources:
            mapping[original] = target
            already_used_sources.add(original)

    missing = [column for column in REQUIRED_COLUMNS if column not in DEFAULTABLE_COLUMNS and column not in mapping.values()]
    df = df.rename(columns=mapping)
    return df, mapping, missing


def validate_column_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> List[str]:
    validation_errors: List[str] = []
    for source_column, target_column in mapping.items():
        expected_type = COLUMN_EXPECTED_TYPES.get(target_column)
        if not expected_type:
            continue
        if not validate_mapped_column(df, source_column, expected_type):
            validation_errors.append(
                f"Column '{source_column}' matched to '{target_column}' but does not contain valid {expected_type} values."
            )
    return validation_errors


def derive_sku_name(df: pd.DataFrame) -> pd.DataFrame:
    if "sku_name" in df.columns:
        return df
    if "category" in df.columns and "sku_id" in df.columns:
        df["sku_name"] = df["sku_id"].astype(str) + " - " + df["category"].astype(str)
    elif "category" in df.columns:
        df["sku_name"] = df["category"].astype(str)
    elif "sku_id" in df.columns:
        df["sku_name"] = df["sku_id"].astype(str)
    else:
        df["sku_name"] = "Unknown"
    return df


def candidate_gemini_models() -> List[str]:
    candidates = [
        settings.GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-2.5-flash-preview-09-2025",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
    ]
    deduped: List[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def detect_anomalies(df: pd.DataFrame) -> List[UploadAnomaly]:
    anomalies: List[UploadAnomaly] = []
    if {"sku_name", "date", "units_sold"} - set(df.columns):
        return anomalies

    working = df.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working["units_sold"] = pd.to_numeric(working["units_sold"], errors="coerce")
    working = working.dropna(subset=["date", "units_sold"]).sort_values(["sku_name", "date"]).reset_index()

    for sku_name, sku_df in working.groupby("sku_name"):
        rolling_mean = sku_df["units_sold"].rolling(window=7, min_periods=3).mean()
        rolling_std = sku_df["units_sold"].rolling(window=7, min_periods=3).std().fillna(0)
        mask = sku_df["units_sold"] > (rolling_mean + (rolling_std * 2.5))
        for _, row in sku_df[mask].iterrows():
            anomalies.append(
                UploadAnomaly(
                    row_index=int(row["index"]),
                    sku_name=sku_name,
                    date=row["date"].date(),
                    units_sold=float(row["units_sold"]),
                    note=f"Unusual spike detected on {row['date'].date().isoformat()}",
                )
            )
    return anomalies


def validate_csv_columns(file_content: str) -> Tuple[bool, List[str], List[str]]:
    try:
        df = pd.read_csv(StringIO(file_content), nrows=3)
        sanitized = normalize_headers(list(df.columns))
        preview_df = df.copy()
        preview_df.columns = sanitized
        _, mapping, missing = map_columns(preview_df)
        missing.extend(validate_column_mapping(preview_df, mapping))
        return len(missing) == 0, sanitized, missing
    except Exception:
        return False, [], [column for column in REQUIRED_COLUMNS if column not in DEFAULTABLE_COLUMNS]


def resolve_column_mapping(
    df: pd.DataFrame, mapping: Optional[dict[str, str]] = None
) -> Tuple[pd.DataFrame, Dict[str, str], List[str], List[str]]:
    mapped_df, discovered_mapping, missing = map_columns(df, mapping)
    validation_errors = validate_column_mapping(df, discovered_mapping)
    return mapped_df, discovered_mapping, missing, validation_errors


class CSVUploadService:
    def __init__(self, db: Session):
        self.db = db

    def preview_csv(self, file_content: str, user: User, mapping: Optional[dict[str, str]] = None) -> CSVPreviewResponse:
        df = pd.read_csv(StringIO(file_content))
        df.columns = [sanitize_column_name(col) for col in df.columns]
        mapped_df, discovered_mapping, missing, validation_errors = resolve_column_mapping(df, mapping)
        used_ai = False
        note = None
        if missing or validation_errors:
            ai_mapping = self._suggest_mapping_with_ai(user, df)
            if ai_mapping:
                mapped_df, discovered_mapping, missing, validation_errors = resolve_column_mapping(df, ai_mapping)
                used_ai = True
                note = "Gemini suggested the mapping for this CSV."
        mapped_df = derive_sku_name(mapped_df)
        missing = [col for col in missing if col != "sku_name"]
        missing.extend(validation_errors)
        anomalies = detect_anomalies(mapped_df if not missing else df)
        return CSVPreviewResponse(
            success=len(missing) == 0,
            suggestion=CSVMappingSuggestion(mapping=discovered_mapping, missing_columns=missing, used_ai=used_ai, note=note),
            sample_columns=list(df.columns),
            anomalies=anomalies,
        )

    def process_csv(
        self,
        file_content: str,
        user: User,
        mapping: Optional[dict[str, str]] = None,
        excluded_rows: Optional[List[int]] = None,
    ) -> CSVUploadResponse:
        excluded_rows = excluded_rows or []
        try:
            df = pd.read_csv(StringIO(file_content))
            df.columns = [sanitize_column_name(col) for col in df.columns]
            df, _, missing, validation_errors = resolve_column_mapping(df, mapping)
            if missing:
                return CSVUploadResponse(
                    success=False,
                    rows_processed=0,
                    rows_failed=len(df),
                    errors=[f"Missing required columns: {', '.join(missing)}"],
                )
            if validation_errors:
                return CSVUploadResponse(
                    success=False,
                    rows_processed=0,
                    rows_failed=len(df),
                    errors=validation_errors,
                )

            if "store_id" not in df.columns:
                df["store_id"] = "STORE001"
            df = derive_sku_name(df)

            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            for col in ["units_sold", "price", "discount"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            anomalies = detect_anomalies(df)
            anomaly_map = {a.row_index: a.note for a in anomalies}
            valid_rows: List[SalesRowSchema] = []
            errors: List[str] = []
            rows_failed = 0
            store_id: Optional[str] = None

            for index, row in enumerate(df.to_dict("records")):
                if index in excluded_rows:
                    continue
                try:
                    row["store_id"] = str(row.get("store_id") or "STORE001")
                    row["sku_id"] = str(row.get("sku_id"))
                    row["sku_name"] = str(row.get("sku_name") or row["sku_id"])
                    if pd.isna(row.get("date")):
                        raise ValueError("Invalid date")
                    valid_row = SalesRowSchema(**row)
                    valid_rows.append(valid_row)
                    store_id = store_id or valid_row.store_id
                except Exception as exc:
                    rows_failed += 1
                    if len(errors) < 10:
                        errors.append(f"Row {index + 2}: {exc}")

            if not valid_rows:
                return CSVUploadResponse(success=False, rows_processed=0, rows_failed=rows_failed, errors=errors, anomalies=anomalies)

            store_map: Dict[str, Store] = {}
            for current_store_id in sorted({row.store_id for row in valid_rows}):
                store = self.db.query(Store).filter(Store.user_id == user.id, Store.store_id == current_store_id).first()
                if not store:
                    store = Store(user_id=user.id, store_id=current_store_id, name=f"Store {current_store_id}")
                    self.db.add(store)
                    self.db.flush()
                store_map[current_store_id] = store

            sku_map: Dict[tuple[int, str], SKU] = {}
            existing_skus = (
                self.db.query(SKU)
                .filter(SKU.user_id == user.id, SKU.store_id.in_([s.id for s in store_map.values()]))
                .all()
            )
            for sku in existing_skus:
                sku_map[(sku.store_id, sku.sku_id)] = sku

            for row in valid_rows:
                store = store_map[row.store_id]
                key = (store.id, row.sku_id)
                if key not in sku_map:
                    sku = SKU(user_id=user.id, store_id=store.id, sku_id=row.sku_id, sku_name=row.sku_name, category=row.category)
                    self.db.add(sku)
                    self.db.flush()
                    sku_map[key] = sku
                else:
                    sku = sku_map[key]
                    sku.sku_name = row.sku_name
                    sku.category = row.category or sku.category

            transactions: List[SalesTransaction] = []
            for index, row in enumerate(valid_rows):
                store = store_map[row.store_id]
                sku = sku_map[(store.id, row.sku_id)]
                transactions.append(
                    SalesTransaction(
                        user_id=user.id,
                        store_id=store.id,
                        sku_id=sku.id,
                        date=row.date,
                        units_sold=row.units_sold,
                        price=row.price,
                        discount=row.discount,
                        excluded_from_forecast=False,
                        anomaly_note=anomaly_map.get(index),
                    )
                )

            for store in store_map.values():
                sku_ids = [sku.id for (store_db_id, _), sku in sku_map.items() if store_db_id == store.id]
                self.db.query(SalesTransaction).filter(
                    SalesTransaction.user_id == user.id,
                    SalesTransaction.store_id == store.id,
                    SalesTransaction.sku_id.in_(sku_ids),
                ).delete(synchronize_session=False)

            self.db.bulk_save_objects(transactions)
            self.db.commit()

            return CSVUploadResponse(
                success=True,
                rows_processed=len(valid_rows),
                rows_failed=rows_failed,
                errors=errors,
                store_id=store_id,
                anomalies=anomalies,
            )
        except Exception as exc:
            self.db.rollback()
            return CSVUploadResponse(success=False, rows_processed=0, rows_failed=0, errors=[f"Failed to parse CSV: {exc}"])

    def _suggest_mapping_with_ai(self, user: User, df: pd.DataFrame) -> Optional[dict[str, str]]:
        api_key = None
        settings_row = self.db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        if settings_row and settings_row.encrypted_gemini_api_key:
            api_key = decrypt_value(settings_row.encrypted_gemini_api_key)
        if not api_key:
            import os
            api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        try:
            import json
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            prompt = (
                "Map these CSV columns to schema fields only when confident. "
                "Schema fields: store_id, sku_id, sku_name, date, units_sold, price, discount, category. "
                f"CSV columns: {list(df.columns)}. "
                f"Sample rows: {df.head(3).to_dict('records')}. "
                "Rules: each source column can only be mapped once. "
                "Return a strict JSON object mapping source column name to schema field name. "
                "Only include mappings you are confident about. Return nothing else."
            )
            last_error: Exception | None = None
            for model_name in candidate_gemini_models():
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
                    return json.loads(raw)
                except Exception as exc:
                    last_error = exc
            raise last_error or RuntimeError("No Gemini model could be used.")
        except Exception:
            return None
