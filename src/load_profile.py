"""Laden und Parsen von Kunden-Lastprofilen (CSV und Excel)."""

import pandas as pd
from pathlib import Path


# Häufige Spaltennamen für Zeitstempel und Leistung
TIMESTAMP_COLUMNS = [
    "zeitstempel", "timestamp", "datum", "date", "zeit", "time",
    "datum/zeit", "date/time", "datetime", "datum_zeit",
]
POWER_COLUMNS = [
    "netzbezug", "bezug", "leistung", "power", "kw", "kwh", "verbrauch",
    "consumption", "grid", "netz", "wirkleistung", "p_bezug",
    "bezug_kw", "leistung_kw", "netzbezug_kw", "bezug_kwh", "verbrauch_kwh",
    "energiemenge", "menge", "wert", "value",
]


def _detect_separator(filepath: Path) -> str:
    """Erkennt den CSV-Separator anhand der ersten Zeilen."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        header = f.readline()
    if ";" in header:
        return ";"
    return ","


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Findet eine Spalte anhand einer Liste möglicher Namen (case-insensitive)."""
    df_cols_lower = {col.lower().strip(): col for col in df.columns}
    for candidate in candidates:
        if candidate in df_cols_lower:
            return df_cols_lower[candidate]
    return None


def _parse_german_float(series: pd.Series) -> pd.Series:
    """Konvertiert deutsche Zahlformate (Komma als Dezimaltrennzeichen)."""
    if pd.api.types.is_string_dtype(series):
        return pd.to_numeric(
            series.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            errors="coerce",
        )
    return pd.to_numeric(series, errors="coerce")


def _detect_unit(filepath: Path, df: pd.DataFrame) -> str:
    """Erkennt ob Werte in kW oder kWh vorliegen anhand Dateiname und Spaltennamen."""
    # Dateiname prüfen
    if "kwh" in filepath.stem.lower():
        print(f"  Auto-Erkennung: 'kWh' im Dateinamen gefunden -> Einheit: kWh")
        return "kwh"
    # Spaltennamen prüfen
    for col in df.columns:
        if "kwh" in col.lower():
            print(f"  Auto-Erkennung: 'kWh' in Spalte '{col}' gefunden -> Einheit: kWh")
            return "kwh"
    return "kw"


def _read_file(filepath: Path) -> pd.DataFrame:
    """Liest CSV- oder Excel-Dateien und gibt ein DataFrame zurück."""
    suffix = filepath.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        print(f"  Excel-Datei erkannt ({suffix})")
        df = pd.read_excel(filepath)
    else:
        sep = _detect_separator(filepath)
        df = pd.read_csv(filepath, sep=sep, encoding="utf-8-sig")
    return df


def load_profile(filepath: str | Path, unit: str = "auto") -> pd.DataFrame:
    """
    Lädt ein Lastprofil aus einer CSV- oder Excel-Datei.

    Gibt ein DataFrame mit DatetimeIndex und Spalte 'netzbezug_kw' zurück.
    Unterstützt CSV (verschiedene Separatoren, deutsches Format) und Excel (.xlsx/.xls).

    Args:
        filepath: Pfad zur Eingabedatei
        unit: Einheit der Werte ('kw', 'kwh' oder 'auto').
              'auto' erkennt kWh aus Dateiname/Spaltennamen.
              Bei 'kwh' wird anhand des Intervalls in kW umgerechnet.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {filepath}")

    df = _read_file(filepath)

    if df.empty:
        raise ValueError("Die Datei ist leer.")

    # Auto-Erkennung der Einheit
    if unit == "auto":
        unit = _detect_unit(filepath, df)
    print(f"  Einheit der Eingabewerte: {unit.upper()}")

    # Verfügbare Spalten anzeigen
    print(f"  Gefundene Spalten: {list(df.columns)}")
    if len(df) > 0:
        print(f"  Erste Zeile: {df.iloc[0].to_dict()}")

    # Zeitstempel-Spalte finden
    ts_col = _find_column(df, TIMESTAMP_COLUMNS)
    if ts_col is None:
        # Erste Spalte als Zeitstempel verwenden
        ts_col = df.columns[0]
        print(f"  Hinweis: Verwende erste Spalte '{ts_col}' als Zeitstempel.")

    # Leistungsspalte finden
    power_col = _find_column(df, POWER_COLUMNS)
    if power_col is None:
        # Zweite numerische Spalte verwenden
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        non_ts_numeric = [c for c in numeric_cols if c != ts_col]
        if non_ts_numeric:
            power_col = non_ts_numeric[0]
        else:
            # Versuche zweite Spalte als deutsche Zahl zu parsen
            power_col = [c for c in df.columns if c != ts_col][0]
    print(f"  Zeitstempel-Spalte: '{ts_col}'")
    print(f"  Werte-Spalte: '{power_col}'")

    # Zeitstempel parsen
    df["zeitstempel"] = pd.to_datetime(df[ts_col], dayfirst=True, format="mixed")
    df = df.set_index("zeitstempel").sort_index()

    # Leistungswerte konvertieren
    df["netzbezug_kw"] = _parse_german_float(df[power_col])

    # Nur relevante Spalte behalten
    result = df[["netzbezug_kw"]].copy()

    # NaN-Werte entfernen
    nan_count = result["netzbezug_kw"].isna().sum()
    if nan_count > 0:
        print(f"  Warnung: {nan_count} ungültige Werte entfernt.")
        result = result.dropna()

    # Intervall prüfen und ggf. kWh -> kW umrechnen
    if len(result) >= 2:
        intervals = result.index.to_series().diff().dropna()
        median_interval = intervals.median()
        print(f"  Erkanntes Intervall: {median_interval}")

        if unit.lower() == "kwh":
            hours_per_interval = median_interval.total_seconds() / 3600
            result["netzbezug_kw"] = result["netzbezug_kw"] / hours_per_interval
            print(f"  kWh -> kW umgerechnet (Faktor: /{hours_per_interval})")

    print(f"  Geladen: {len(result)} Datenpunkte von {result.index[0]} bis {result.index[-1]}")
    return result
