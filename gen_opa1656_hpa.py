#!/usr/bin/env python3
"""OPA1656 1個(デュアル)のヘッドホンアンプ回路から KiCad 7 の .kicad_sch を生成する。

想定ヘッドホン: AKG K371 (32Ω / 114 dB SPL/V の高能率機)
電源: 正負 ±15V (±5V〜±16V 範囲で可)
回路: 非反転アンプ (ゲイン 1+Rf/Rg = 2倍 = +6dB) を L/R 各1ch (U1A/U1B)
      入力 AC結合 -> ボリューム(10kΩ log 2連) -> RFフィルタ -> OPA1656 -> 10Ω -> ヘッドホン
      帰還は 10Ω の前から取る。

部品は同梱の簡易シンボル(Local:*)を使い、接続はピン端のネットラベルで表現する。
使い方: python3 gen_opa1656_hpa.py [出力.kicad_sch]
生成後、KiCad で開き、必要なら標準ライブラリのシンボル/フットプリントに差し替えてください。
"""
import sys
import uuid

ROOT = str(uuid.uuid4())
PROJECT = "opa1656_hpa"
FONT = "(effects (font (size 1.27 1.27)))"
HIDE = "(effects (font (size 1.27 1.27)) hide)"


def uid():
    return str(uuid.uuid4())


def conn(n, names):
    """左側にピンが並ぶコネクタ。"""
    h = 2.54 * n
    return dict(prefix="J", body=(-3.81, -h / 2, 3.81, h / 2),
                pins=[(str(i + 1), names[i], -6.35, round(h / 2 - 1.27 - 2.54 * i, 2), 0)
                      for i in range(n)])


# pins = (番号, 名前, x, y, 角度) シンボル座標系(Y上向き)
# 角度: 0=ピンは左側(右向きに伸びる), 180=右側, 90=下側, 270=上側
LIB = {
    "R": dict(prefix="R", body=(-1.016, -2.54, 1.016, 2.54),
              pins=[("1", "~", 0, 3.81, 270), ("2", "~", 0, -3.81, 90)]),
    "C": dict(prefix="C", body=(-1.27, -0.6, 1.27, 0.6),
              pins=[("1", "~", 0, 3.81, 270), ("2", "~", 0, -3.81, 90)]),
    "CP": dict(prefix="C", body=(-1.27, -0.6, 1.27, 0.6),
               pins=[("1", "+", 0, 3.81, 270), ("2", "-", 0, -3.81, 90)]),
    "POT": dict(prefix="RV", body=(-1.016, -2.54, 1.016, 2.54),
                pins=[("1", "1", 0, 3.81, 270), ("2", "2", 0, -3.81, 90),
                      ("3", "W", -3.81, 0, 0)]),
    "CONN3": conn(3, ["1", "2", "3"]),
    # OPA1656: unit1=A(3,2,1) unit2=B(5,6,7) unit3=電源(8,4)
    "OPA1656": dict(
        prefix="U",
        units={
            1: dict(body=(-5.08, -5.08, 5.08, 5.08),
                    pins=[("3", "+", -7.62, 2.54, 0), ("2", "-", -7.62, -2.54, 0),
                          ("1", "~", 7.62, 0, 180)]),
            2: dict(body=(-5.08, -5.08, 5.08, 5.08),
                    pins=[("5", "+", -7.62, 2.54, 0), ("6", "-", -7.62, -2.54, 0),
                          ("7", "~", 7.62, 0, 180)]),
            3: dict(body=(-5.08, -5.08, 5.08, 5.08),
                    pins=[("8", "V+", 0, 7.62, 270), ("4", "V-", 0, -7.62, 90)]),
        }),
}


def units_of(name):
    d = LIB[name]
    return d["units"] if "units" in d else {1: d}


def lib_symbol_sexp(name):
    out = [f'(symbol "Local:{name}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)',
           f'(property "Reference" "{LIB[name]["prefix"]}" (at 0 0 0) {FONT})',
           f'(property "Value" "{name}" (at 0 0 0) {FONT})',
           f'(property "Footprint" "" (at 0 0 0) {HIDE})',
           f'(property "Datasheet" "" (at 0 0 0) {HIDE})']
    for u, d in units_of(name).items():
        x1, y1, x2, y2 = d["body"]
        out.append(f'(symbol "{name}_{u}_1"')
        out.append(f'(rectangle (start {x1} {y1}) (end {x2} {y2}) '
                   '(stroke (width 0.254) (type default)) (fill (type background)))')
        for num, pname, x, y, a in d["pins"]:
            out.append(f'(pin passive line (at {x} {y} {a}) (length 2.54) '
                       f'(name "{pname}" {FONT}) (number "{num}" {FONT}))')
        out.append(')')
    out.append(')')
    return "\n".join(out)


def label_angle(a):
    return {0: 180, 180: 0, 90: 270, 270: 90}[a]


class Sch:
    def __init__(self):
        self.items = []

    def part(self, ref, value, lib, x, y, nets, unit=1):
        """nets: {ピン番号: ネット名}"""
        d = units_of(lib)[unit]
        s = [f'(symbol (lib_id "Local:{lib}") (at {x} {y} 0) (unit {unit}) '
             f'(in_bom yes) (on_board yes) (dnp no) (uuid {uid()})',
             f'(property "Reference" "{ref}" (at {x + 3} {y - 2} 0) {FONT})',
             f'(property "Value" "{value}" (at {x + 3} {y + 2} 0) {FONT})',
             f'(property "Footprint" "" (at 0 0 0) {HIDE})',
             f'(property "Datasheet" "" (at 0 0 0) {HIDE})']
        for num, *_ in d["pins"]:
            s.append(f'(pin "{num}" (uuid {uid()}))')
        s.append(f'(instances (project "{PROJECT}" (path "/{ROOT}" '
                 f'(reference "{ref}") (unit {unit}))))')
        s.append(')')
        self.items.append("\n".join(s))
        for num, _n, px, py, a in d["pins"]:
            net = nets.get(num)
            if not net:
                continue
            self.label(net, round(x + px, 2), round(y - py, 2), label_angle(a))

    def label(self, net, x, y, a=0):
        self.items.append(
            f'(label "{net}" (at {x} {y} {a}) '
            f'(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid()}))')

    def text(self, s, x, y):
        self.items.append(f'(text "{s}" (at {x} {y} 0) {FONT} (uuid {uid()}))')


def snap(v):
    return round(round(v / 1.27) * 1.27, 2)


def channel(sch, ch, unit, ox, oy, ref_idx):
    """ch: 'L' or 'R'。ネット名は ch 接頭辞で分離。unit: OPA1656 のユニット番号。"""
    n = lambda s: f"{ch}_{s}"
    opin = {1: ("3", "2", "1"), 2: ("5", "6", "7")}[unit]  # (+, -, out)
    P = [
        (f"C{ref_idx}1", "2.2u film", "C", {"1": f"{ch}_IN", "2": n("AC")}),
        (f"RV{ref_idx}", "10k log (2連)", "POT", {"1": n("AC"), "2": "GND", "3": n("W")}),
        (f"R{ref_idx}1", "1k", "R", {"1": n("W"), "2": n("P")}),
        (f"C{ref_idx}2", "220p C0G", "C", {"1": n("P"), "2": "GND"}),
        (f"R{ref_idx}2", "1k", "R", {"1": n("OUT"), "2": n("N")}),
        (f"R{ref_idx}3", "1k", "R", {"1": n("N"), "2": "GND"}),
        (f"R{ref_idx}4", "10", "R", {"1": n("OUT"), "2": f"{ch}_HP"}),
        (f"R{ref_idx}5", "100k", "R", {"1": f"{ch}_HP", "2": "GND"}),
    ]
    for i, (ref, val, lib, nets) in enumerate(P):
        sch.part(ref, val, lib, snap(ox + i * 25.4), snap(oy), nets)
    ay = oy + 30
    sch.part("U1", "OPA1656", "OPA1656", snap(ox + 30), snap(ay),
             {opin[0]: n("P"), opin[1]: n("N"), opin[2]: n("OUT")}, unit=unit)
    sch.text(f"{ch}ch: ゲイン = 1 + R{ref_idx}2/R{ref_idx}3 = 2倍 (+6dB)", snap(ox), snap(oy - 12))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "opa1656_hpa.kicad_sch"
    sch = Sch()
    sch.text("OPA1656 ヘッドホンアンプ (AKG K371 想定, ±15V)", 20, 12)
    sch.text("K371は32Ω/114dB/V と高能率のため、ゲインは+6dB・出力抵抗は10Ωと控えめ", 20, 18)

    # コネクタ
    sch.part("J1", "Audio In (RCA/3.5mm)", "CONN3", 30, 45, {"1": "L_IN", "2": "GND", "3": "R_IN"})
    sch.part("J2", "Headphone Out (TRS 6.3mm)", "CONN3", 30, 85, {"1": "L_HP", "2": "R_HP", "3": "GND"})
    sch.part("J3", "Power +15V/GND/-15V", "CONN3", 30, 125, {"1": "+15V", "2": "GND", "3": "-15V"})
    sch.text("J2: 1=Tip(L) 2=Ring(R) 3=Sleeve(GND)", 20, 135)

    # 左右チャネル
    channel(sch, "L", 1, 80, 55, 1)
    channel(sch, "R", 2, 80, 125, 2)

    # 電源/デカップリング (U1 近傍に 0.1u + 10u を V+/V- 各々)
    sch.part("U1", "OPA1656", "OPA1656", 285, 60, {"8": "+15V", "4": "-15V"}, unit=3)
    sch.part("C11", "0.1u C0G/X7R", "C", 315, 60, {"1": "+15V", "2": "GND"})
    sch.part("C12", "10u", "CP", 335, 60, {"1": "+15V", "2": "GND"})
    sch.part("C13", "0.1u C0G/X7R", "C", 315, 90, {"1": "GND", "2": "-15V"})
    sch.part("C14", "10u", "CP", 335, 90, {"1": "GND", "2": "-15V"})
    # 基板入口のバルクコン
    sch.part("C15", "100u/25V", "CP", 355, 60, {"1": "+15V", "2": "GND"})
    sch.part("C16", "100u/25V", "CP", 355, 90, {"1": "GND", "2": "-15V"})
    sch.text("電源: C14,C16 は極性に注意 (GND側が+)", 300, 105)
    sch.text("RV1: 2連ボリュームの L/R 各ギャング (Lch=RV1, Rch=RV2 として2連扱い)", 20, 150)

    libs = "\n".join(lib_symbol_sexp(n) for n in LIB)
    body = "\n".join(sch.items)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f'(kicad_sch (version 20230121) (generator opa1656_gen)\n'
                f'(uuid {ROOT})\n(paper "A3")\n(lib_symbols\n{libs}\n)\n{body}\n'
                f'(sheet_instances (path "/" (page "1")))\n)\n')
    print("wrote", out)


if __name__ == "__main__":
    main()
