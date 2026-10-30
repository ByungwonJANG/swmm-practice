scenarios = ["2-yr", "10-yr", "100-yr"]

with open("models/base.inp", encoding="utf-8") as f:
    lines = f.read().splitlines()

for name in scenarios:
    section = ""
    new_lines = []

    for line in lines:
        text = line.strip()

        if text.startswith("["):
            section = text.upper()

        if section == "[RAINGAGES]" and text and not text.startswith(";") and not text.startswith("["):
            parts = line.split()
            parts[-1] = name
            line = "  ".join(parts)

        new_lines.append(line)

    out_file = f"models/scenario_{name.replace('-', '')}.inp"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    print(f"{out_file} 생성 완료 (강우: {name})")