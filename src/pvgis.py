"""PVGIS API Client für PV-Ertragssimulation."""

import requests
import pandas as pd
import io

PVGIS_BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


def get_pv_production(
    lat: float,
    lon: float,
    peak_power_kw: float,
    azimuth: float = 0,
    tilt: float = 30,
    year: int | None = None,
    loss: float = 14.0,
    verify_ssl: bool = True,
) -> pd.DataFrame:
    """
    Ruft stündliche PV-Erzeugungsdaten von der PVGIS API ab.

    Args:
        lat: Breitengrad
        lon: Längengrad
        peak_power_kw: Installierte Leistung in kWp
        azimuth: Ausrichtung in Grad (0=Süd, -90=Ost, 90=West)
        tilt: Dachneigung in Grad
        year: Konkretes Jahr für historische Daten (None = TMY)
        loss: Systemverluste in Prozent (Default: 14%)

    Returns:
        DataFrame mit DatetimeIndex und Spalte 'pv_kw' (stündliche PV-Leistung in kW)
    """
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": peak_power_kw,
        "angle": tilt,
        "aspect": azimuth,
        "loss": loss,
        "outputformat": "csv",
        "pvcalculation": 1,
    }

    if year is not None:
        params["startyear"] = year
        params["endyear"] = year
    else:
        # TMY-Daten (Typical Meteorological Year)
        params["startyear"] = 2005
        params["endyear"] = 2020

    print(f"  PVGIS-Abfrage: {peak_power_kw} kWp, Standort ({lat}, {lon}), "
          f"Azimut {azimuth}°, Neigung {tilt}°")

    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(PVGIS_BASE_URL, params=params, timeout=60, verify=verify_ssl)
    response.raise_for_status()

    # PVGIS CSV hat Header-Zeilen und Footer-Zeilen die übersprungen werden müssen
    content = response.text
    lines = content.strip().split("\n")

    # Header-Zeilen finden (beginnen mit Metadaten, Daten starten nach leerem Block)
    data_start = None
    data_end = None
    for i, line in enumerate(lines):
        if line.startswith("time,"):
            data_start = i
        if data_start is not None and i > data_start and line.strip() == "":
            data_end = i
            break

    if data_start is None:
        raise ValueError("PVGIS-Antwort konnte nicht geparst werden. "
                         "Prüfen Sie die Eingabeparameter.")

    if data_end is None:
        data_end = len(lines)

    csv_data = "\n".join(lines[data_start:data_end])
    df = pd.read_csv(io.StringIO(csv_data))

    # Zeitstempel parsen (Format: "20050101:0010" = YYYYMMDD:HHMM)
    df["zeitstempel"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M")
    df = df.set_index("zeitstempel").sort_index()

    # P ist die PV-Leistung in Watt -> in kW umrechnen
    df["pv_kw"] = df["P"] / 1000.0

    result = df[["pv_kw"]].copy()

    # Bei TMY: Daten auf ein einziges "repräsentatives" Jahr normalisieren
    if year is None:
        # TMY liefert Daten mit verschiedenen Jahren - wir nehmen einfach das Muster
        # und setzen alles auf ein Referenzjahr (2020)
        result = _normalize_tmy_to_single_year(result, reference_year=2020)

    total_kwh = result["pv_kw"].sum()  # Stündliche Werte = kWh
    specific_yield = total_kwh / peak_power_kw if peak_power_kw > 0 else 0
    print(f"  PVGIS-Ergebnis: {total_kwh:.0f} kWh/Jahr "
          f"({specific_yield:.0f} kWh/kWp)")

    return result


def _normalize_tmy_to_single_year(df: pd.DataFrame, reference_year: int) -> pd.DataFrame:
    """Normalisiert TMY-Daten auf ein einziges Referenzjahr."""
    new_index = df.index.map(
        lambda ts: ts.replace(year=reference_year)
    )
    # Schaltjahr-Handling: 29. Feb kann in manchen TMY-Jahren fehlen
    df = df.copy()
    df.index = new_index
    # Duplikate entfernen (können bei Jahreswechseln in TMY auftreten)
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()
    return df
