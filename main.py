#!/usr/bin/env python3
"""
PV-Lastprofil Gegensimulation

Rekonstruiert den Brutto-Stromverbrauch aus einem Lastprofil (Netzbezug),
indem die PV-Erzeugung einer Bestandsanlage via PVGIS simuliert und
auf den Netzbezug addiert wird.

Brutto-Verbrauch = Netzbezug (gemessen) + PV-Erzeugung (simuliert)
"""

import argparse
import sys
from pathlib import Path

from src.load_profile import load_profile
from src.pvgis import get_pv_production
from src.pv_simulation import simulate_gross_consumption
from src.export import export_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PV-Lastprofil Gegensimulation: Rekonstruiert den Brutto-Verbrauch "
                    "ohne PV aus einem Lastprofil mit eingerechneter Bestandsanlage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiel:
  python main.py -i lastprofil.csv --kwp 30 --lat 48.1 --lon 11.6

  python main.py -i lastprofil.csv --kwp 50 --lat 51.0 --lon 6.8 \\
                 --azimuth -10 --tilt 25 --year 2023 -o ergebnis.csv
        """,
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Pfad zur Kunden-CSV mit Lastprofil (Netzbezug)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Pfad für die Ergebnis-CSV (Default: <input>_brutto.csv)",
    )
    parser.add_argument(
        "--kwp",
        type=float,
        required=True,
        help="Installierte PV-Leistung in kWp",
    )
    parser.add_argument(
        "--lat",
        type=float,
        required=True,
        help="Breitengrad des Standorts",
    )
    parser.add_argument(
        "--lon",
        type=float,
        required=True,
        help="Längengrad des Standorts",
    )
    parser.add_argument(
        "--azimuth",
        type=float,
        default=0,
        help="Ausrichtung in Grad (0=Süd, -90=Ost, 90=West). Default: 0",
    )
    parser.add_argument(
        "--tilt",
        type=float,
        default=30,
        help="Dachneigung in Grad. Default: 30",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Jahr für historische Wetterdaten (Default: TMY)",
    )
    parser.add_argument(
        "--loss",
        type=float,
        default=14.0,
        help="Systemverluste in Prozent. Default: 14",
    )
    parser.add_argument(
        "--unit",
        choices=["kw", "kwh", "auto"],
        default="auto",
        help="Einheit der Werte in der Eingabedatei. Default: auto "
             "(erkennt kWh aus Dateiname/Spaltennamen). "
             "Bei 'kwh' wird automatisch in kW umgerechnet.",
    )
    parser.add_argument(
        "--no-ssl-verify",
        action="store_true",
        default=False,
        help="SSL-Zertifikatsprüfung deaktivieren (für Firmennetzwerke mit Proxy)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(f"{input_path.stem}_brutto.csv")

    print("=" * 60)
    print("  PV-LASTPROFIL GEGENSIMULATION")
    print("=" * 60)

    # 1. Lastprofil laden
    print("\n[1/4] Lastprofil laden...")
    lp = load_profile(input_path, unit=args.unit)

    # 2. PV-Erzeugung von PVGIS abrufen
    print("\n[2/4] PV-Erzeugung von PVGIS abrufen...")
    pv = get_pv_production(
        lat=args.lat,
        lon=args.lon,
        peak_power_kw=args.kwp,
        azimuth=args.azimuth,
        tilt=args.tilt,
        year=args.year,
        loss=args.loss,
        verify_ssl=not args.no_ssl_verify,
    )

    # 3. Brutto-Verbrauch berechnen
    print("\n[3/4] Brutto-Verbrauch berechnen...")
    result = simulate_gross_consumption(lp, pv)

    # 4. Ergebnis exportieren
    print("\n[4/4] Ergebnis exportieren...")
    export_results(result, output_path)

    print("\nFertig!")


if __name__ == "__main__":
    main()
