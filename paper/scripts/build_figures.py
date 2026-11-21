"""Create publication-ready S4 charts from the bundled computed results."""
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"
FIGURES = ROOT / "figures"
W, H = 1800, 1000
FONT_FILE = Path("C:/Windows/Fonts/arial.ttf")

COLORS = {
    "model": "#3B82F6",
    "infra": "#F97316",
    "multi_w70": "#8B5CF6",
    "multi_w50": "#14B8A6",
    "multi_w30": "#E11D48",
    "random": "#475569",
}
LABELS = {
    "model": "Model",
    "infra": "Rack",
    "multi_w70": "Multi (model 0.7)",
    "multi_w50": "Multi (model 0.5)",
    "multi_w30": "Multi (model 0.3)",
    "random": "Random",
}
ORDER = ["model", "infra", "multi_w70", "multi_w50", "multi_w30", "random"]


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_FILE), size)
    except OSError:
        return ImageFont.load_default()


def line_chart(df: pd.DataFrame, metric: str, title: str, y_label: str,
               filename: str, y_max: float, percent: bool = False) -> None:
    image = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(image)
    title_font, label_font, small_font = font(46), font(28), font(22)
    draw.text((W / 2, 36), title, anchor="mt", fill="#111827", font=title_font)

    left, right, top, bottom = 160, 130, 145, 780
    x_min, x_max = 5.0, 20.0
    series = df.pivot(index="budget_pct", columns="variant", values=metric)
    x = lambda budget: left + (budget - x_min) / (x_max - x_min) * (W - left - right)
    y = lambda val: bottom - val / y_max * (bottom - top)

    ticks = 5
    for i in range(ticks + 1):
        val = y_max * i / ticks
        yy = y(val)
        draw.line((left, yy, W - right, yy), fill="#E5E7EB", width=2)
        tick_text = f"{val * 100:.0f}%" if percent else f"{val:.1f}"
        draw.text((left - 18, yy), tick_text, anchor="rm", fill="#4B5563", font=small_font)
    for budget in (5, 10, 15, 20):
        xx = x(float(budget))
        draw.line((xx, top, xx, bottom), fill="#F3F4F6", width=1)
        draw.text((xx, bottom + 18), f"{budget}%", anchor="mt", fill="#374151", font=label_font)

    draw.line((left, top, left, bottom), fill="#374151", width=3)
    draw.line((left, bottom, W - right, bottom), fill="#374151", width=3)
    draw.text((W / 2, 850), "Maintenance capacity budget", anchor="mt", fill="#111827", font=label_font)
    label_box = Image.new("RGBA", (560, 48), (255, 255, 255, 0))
    ImageDraw.Draw(label_box).text((280, 24), y_label, anchor="mm", fill="#111827", font=label_font)
    rotated = label_box.rotate(90, expand=True)
    image.paste(rotated, (8, int((top + bottom - rotated.height) / 2)), rotated)

    for variant in ORDER:
        if variant not in series.columns:
            continue
        points = [(x(float(b)), y(float(series.loc[b, variant])))
                  for b in series.index if pd.notna(series.loc[b, variant])]
        color = COLORS[variant]
        if len(points) > 1:
            draw.line(points, fill=color, width=7, joint="curve")
        for xx, yy in points:
            draw.ellipse((xx - 9, yy - 9, xx + 9, yy + 9), fill=color, outline="white", width=2)

    legend_y = 925
    legend_positions = [185, 435, 680, 980, 1260, 1510]
    for variant, lx in zip(ORDER, legend_positions):
        draw.line((lx, legend_y + 9, lx + 38, legend_y + 9), fill=COLORS[variant], width=6)
        draw.text((lx + 48, legend_y), LABELS[variant], fill="#1F2937", font=small_font)
    image.save(FIGURES / filename, dpi=(300, 300), optimize=True)


def workflow_diagram() -> None:
    image = Image.new("RGB", (1800, 700), "white")
    draw = ImageDraw.Draw(image)
    heading, box_font, desc_font = font(42), font(28), font(22)
    draw.text((900, 38), "Chronological maintenance prioritisation", anchor="mt", fill="#111827", font=heading)

    boxes = [
        (60, 220, 420, 470, "Historical tickets\nand topology", "Failures strictly before t"),
        (520, 220, 880, 470, "Group risk", "Model and rack rates\nshrunk from past events"),
        (980, 220, 1340, 470, "Equal-budget lists", "Rank strategies; select\nthe same K drives"),
        (1440, 220, 1740, 470, "Evaluate", "Count failures strictly\nafter t"),
    ]
    fills = ["#DBEAFE", "#CCFBF1", "#FEF3C7", "#FFE4E6"]
    for idx, (x1, y1, x2, y2, title, desc) in enumerate(boxes):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=24, fill=fills[idx], outline="#334155", width=3)
        draw.multiline_text(((x1 + x2) / 2, y1 + 56), title, anchor="mm", align="center", fill="#111827", font=box_font, spacing=10)
        draw.multiline_text(((x1 + x2) / 2, y1 + 165), desc, anchor="mm", align="center", fill="#334155", font=desc_font, spacing=8)
        if idx < len(boxes) - 1:
            draw.line((x2 + 12, 345, boxes[idx + 1][0] - 18, 345), fill="#475569", width=6)
            ax = boxes[idx + 1][0] - 18
            draw.polygon([(ax, 345), (ax - 20, 332), (ax - 20, 358)], fill="#475569")
    draw.text((900, 565), "Ranking inputs are rebuilt at each decision date; test outcomes never affect scores.",
              anchor="mt", fill="#374151", font=desc_font)
    image.save(FIGURES / "study_workflow.png", dpi=(300, 300), optimize=True)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(TABLES / "s4_results.csv")
    data["variant"] = data["strategy"].where(data["strategy"].isin(["model", "infra"]),
        "multi_w" + data["weights"].map(lambda value: str(int(value * 100)) if pd.notna(value) else ""))
    data.loc[data["strategy"] == "random", "variant"] = "random"
    means = data.groupby(["variant", "budget_pct"], as_index=False).mean(numeric_only=True)
    line_chart(means, "coverage", "Failure coverage by maintenance budget",
               "Subsequent failure coverage", "s4_coverage_budget.png", 0.70, percent=True)
    line_chart(means, "lift", "Mean lift by maintenance budget",
               "Lift over random", "s4_lift_budget.png", 4.0)
    workflow_diagram()
    print("Built three figures from the bundled S4 results.")


if __name__ == "__main__":
    main()
