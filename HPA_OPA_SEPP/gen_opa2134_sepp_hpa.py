#!/usr/bin/env python3
"""図5-5 「OPアンプ+SEPP回路ヘッドホン・アンプ」から KiCad 7 の .kicad_sch を生成する。

回路: OPA2134 の出力を、ダイオード・バイアス(D1-D4) + 1000uF ブートストラップで
      Tr1(NPN TTC015B) / Tr2(PNP TTA008B) のSEPPに接続。エミッタ 5.6Ω を経て出力、
      出力から 56k/1.5k + 100uF + 1k で帰還。電源は ±7V。

左右2ch分(OPA2134 の A/B を使用)を生成する。
部品は gen_opa1656_hpa.py と同様に同梱の簡易シンボル(Local:*)を使い、
接続はピン端のネットラベルで表現する。
使い方: python3 gen_opa2134_sepp_hpa.py [出力.kicad_sch]
"""
import sys
import uuid

ROOT = str(uuid.uuid4())
PROJECT = "opa2134_sepp_hpa"
FONT = "(effects (font (size 1.27 1.27)))"
HIDE = "(effects (font (size 1.27 1.27)) hide)"


def uid():
    return str(uuid.uuid4())


def conn(n, names):
    h = 2.54 * n
    return dict(prefix="J", body=(-3.81, -h / 2, 3.81, h / 2),
                pins=[(str(i + 1), names[i], -6.35, round(h / 2 - 1.27 - 2.54 * i, 2), 0)
                      for i in range(n)])


# pins = (番号, 名前, x, y, 角度) シンボル座標系(Y上向き)
# 角度: 0=ピンは左側, 180=右側, 90=下側, 270=上側
LIB = {
    "R": dict(prefix="R", body=(-1.016, -2.54, 1.016, 2.54),
              pins=[("1", "~", 0, 3.81, 270), ("2", "~", 0, -3.81, 90)]),
    "C": dict(prefix="C", body=(-1.27, -0.6, 1.27, 0.6),
              pins=[("1", "~", 0, 3.81, 270), ("2", "~", 0, -3.81, 90)]),
    "CP": dict(prefix="C", body=(-1.27, -0.6, 1.27, 0.6),
               pins=[("1", "+", 0, 3.81, 270), ("2", "-", 0, -3.81, 90)]),
    "D": dict(prefix="D", body=(-1.016, -2.54, 1.016, 2.54),
              pins=[("1", "A", 0, 3.81, 270), ("2", "K", 0, -3.81, 90)]),
    # トランジスタ (NPN/PNP 共通の簡易形): B=ベース C=コレクタ E=エミッタ
    "Q": dict(prefix="Q", body=(-2.54, -2.54, 2.54, 2.54),
              pins=[("1", "B", -5.08, 0, 0), ("2", "C", 0, 6.35, 270),
                    ("3", "E", 0, -6.35, 90)]),
    "CONN1": conn(1, ["1"]),
    # OPA2134: unit1=A(3,2,1) unit2=B(5,6,7) unit3=電源(8,4)
    "OPA2134": dict(
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
            if net:
                self.label(net, round(x + px, 2), round(y - py, 2), label_angle(a))

    def label(self, net, x, y, a=0):
        self.items.append(
            f'(label "{net}" (at {x} {y} {a}) '
            f'(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid()}))')

    def text(self, s, x, y):
        self.items.append(f'(text "{s}" (at {x} {y} 0) {FONT} (uuid {uid()}))')


def channel(sch, ch, unit, ox, base):
    """1ch分。ch='L'/'R'、unit=OPA2134のユニット番号、ox=X方向オフセット、base=部品番号の開始値。"""
    n = lambda x: f"{ch}_{x}"
    r = lambda i: f"R{base + i}"
    c = lambda i: f"C{base + i}"
    opin = {1: ("3", "2", "1"), 2: ("5", "6", "7")}[unit]  # (+, -, out)
    x = lambda v: v + ox

    sch.part(f"J{base + 1}", f"{ch} 入力", "CONN1", x(30), 60, {"1": n("IN")})
    sch.part(c(1), "10uF/50V", "CP", x(60), 60, {"1": n("P"), "2": n("IN")})  # +はOPアンプ側
    sch.part(r(1), "56k", "R", x(90), 80, {"1": n("P"), "2": "GND"})

    sch.part("U1", "OPA2134", "OPA2134", x(130), 60,
             {opin[0]: n("P"), opin[1]: n("N"), opin[2]: n("OUT")}, unit=unit)

    # バイアス: +7V -1k- B1 -D1-D2- OUT -D3-D4- B2 -1k- -7V
    sch.part(r(2), "1k", "R", x(170), 40, {"1": "+7V", "2": n("B1")})
    sch.part(f"D{base + 1}", "1S2076A (SiDi)", "D", x(170), 65, {"1": n("B1"), "2": n("DA")})
    sch.part(f"D{base + 2}", "BAT46/BAT43 (SBD)", "D", x(170), 85, {"1": n("DA"), "2": n("OUT")})
    sch.part(f"D{base + 3}", "1S2076A (SiDi)", "D", x(170), 105, {"1": n("OUT"), "2": n("DB")})
    sch.part(f"D{base + 4}", "BAT46/BAT43 (SBD)", "D", x(170), 125, {"1": n("DB"), "2": n("B2")})
    sch.part(r(3), "1k", "R", x(170), 150, {"1": n("B2"), "2": "-7V"})
    sch.part(c(2), "1000uF/10V", "CP", x(150), 70, {"1": n("B1"), "2": n("OUT")})
    sch.part(c(3), "1000uF/10V", "CP", x(150), 115, {"1": n("OUT"), "2": n("B2")})

    # SEPP出力段
    sch.part(f"Q{base + 1}", "TTC015B (NPN)", "Q", x(200), 55, {"1": n("B1"), "2": "+7V", "3": n("E1")})
    sch.part(f"Q{base + 2}", "TTA008B (PNP)", "Q", x(200), 135, {"1": n("B2"), "2": "-7V", "3": n("E2")})
    sch.part(r(4), "5.6", "R", x(225), 70, {"1": n("E1"), "2": n("HP")})
    sch.part(r(5), "5.6", "R", x(225), 120, {"1": n("HP"), "2": n("E2")})
    sch.part(f"J{base + 2}", f"{ch} ヘッドホン出力", "CONN1", x(260), 95, {"1": n("HP")})

    # 帰還
    sch.part(r(6), "56k", "R", x(110), 175, {"1": n("N"), "2": n("HP")})
    sch.part(r(7), "1.5k", "R", x(130), 190, {"1": n("M"), "2": n("HP")})
    sch.part(c(4), "100uF/10V", "CP", x(95), 175, {"1": n("N"), "2": n("M")})
    sch.part(r(8), "1k", "R", x(95), 205, {"1": n("M"), "2": "GND"})


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "opa2134_sepp_hpa.kicad_sch"
    sch = Sch()
    sch.text("OPアンプ+SEPP回路 ステレオ・ヘッドホン・アンプ (図5-5 x2ch) ±7V", 20, 12)

    channel(sch, "L", 1, 0, 0)     # U1A, 部品番号 1x
    channel(sch, "R", 2, 300, 10)  # U1B, 部品番号 1xの次(11〜)

    # 電源 (左右共通)
    sch.part("U1", "OPA2134", "OPA2134", 640, 60, {"8": "+7V", "4": "-7V"}, unit=3)
    sch.part("J20", "+7V", "CONN1", 640, 20, {"1": "+7V"})
    sch.part("J21", "-7V", "CONN1", 640, 100, {"1": "-7V"})
    sch.part("J22", "GND", "CONN1", 640, 120, {"1": "GND"})
    sch.part("C30", "4700uF/16V", "CP", 670, 45, {"1": "+7V", "2": "GND"})
    sch.part("C31", "4700uF/16V", "CP", 670, 100, {"1": "GND", "2": "-7V"})
    sch.text("Tr1: TTC015B / Tr2: TTA008B / D1,D3: 1S2076A / D2,D4: BAT46 or BAT43", 20, 235)
    sch.text("Q: 1=B 2=C 3=E (簡易シンボル)。Lch 部品番号 1x / Rch 部品番号 11〜 (U1A=Lch, U1B=Rch)", 20, 241)

    libs = "\n".join(lib_symbol_sexp(n) for n in LIB)
    body = "\n".join(sch.items)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f'(kicad_sch (version 20230121) (generator opa2134_sepp_gen)\n'
                f'(uuid {ROOT})\n(paper "A3")\n(lib_symbols\n{libs}\n)\n{body}\n'
                f'(sheet_instances (path "/" (page "1")))\n)\n')
    print("wrote", out)


if __name__ == "__main__":
    main()
