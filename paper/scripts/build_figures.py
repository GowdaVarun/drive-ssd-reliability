"""Build result figures from the bundled computed result tables."""
from math import ceil
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"
FIGURES = ROOT / "figures"
FONT_FILE = Path("C:/Windows/Fonts/arial.ttf")
W, H = 1400, 900

PRIMARY = [
    ("model", "Model risk", "#3973AC"),
    ("infra", "Rack risk", "#087E8B"),
    ("multi_0.7", "Multi-factor w=0.7", "#6C8EAD"),
    ("multi_0.5", "Multi-factor w=0.5", "#7B8794"),
    ("multi_0.3", "Multi-factor w=0.3", "#8A6FB0"),
    ("random", "Random selection", "#B8C0CC"),
]
TELEMETRY = [
    ("smart_threshold", "SMART rule", "#68778D"),
    ("ml_logreg", "SMART logistic", "#148A77"),
    ("ml_gbdt", "SMART LightGBM", "#2463A6"),
    ("drive_model", "DRIVE model risk", "#D08A25"),
    ("drive_infra", "DRIVE rack risk", "#087E8B"),
    ("drive_multi_w70", "DRIVE multi w=0.7", "#7556A7"),
    ("drive_multi_w50", "DRIVE multi w=0.5", "#B65372"),
    ("drive_multi_w30", "DRIVE multi w=0.3", "#508A43"),
    ("random", "Random selection", "#B8C0CC"),
]


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_FILE), size)
    except OSError:
        return ImageFont.load_default()


def build_coverage_chart(data: pd.DataFrame,
                         series: list[tuple[str, str, str]], *,
                         title: str, filename: str,
                         confidence: bool = False) -> None:
    image = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(image)
    title_font, tick_font, legend_font = font(48), font(38), font(35)
    left, right, top, bottom = 125, W - 55, 120, 570
    y_max = 0.70
    x = lambda budget: left + (float(budget) - 5.0) / 15.0 * (right - left)
    y = lambda value: bottom - float(value) / y_max * (bottom - top)

    draw.text((W / 2, 38), title, anchor="mt", fill="#142033", font=title_font)
    for tick in range(0, 71, 10):
        yy = y(tick / 100)
        draw.line((left, yy, right, yy), fill="#E5EAF0", width=2)
        draw.text((left - 17, yy), f"{tick}%", anchor="rm",
                  fill="#465366", font=tick_font)
    for budget in (5, 10, 15, 20):
        xx = x(budget)
        draw.line((xx, top, xx, bottom), fill="#F0F3F7", width=1)
        draw.text((xx, bottom + 16), f"{budget}%", anchor="mt",
                  fill="#465366", font=tick_font)
    draw.line((left, top, left, bottom), fill="#334155", width=2)
    draw.line((left, bottom, right, bottom), fill="#334155", width=2)
    draw.text(((left + right) / 2, 615), "Maintenance capacity budget",
              anchor="mt", fill="#243247", font=tick_font)

    for key, _label, color in series:
        rows = data[data["variant"] == key].sort_values("budget_pct")
        points = [(x(row.budget_pct), y(row.coverage)) for row in rows.itertuples()]
        if len(points) < 2:
            continue
        draw.line(points, fill=color, width=6, joint="curve")
        for px, py in points:
            draw.ellipse((px - 9, py - 9, px + 9, py + 9), fill=color,
                         outline="white", width=2)
        if confidence and key == "random":
            for row in rows.itertuples():
                px = x(row.budget_pct)
                py_low, py_high = y(row.coverage_ci_2_5), y(row.coverage_ci_97_5)
                draw.line((px, py_high, px, py_low), fill=color, width=3)
                draw.line((px - 8, py_high, px + 8, py_high), fill=color, width=3)
                draw.line((px - 8, py_low, px + 8, py_low), fill=color, width=3)

    columns = 3
    col_width = W // columns
    rows_per_col = ceil(len(series) / columns)
    legend_top = 685
    for index, (_key, label, color) in enumerate(series):
        col, row = index // rows_per_col, index % rows_per_col
        lx, ly = col * col_width + 16, legend_top + row * 48
        draw.line((lx, ly + 18, lx + 38, ly + 18), fill=color, width=6)
        draw.ellipse((lx + 13, ly + 10, lx + 29, ly + 26), fill=color)
        draw.text((lx + 54, ly), label, fill="#243247", font=legend_font)

    FIGURES.mkdir(parents=True, exist_ok=True)
    image.save(FIGURES / filename, dpi=(300, 300), optimize=True)


def main() -> None:
    primary = pd.read_csv(TABLES / "s4_results.csv")
    primary["variant"] = primary["strategy"]
    multi = primary["strategy"] == "multi"
    primary.loc[multi, "variant"] = primary.loc[multi, "weights"].map(
        lambda value: f"multi_{float(value):.1f}"
    )
    primary = primary.groupby(
        ["variant", "budget_pct"], as_index=False
    ).mean(numeric_only=True)
    build_coverage_chart(
        primary, PRIMARY,
        title="Full-fleet results: 11 models, mean across four decision dates",
        filename="full_fleet_coverage.png",
    )

    telemetry = pd.read_csv(TABLES / "s5_temporal_results.csv")
    telemetry = telemetry.rename(columns={"strategy": "variant"})
    build_coverage_chart(
        telemetry, TELEMETRY,
        title="Temporal SMART holdout: six-family October test cohort",
        filename="temporal_smart_coverage.png", confidence=True,
    )
    print("Built separate full-fleet and temporal SMART coverage figures.")


if __name__ == "__main__":
    main()
