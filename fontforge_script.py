#!fontforge --lang=py -script

# 2つのフォントを合成する

import configparser
import os
import shutil
import sys
import uuid
from decimal import ROUND_HALF_UP, Decimal
from math import radians

import fontforge
import psMat

# iniファイルを読み込む
settings = configparser.ConfigParser()
settings.read("build.ini", encoding="utf-8")

VERSION = settings.get("DEFAULT", "VERSION")
FONT_NAME = settings.get("DEFAULT", "FONT_NAME")
JP_FONT = settings.get("DEFAULT", "JP_FONT")
ENG_FONT = settings.get("DEFAULT", "ENG_FONT")
SOURCE_FONTS_DIR = settings.get("DEFAULT", "SOURCE_FONTS_DIR")
BUILD_FONTS_DIR = settings.get("DEFAULT", "BUILD_FONTS_DIR")
VENDER_NAME = settings.get("DEFAULT", "VENDER_NAME")
FONTFORGE_PREFIX = settings.get("DEFAULT", "FONTFORGE_PREFIX")
IDEOGRAPHIC_SPACE = settings.get("DEFAULT", "IDEOGRAPHIC_SPACE")
DISCORD_STR = settings.get("DEFAULT", "DISCORD_STR")
WIDTH_35_STR = settings.get("DEFAULT", "WIDTH_35_STR")
INVISIBLE_ZENKAKU_SPACE_STR = settings.get("DEFAULT", "INVISIBLE_ZENKAKU_SPACE_STR")
JPDOC_STR = settings.get("DEFAULT", "JPDOC_STR")
NERD_FONTS_STR = settings.get("DEFAULT", "NERD_FONTS_STR")
EM_ASCENT = int(settings.get("DEFAULT", "EM_ASCENT"))
EM_DESCENT = int(settings.get("DEFAULT", "EM_DESCENT"))
OS2_ASCENT = int(settings.get("DEFAULT", "OS2_ASCENT"))
OS2_DESCENT = int(settings.get("DEFAULT", "OS2_DESCENT"))
HALF_WIDTH_12 = int(settings.get("DEFAULT", "HALF_WIDTH_12"))
FULL_WIDTH_35 = int(settings.get("DEFAULT", "FULL_WIDTH_35"))
JP_SCALE = Decimal(settings.get("DEFAULT", "JP_SCALE"))

COPYRIGHT = """[Inconsolata]
Copyright 2006 The Inconsolata Project Authors https://github.com/googlefonts/Inconsolata

[BIZ UDGothic]
Copyright 2022 The BIZ UDGothic Project Authors https://github.com/googlefonts/morisawa-biz-ud-gothic

[Nerd Fonts]
Copyright (c) 2014, Ryan L McIntyre https://ryanlmcintyre.com

[Bizin Gothic]
Copyright 2022 Yuko Otawara
"""  # noqa: E501

options = {}
hack_font = None
nerd_font = None


def main():
    # オプション判定
    get_options()
    if options.get("unknown-option"):
        usage()
        return

    # buildディレクトリを作成する
    if os.path.exists(BUILD_FONTS_DIR) and not options.get("do-not-delete-build-dir"):
        shutil.rmtree(BUILD_FONTS_DIR)
        os.mkdir(BUILD_FONTS_DIR)
    if not os.path.exists(BUILD_FONTS_DIR):
        os.mkdir(BUILD_FONTS_DIR)

    generate_font(
        jp_style="Regular",
        eng_style="Medium",
        merged_style="Regular",
    )
    generate_font(
        jp_style="Bold",
        eng_style="Bold",
        merged_style="Bold",
    )


def usage():
    print(
        f"Usage: {sys.argv[0]} "
        "[--invisible-zenkaku-space] [--35] [--jpdoc] [--nerd-font]"
    )


def get_options():
    """オプションを取得する"""

    global options

    # オプションなしの場合は何もしない
    if len(sys.argv) == 1:
        return

    for arg in sys.argv[1:]:
        # オプション判定
        if arg == "--do-not-delete-build-dir":
            options["do-not-delete-build-dir"] = True
        elif arg == "--invisible-zenkaku-space":
            options["invisible-zenkaku-space"] = True
        elif arg == "--35":
            options["35"] = True
        elif arg == "--nerd-font":
            options["nerd-font"] = True
        elif arg == "--discord":
            options["discord"] = True
        elif arg.startswith("--discord-ignore="):
            options["discord-ignore-char-list"] = arg.split("=")[1]
        else:
            options["unknown-option"] = True
            return


def generate_font(jp_style, eng_style, merged_style):
    print(f"=== Generate {merged_style} ===")

    # 合成するフォントを開く
    jp_font, eng_font = open_fonts(jp_style, eng_style)

    # フォントのEMを揃える
    adjust_em(eng_font)

    # 日本語文書に頻出する記号を英語フォントから削除する
    if not options.get("nerd-font"):
        remove_jpdoc_symbols(eng_font)

    # いくつかのグリフ形状に調整を加える
    adjust_some_glyph(jp_font, jp_style, eng_font, eng_style)

    # Discord用の調整
    if options.get("discord"):
        create_discord(eng_font, jp_font, jp_style)

    # 重複するグリフを削除する
    delete_duplicate_glyphs(jp_font, eng_font)

    # 日本語フォントのスケールを調整する
    shrink_jp_font(jp_font)

    # GSUB, GPOS テーブル調整
    remove_lookups(jp_font, remove_gsub=False, remove_gpos=True)

    # inconsolata 連続するバッククォートで grave.case が使われるのを防ぐ
    for lookup in eng_font.gsub_lookups:
        if "ccmp" in lookup:
            eng_font.removeLookup(lookup)

    # 全角スペースを可視化する
    if not options.get("invisible-zenkaku-space"):
        visualize_zenkaku_space(jp_font)

    if options.get("nerd-font"):
        # East Asian Ambiguous Width のグリフを半角幅に縮小する
        shrink_east_asian_ambiguous_width(jp_font)
        # Nerd Fontのグリフを追加する
        add_nerd_font_glyphs(jp_font, eng_font)

    # オプション毎の修飾子を追加する
    variant = f"{DISCORD_STR} " if options.get("discord") else ""
    variant += WIDTH_35_STR if options.get("35") else ""
    variant += (
        INVISIBLE_ZENKAKU_SPACE_STR if options.get("invisible-zenkaku-space") else ""
    )
    variant += JPDOC_STR if options.get("jpdoc") else ""
    variant += NERD_FONTS_STR if options.get("nerd-font") else ""
    variant = variant.strip()

    # macOSでのpostテーブルの使用性エラー対策
    # 重複するグリフ名を持つグリフをリネームする
    delete_glyphs_with_duplicate_glyph_names(eng_font)
    delete_glyphs_with_duplicate_glyph_names(jp_font)

    # メタデータを編集する
    cap_height = int(
        Decimal(str(eng_font[0x0048].boundingBox()[3])).quantize(
            Decimal("0"), ROUND_HALF_UP
        )
    )
    x_height = int(
        Decimal(str(eng_font[0x0078].boundingBox()[3])).quantize(
            Decimal("0"), ROUND_HALF_UP
        )
    )
    edit_meta_data(eng_font, merged_style, variant, cap_height, x_height)
    edit_meta_data(jp_font, merged_style, variant, cap_height, x_height)

    # ttfファイルに保存
    # ヒンティングはあとで ttfautohint で行う。
    # flags=("no-hints", "omit-instructions") を使うとヒンティングだけでなく GPOS や GSUB も削除されてしまうので使わない
    eng_font.generate(
        f"{BUILD_FONTS_DIR}/{FONTFORGE_PREFIX}{FONT_NAME}{variant.replace(' ', '')}-{merged_style}-eng.ttf",
    )
    jp_font.generate(
        f"{BUILD_FONTS_DIR}/{FONTFORGE_PREFIX}{FONT_NAME}{variant.replace(' ', '')}-{merged_style}-jp.ttf",
    )

    # ttfを閉じる
    jp_font.close()
    eng_font.close()


def open_fonts(jp_style: str, eng_style: str):
    """フォントを開く"""
    jp_font = fontforge.open(
        SOURCE_FONTS_DIR + "/" + JP_FONT.replace("{style}", jp_style)
    )
    eng_font = fontforge.open(
        SOURCE_FONTS_DIR + "/" + ENG_FONT.replace("{style}", eng_style)
    )

    # fonttools merge エラー対処
    jp_font = altuni_to_entity(jp_font)

    # フォント参照を解除する
    for glyph in jp_font.glyphs():
        if glyph.isWorthOutputting():
            jp_font.selection.select(("more", None), glyph)
    jp_font.unlinkReferences()
    for glyph in eng_font.glyphs():
        if glyph.isWorthOutputting():
            eng_font.selection.select(("more", None), glyph)
    eng_font.unlinkReferences()
    jp_font.selection.none()
    eng_font.selection.none()

    return jp_font, eng_font


def altuni_to_entity(jp_font):
    """Alternate Unicodeで透過的に参照して表示している箇所を実体のあるグリフに変換する"""
    for glyph in jp_font.glyphs():
        if glyph.altuni is not None:
            # 以下形式のタプルで返ってくる
            # (unicode-value, variation-selector, reserved-field)
            # 第3フィールドは常に0なので無視
            altunis = glyph.altuni

            # variation-selectorがなく (-1)、透過的にグリフを参照しているものは実体のグリフに変換する
            before_altuni = ""
            for altuni in altunis:
                # 直前のaltuniと同じ場合はスキップ
                if altuni[1] == -1 and before_altuni != ",".join(map(str, altuni)):
                    glyph.altuni = None
                    copy_target_unicode = altuni[0]
                    try:
                        copy_target_glyph = jp_font.createChar(
                            copy_target_unicode,
                            f"uni{hex(copy_target_unicode).replace('0x', '').upper()}copy",
                        )
                    except Exception:
                        copy_target_glyph = jp_font[copy_target_unicode]
                    copy_target_glyph.clear()
                    copy_target_glyph.width = glyph.width
                    # copy_target_glyph.addReference(glyph.glyphname)
                    jp_font.selection.select(glyph.glyphname)
                    jp_font.copy()
                    jp_font.selection.select(copy_target_glyph.glyphname)
                    jp_font.paste()
                before_altuni = ",".join(map(str, altuni))
    # エンコーディングの整理のため、開き直す
    font_path = f"{BUILD_FONTS_DIR}/{jp_font.fullname}_{uuid.uuid4()}.ttf"
    jp_font.generate(font_path)
    jp_font.close()
    reopen_jp_font = fontforge.open(font_path)
    # 一時ファイルを削除
    os.remove(font_path)
    return reopen_jp_font


def adjust_some_glyph(jp_font, jp_style, eng_font, eng_style):
    """いくつかのグリフ形状に調整を加える"""
    # 全角括弧の開きを広くする
    full_width = jp_font[0x3042].width
    for glyph_name in [0xFF08, 0xFF3B, 0xFF5B]:
        glyph = jp_font[glyph_name]
        glyph.transform(psMat.translate(-(full_width / 6), 0))
        glyph.width = full_width
    for glyph_name in [0xFF09, 0xFF3D, 0xFF5D]:
        glyph = jp_font[glyph_name]
        glyph.transform(psMat.translate((full_width / 6), 0))
        glyph.width = full_width
    # LEFT SINGLE QUOTATION MARK (U+2018) ～ DOUBLE LOW-9 QUOTATION MARK (U+201E) の幅を全角幅にする
    for uni in range(0x2018, 0x201E + 1):
        try:
            glyph = jp_font[uni]
            if glyph.isWorthOutputting():
                glyph.transform(psMat.translate((full_width - glyph.width) / 2, 0))
                glyph.width = full_width
        except TypeError:
            # グリフが存在しない場合は継続する
            continue
    jp_font.selection.none()

    # シングルクォート、ダブルクォートを大きくする
    for glyph_name in [0x0027, 0x0022]:
        glyph = eng_font[glyph_name]
        scale_glyph(glyph, 1.1, 1)
    # コロン、セミコロン、カンマ、ドットを大きくする
    for glyph_name in [0x003A, 0x003B, 0x002C, 0x002E]:
        glyph = eng_font[glyph_name]
        scale_glyph(glyph, 1.1, 1.1)
    # バッククォートを大きくする
    for glyph_name in [0x0060]:
        glyph = eng_font[glyph_name]
        rotate_glyph(glyph, -32)
        scale_glyph(glyph, 1.1, 1.25)
        rotate_glyph(glyph, 37)
    # ハイフンを広げる
    hyphen = eng_font[0x002D]
    scale_glyph(hyphen, 1.2, 1)
    # プラスを大きくする
    for glyph_name in [0x002B]:
        glyph = eng_font[glyph_name]
        scale_glyph(glyph, 1, 1.15)
    # 波ダッシュを垂直に反転
    tilde = jp_font[0x301C]
    inverse_glyph(tilde)
    # 英語フォントにカスタムグリフを適用する
    # - チルダを調整
    tilde = eng_font[0x007E]
    tilde.clear()
    eng_font.mergeFonts(f"{SOURCE_FONTS_DIR}/inconsolata/custom_glyphs-{eng_style}.sfd")
    eng_font.selection.none()
    # 日本語フォントにカスタムグリフを適用する
    # - ぱぴぷぺぽ パピプペポ の半濁点を調整 20%拡大
    for uni in [
        0x3071,
        0x3074,
        0x3077,
        0x307A,
        0x307D,
        0x30D1,
        0x30D4,
        0x30D7,
        0x30DA,
        0x30DD,
    ]:
        glyph = jp_font[uni]
        glyph.clear()
    jp_font.mergeFonts(f"{SOURCE_FONTS_DIR}/biz-ud-gothic/custom_glyphs-{jp_style}.sfd")


def scale_glyph(glyph, scale_x, scale_y):
    """グリフのスケールを調整する"""
    original_width = glyph.width
    # スケール前の中心位置を求める
    before_bb = glyph.boundingBox()
    before_center_x = (before_bb[0] + before_bb[2]) / 2
    before_center_y = (before_bb[1] + before_bb[3]) / 2
    # スケール変換
    glyph.transform(psMat.scale(scale_x, scale_y))
    # スケール後の中心位置を求める
    after_bb = glyph.boundingBox()
    after_center_x = (after_bb[0] + after_bb[2]) / 2
    after_center_y = (after_bb[1] + after_bb[3]) / 2
    # 拡大で増えた分を考慮して中心位置を調整
    glyph.transform(
        psMat.translate(
            before_center_x - after_center_x,
            before_center_y - after_center_y,
        )
    )
    glyph.width = original_width


def rotate_glyph(glyph, degree):
    """グリフを回転する"""
    # 原点が中央になるように寄せる
    bb = glyph.boundingBox()
    center_x = (bb[0] + bb[2]) / 2
    center_y = (bb[1] + bb[3]) / 2
    to_origin = psMat.translate(-center_x, -center_y)
    # 回転して戻す
    translate_compose = psMat.compose(
        to_origin,
        psMat.compose(psMat.rotate(radians(degree)), psMat.inverse(to_origin)),
    )
    glyph.transform(translate_compose)


def inverse_glyph(glyph):
    """グリフを反転する"""
    before_bb = glyph.boundingBox()
    before_top_y = before_bb[1]
    glyph.transform(psMat.scale(1, -1))
    after_bb = glyph.boundingBox()
    after_top_y = after_bb[1]
    glyph.transform(psMat.translate(0, before_top_y - after_top_y))


def create_discord(eng_font, jp_font, jp_style):
    """Discord用の調整を行う"""
    # Discord用の調整
    discord_char_list = "07DZlrz|"
    if options.get("discord-ignore-char-list"):
        for char in options.get("discord-ignore-char-list"):
            discord_char_list = discord_char_list.replace(char, "")

    if "0" in discord_char_list:
        eng_font.selection.select("zero.zero")
        eng_font.copy()
        eng_font.selection.select("zero")
        eng_font.paste()
    if "7" in discord_char_list:
        # macron を一時的に退避して編集をかける
        eng_font.selection.select("U+00AF")
        eng_font.copy()
        eng_font.selection.select("U+FFFF")
        eng_font.paste()
        for glyph in eng_font.selection.byGlyphs:
            glyph.transform(psMat.translate(55, -550), ("round",))
        eng_font.copy()
        # 7 に編集をかける
        eng_font.selection.select("7")
        eng_font.pasteInto()
        for glyph in eng_font.selection.byGlyphs:
            glyph.removeOverlap()
        eng_font.selection.select("U+FFFF")
        eng_font.clear()
    if "D" in discord_char_list:
        eng_font.selection.select("U+00D0")
        eng_font.copy()
        eng_font.selection.select("D")
        eng_font.paste()
    if "Z" in discord_char_list:
        # macron を一時的に退避して編集をかける
        eng_font.selection.select("U+00AF")
        eng_font.copy()
        eng_font.selection.select("U+FFFF")
        eng_font.paste()
        for glyph in eng_font.selection.byGlyphs:
            rotate_glyph(glyph, -31)
            # 移動
            glyph.transform(psMat.translate(20, -560))
        eng_font.copy()
        # Z に編集をかける
        eng_font.selection.select("Z")
        eng_font.pasteInto()
        for glyph in eng_font.selection.byGlyphs:
            glyph.removeOverlap()
        eng_font.selection.select("U+FFFF")
        eng_font.clear()
    if "l" in discord_char_list:
        eng_font.selection.select("l")
        eng_font.copy()
        for glyph in eng_font.selection.byGlyphs:
            rotate_glyph(glyph, 180)
        eng_font.pasteInto()
        for glyph in eng_font.selection.byGlyphs:
            glyph.intersect()
    if "r" in discord_char_list:
        eng_font.selection.select("r.serif")
        eng_font.copy()
        eng_font.selection.select("r")
        eng_font.paste()
    if "z" in discord_char_list:
        # macron を一時的に退避して編集をかける
        eng_font.selection.select("U+00AF")
        eng_font.copy()
        eng_font.selection.select("U+FFFF")
        eng_font.paste()
        for glyph in eng_font.selection.byGlyphs:
            rotate_glyph(glyph, -37)
            # 移動
            glyph.transform(psMat.translate(0, -745))
        eng_font.copy()
        # z に編集をかける
        eng_font.selection.select("z")
        eng_font.pasteInto()
        for glyph in eng_font.selection.byGlyphs:
            glyph.removeOverlap()
        eng_font.selection.select("U+FFFF")
        eng_font.clear()
    if "|" in discord_char_list:
        eng_font.selection.select("U+00A6")
        eng_font.copy()
        eng_font.selection.select("U+007C")
        eng_font.paste()

    eng_font.selection.none()

    # シングルクォート、ダブルクォートをさらに大きくする
    for glyph_name in [0x0027, 0x0022]:
        glyph = eng_font[glyph_name]
        scale_glyph(glyph, 1.1, 1.1)
    # セミコロン、コロン、カンマ、ドットをさらに大きくする
    for glyph_name in [0x003A, 0x003B, 0x002C, 0x002E]:
        glyph = eng_font[glyph_name]
        scale_glyph(glyph, 1.1, 1.1)
    # バッククォートをさらに大きくする
    for glyph_name in [0x0060]:
        glyph = eng_font[glyph_name]
        rotate_glyph(glyph, -37)
        scale_glyph(glyph, 1, 1.3)
        rotate_glyph(glyph, 37)
        glyph.transform(psMat.translate(0, -80))
    # ハット、アスタリスクを大きくする
    for glyph_name in [0x005E, 0x002A]:
        glyph = eng_font[glyph_name]
        scale_glyph(glyph, 1.15, 1.15)

    # 日本語フォントにカスタムグリフを適用する
    # - ぱぴぷぺぽ パピプペポ の半濁点を調整 30%拡大
    # - カタカナ ヘペベ に特徴付け
    # - カ力 エ工 ロ口 ー一 ニ二 のグリフに特徴付け
    for uni in [
        0x3071,
        0x3074,
        0x3077,
        0x307A,
        0x307D,
        0x30D1,
        0x30D4,
        0x30D7,
        0x30DA,
        0x30DD,
        0x30D8,
        0x30D9,
        0x529B,
        0x5DE5,
        0x53E3,
        0x30FC,
        0x4E00,
        0x4E8C,
    ]:
        glyph = jp_font[uni]
        glyph.clear()
    jp_font.mergeFonts(
        f"{SOURCE_FONTS_DIR}/biz-ud-gothic/custom_glyphs_discord-{jp_style}.sfd"
    )


def adjust_em(font):
    """フォントのEMを揃える"""
    font.em = EM_ASCENT + EM_DESCENT


def delete_duplicate_glyphs(jp_font, eng_font):
    """jp_fontとeng_fontのグリフを比較し、重複するグリフを削除する"""

    eng_font.selection.none()
    jp_font.selection.none()

    for glyph in jp_font.glyphs("encoding"):
        try:
            if glyph.isWorthOutputting() and glyph.unicode > 0:
                eng_font.selection.select(("more", "unicode"), glyph.unicode)
        except ValueError:
            # Encoding is out of range のときは継続する
            continue
    for glyph in eng_font.selection.byGlyphs:
        # if glyph.isWorthOutputting():
        jp_font.selection.select(("more", "unicode"), glyph.unicode)
    for glyph in jp_font.selection.byGlyphs:
        glyph.clear()

    jp_font.selection.none()
    eng_font.selection.none()


def shrink_jp_font(jp_font):
    """日本語フォントを縮小する"""
    for glyph in jp_font.glyphs():
        if glyph.isWorthOutputting():
            original_width = glyph.width
            # スケール縮小
            glyph.transform(psMat.scale(JP_SCALE, JP_SCALE))
            # 中心位置に移動する
            glyph.transform(psMat.translate((original_width - glyph.width) / 2, 0))
            # 幅を元に戻す
            glyph.width = original_width


def remove_lookups(font, remove_gsub=True, remove_gpos=True):
    """GSUB, GPOSテーブルを削除する"""
    if remove_gsub:
        for lookup in font.gsub_lookups:
            font.removeLookup(lookup)
    if remove_gpos:
        for lookup in font.gpos_lookups:
            font.removeLookup(lookup)


def shrink_east_asian_ambiguous_width(jp_font):
    """East Asian Ambiguous Width のグリフを半角幅に縮小する"""
    # ref: Unicode East Asian Ambiguous Width: https://www.unicode.org/Public/15.0.0/ucd/EastAsianWidth.txt

    # 半分に縮小するグリフ
    for uni in [
        *range(
            0x01CD, 0x01DC
        ),  # LATIN CAPITAL LETTER A WITH CARON..LATIN CAPITAL LETTER U WITH DIAERESIS
        *range(
            0x0386, 0x03CF + 1
        ),  # GREEK CAPITAL LETTER ALPHA WITH TONOS..GREEK SMALL LETTER OMEGA WITH DASIA
        *range(
            0x0401, 0x044F + 1
        ),  # CYRILLIC CAPITAL LETTER IO..CYRILLIC SMALL LETTER YA
        *range(
            0x0451, 0x045F + 1
        ),  # CYRILLIC SMALL LETTER IO..CYRILLIC SMALL LETTER DZHE
        0x2025,  # TWO DOT LEADER
        0x203B,  # REFERENCE MARK
        0x2103,  # DEGREE CELSIUS
        *range(0x2121, 0x2122 + 1),  # TELEPHONE SIGN..TRADE MARK SIGN
        0x212B,  # ANGSTROM SIGN
        *range(0x213A, 0x213B + 1),  # ROTATED CAPITAL Q..FACSIMILE SIGN
        *range(0x2160, 0x216B + 1),  # ROMAN NUMERAL ONE..ROMAN NUMERAL TWELVE
        *range(
            0x2170, 0x217B + 1
        ),  # SMALL ROMAN NUMERAL ONE..SMALL ROMAN NUMERAL TWELVE
        0x2200,  # FOR ALL
        *range(0x2202, 0x2203 + 1),  # PARTIAL DIFFERENTIAL..THERE EXISTS
        *range(0x2207, 0x2208 + 1),  # NABLA..ELEMENT OF
        0x220B,  # CONTAINS AS MEMBER
        *range(0x221F, 0x2220 + 1),  # RIGHT ANGLE..ANGLE
        *range(0x2225, 0x222C + 1),  # PARALLEL TO..DOUBLE INTEGRAL
        0x222E,  # CONTOUR INTEGRAL
        *range(0x2234, 0x2235 + 1),  # THEREFORE..BECAUSE
        0x2252,  # APPROXIMATELY EQUAL TO OR THE IMAGE OF
        0x2261,  # IDENTICAL TO
        *range(
            0x2266, 0x2267 + 1
        ),  # LESS-THAN OVER EQUAL TO..GREATER-THAN OVER EQUAL TO
        *range(0x226A, 0x226B + 1),  # MUCH LESS-THAN..MUCH GREATER-THAN
        *range(0x2282, 0x2283 + 1),  # SUBSET OF..SUPERSET OF
        *range(0x2286, 0x2287 + 1),  # SUBSET OF OR EQUAL TO..SUPERSET OF OR EQUAL TO
        0x22A5,  # UP TACK
        *range(0x2460, 0x24FF + 1),  # CIRCLED DIGIT ONE..NEGATIVE CIRCLED DIGIT TEN
        *range(0x25A0, 0x25A1 + 1),  # BLACK SQUARE..WHITE SQUARE
        *range(
            0x25B2, 0x25B3 + 1
        ),  # BLACK UP-POINTING TRIANGLE..WHITE UP-POINTING TRIANGLE
        *range(
            0x25BC, 0x25BD + 1
        ),  # BLACK DOWN-POINTING TRIANGLE..WHITE DOWN-POINTING TRIANGLE
        0x25CE,  # BULLSEYE
        0x25EF,  # LARGE CIRCLE
        *range(0x2605, 0x2606 + 1),  # BLACK STAR..WHITE STAR
        0x260E,  # BLACK TELEPHONE
        0x2640,  # FEMALE SIGN
        0x2642,  # MALE SIGN
        *range(0x2668, 0x266F + 1),  # HOT SPRINGS..MUSIC SHARP SIGN
        0x2756,  # BLACK DIAMOND MINUS WHITE X
        *range(
            0x2776, 0x277F + 1
        ),  # DINGBAT NEGATIVE CIRCLED DIGIT ONE..DINGBAT NEGATIVE CIRCLED NUMBER TEN
        0x27A1,  # BLACK RIGHTWARDS ARROW
        0x29BF,  # CIRCLED BULLET
        0x1F100,  # DIGIT ZERO FULL STOP
    ]:
        try:
            glyph = jp_font[uni]
            if glyph.isWorthOutputting() and glyph.width == HALF_WIDTH_12 * 2:
                before_width = glyph.width
                scale_glyph(glyph, 0.6, 1)
                glyph.transform(psMat.translate((HALF_WIDTH_12 - before_width) / 2, 0))
                glyph.width = HALF_WIDTH_12
        except Exception:
            continue

    # 半分の幅にしても収まるために幅を半分に位置調整だけするグリフ
    for uni in [0x2016]:  # DOUBLE VERTICAL LINE
        try:
            glyph = jp_font[uni]
            if glyph.isWorthOutputting() and glyph.width == HALF_WIDTH_12 * 2:
                glyph.transform(psMat.translate((HALF_WIDTH_12 - glyph.width) / 2, 0))
                glyph.width = HALF_WIDTH_12
        except Exception:
            continue

    # 文字が潰れて見えなくなってしまうため、縮小なし、位置移動なしで幅だけ半角にするグリフ
    for uni in [
        *range(0x2600, 0x2603 + 1),  # BLACK SUN WITH RAYS..SNOWMAN
        *range(
            0x261C, 0x261F + 1
        ),  # WHITE LEFT POINTING INDEX..WHITE DOWN POINTING INDEX
    ]:
        try:
            glyph = jp_font[uni]
            if glyph.isWorthOutputting() and glyph.width == HALF_WIDTH_12 * 2:
                glyph.width = HALF_WIDTH_12
        except Exception:
            continue

    # 半分の幅にしつつ、潰れないように縦には広げるグリフ
    for uni in [
        0x21D2,  # RIGHTWARDS DOUBLE ARROW
        0x21D4,  # LEFT RIGHT DOUBLE ARROW
        0x221D,  # PROPORTIONAL TO
        0x223D,  # REVERSED TILDE
    ]:
        try:
            glyph = jp_font[uni]
            if glyph.isWorthOutputting() and glyph.width == HALF_WIDTH_12 * 2:
                before_width = glyph.width
                scale_glyph(glyph, 0.6, 1.25)
                glyph.transform(psMat.translate((HALF_WIDTH_12 - before_width) / 2, 0))
                glyph.width = HALF_WIDTH_12
        except Exception:
            continue


def remove_jpdoc_symbols(eng_font):
    """日本語文書に頻出する記号を削除する"""
    eng_font.selection.none()
    # § (U+00A7)
    eng_font.selection.select(("more", "unicode"), 0x00A7)
    # ± (U+00B1)
    eng_font.selection.select(("more", "unicode"), 0x00B1)
    # ¶ (U+00B6)
    eng_font.selection.select(("more", "unicode"), 0x00B6)
    # ÷ (U+00F7)
    eng_font.selection.select(("more", "unicode"), 0x00F7)
    # × (U+00D7)
    eng_font.selection.select(("more", "unicode"), 0x00D7)
    # ⇒ (U+21D2)
    eng_font.selection.select(("more", "unicode"), 0x21D2)
    # ⇔ (U+21D4)
    eng_font.selection.select(("more", "unicode"), 0x21D4)
    # ■-□ (U+25A0-U+25A1)
    eng_font.selection.select(("more", "ranges"), 0x25A0, 0x25A1)
    # ▲-△ (U+25B2-U+25B3)
    eng_font.selection.select(("more", "ranges"), 0x25A0, 0x25B3)
    # ▼-▽ (U+25BC-U+25BD)
    eng_font.selection.select(("more", "ranges"), 0x25BC, 0x25BD)
    # ◆-◇ (U+25C6-U+25C7)
    eng_font.selection.select(("more", "ranges"), 0x25C6, 0x25C7)
    # ○ (U+25CB)
    eng_font.selection.select(("more", "unicode"), 0x25CB)
    # ◎-● (U+25CE-U+25CF)
    eng_font.selection.select(("more", "ranges"), 0x25CE, 0x25CF)
    # ◥ (U+25E5)
    eng_font.selection.select(("more", "unicode"), 0x25E5)
    # ◯ (U+25EF)
    eng_font.selection.select(("more", "unicode"), 0x25EF)
    # √ (U+221A)
    eng_font.selection.select(("more", "unicode"), 0x221A)
    # ∞ (U+221E)
    eng_font.selection.select(("more", "unicode"), 0x221E)
    # ‐ (U+2010)
    eng_font.selection.select(("more", "unicode"), 0x2010)
    # ‘-‚ (U+2018-U+201A)
    eng_font.selection.select(("more", "ranges"), 0x2018, 0x201A)
    # “-„ (U+201C-U+201E)
    eng_font.selection.select(("more", "ranges"), 0x201C, 0x201E)
    # †-‡ (U+2020-U+2021)
    eng_font.selection.select(("more", "ranges"), 0x2020, 0x2021)
    # … (U+2026)
    eng_font.selection.select(("more", "unicode"), 0x2026)
    # ‰ (U+2030)
    eng_font.selection.select(("more", "unicode"), 0x2030)
    # ←-↓ (U+2190-U+2193)
    eng_font.selection.select(("more", "ranges"), 0x2190, 0x2193)
    # ∀ (U+2200)
    eng_font.selection.select(("more", "unicode"), 0x2200)
    # ∂-∃ (U+2202-U+2203)
    eng_font.selection.select(("more", "ranges"), 0x2202, 0x2203)
    # ∈ (U+2208)
    eng_font.selection.select(("more", "unicode"), 0x2208)
    # ∋ (U+220B)
    eng_font.selection.select(("more", "unicode"), 0x220B)
    # ∑ (U+2211)
    eng_font.selection.select(("more", "unicode"), 0x2211)
    # ∥ (U+2225)
    eng_font.selection.select(("more", "unicode"), 0x2225)
    # ∧-∬ (U+2227-U+222C)
    eng_font.selection.select(("more", "ranges"), 0x2227, 0x222C)
    # ≠-≡ (U+2260-U+2261)
    eng_font.selection.select(("more", "ranges"), 0x2260, 0x2261)
    # ⊂-⊃ (U+2282-U+2283)
    eng_font.selection.select(("more", "ranges"), 0x2282, 0x2283)
    # ⊆-⊇ (U+2286-U+2287)
    eng_font.selection.select(("more", "ranges"), 0x2286, 0x2287)
    # ─-╿ (Box Drawing) (U+2500-U+257F)
    eng_font.selection.select(("more", "ranges"), 0x2500, 0x257F)
    for glyph in eng_font.selection.byGlyphs:
        if glyph.isWorthOutputting():
            glyph.clear()
    eng_font.selection.none()


def visualize_zenkaku_space(jp_font):
    """全角スペースを可視化する"""
    # 全角スペースを差し替え
    glyph = jp_font[0x3000]
    width_to = glyph.width
    glyph.clear()
    jp_font.mergeFonts(fontforge.open(f"{SOURCE_FONTS_DIR}/{IDEOGRAPHIC_SPACE}"))
    # 幅を設定し位置調整
    jp_font.selection.select("U+3000")
    for glyph in jp_font.selection.byGlyphs:
        width_from = glyph.width
        glyph.transform(psMat.translate((width_to - width_from) / 2, 0))
        glyph.width = width_to
    jp_font.selection.none()


def add_box_drawing_block_elements(jp_font, eng_font):
    """Box Drawing, Block Elements を追加する"""
    global hack_font
    if hack_font is None:
        hack_font = fontforge.open(f"{SOURCE_FONTS_DIR}/hack/Hack-Regular.ttf")
        hack_font.em = EM_ASCENT + EM_DESCENT
        half_width = eng_font[0x0030].width
        # 対象記号を選択
        for uni in range(0x2500, 0x259F + 1):
            hack_font.selection.select(("more", "unicode"), uni)
        # マージする記号のみを残す
        hack_font.selection.invert()
        for glyph in hack_font.selection.byGlyphs:
            hack_font.removeGlyph(glyph)
        # 位置合わせ
        for glyph in hack_font.glyphs():
            if glyph.isWorthOutputting():
                glyph.transform(psMat.translate((half_width - glyph.width) / 2, 0))
                glyph.width = half_width
    # マージする範囲をあらかじめ削除
    eng_font.selection.none()
    for uni in range(0x2500, 0x259F + 1):
        try:
            eng_font.selection.select(("more", "unicode"), uni)
        except Exception:
            pass
    for glyph in eng_font.selection.byGlyphs:
        glyph.clear()
    # jpdoc 版の場合は罫線を日本語フォント優先にする
    if not options.get("jpdoc"):
        jp_font.selection.none()
        for uni in range(0x2500, 0x259F + 1):
            try:
                jp_font.selection.select(("more", "unicode"), uni)
            except Exception:
                pass
        for glyph in jp_font.selection.byGlyphs:
            glyph.clear()
    jp_font.mergeFonts(hack_font)


def add_nerd_font_glyphs(jp_font, eng_font):
    """Nerd Fontのグリフを追加する"""
    global nerd_font
    # Nerd Fontのグリフを追加する
    if nerd_font is None:
        nerd_font = fontforge.open(f"{SOURCE_FONTS_DIR}/SymbolsNerdFont-Regular.ttf")
        nerd_font.em = EM_ASCENT + EM_DESCENT
        glyph_names = set()
        for nerd_glyph in nerd_font.glyphs():
            # Nerd Fontsのグリフ名をユニークにするため接尾辞を付ける
            nerd_glyph.glyphname = f"{nerd_glyph.glyphname}-nf"
            # postテーブルでのグリフ名重複対策
            # fonttools merge で合成した後、MacOSで `'post'テーブルの使用性` エラーが発生することへの対処
            if nerd_glyph.glyphname in glyph_names:
                nerd_glyph.glyphname = f"{nerd_glyph.glyphname}-{nerd_glyph.encoding}"
            glyph_names.add(nerd_glyph.glyphname)
            # 幅を調整する
            half_width = eng_font[0x0030].width
            # Powerline Symbols の調整
            if 0xE0B0 <= nerd_glyph.unicode <= 0xE0D4:
                # なぜかズレている右付きグリフの個別調整 (EM 1000 に変更した後を想定して調整)
                original_width = nerd_glyph.width
                if nerd_glyph.unicode == 0xE0B2:
                    nerd_glyph.transform(psMat.translate(-353 * 2.024, 0))
                elif nerd_glyph.unicode == 0xE0B6:
                    nerd_glyph.transform(psMat.translate(-414 * 2.024, 0))
                elif nerd_glyph.unicode == 0xE0C5:
                    nerd_glyph.transform(psMat.translate(-137 * 2.024, 0))
                elif nerd_glyph.unicode == 0xE0C7:
                    nerd_glyph.transform(psMat.translate(-214 * 2.024, 0))
                elif nerd_glyph.unicode == 0xE0D4:
                    nerd_glyph.transform(psMat.translate(-314 * 2.024, 0))
                nerd_glyph.width = original_width
                # 位置と幅合わせ
                if nerd_glyph.width < half_width:
                    nerd_glyph.transform(
                        psMat.translate((half_width - nerd_glyph.width) / 2, 0)
                    )
                elif nerd_glyph.width > half_width:
                    nerd_glyph.transform(psMat.scale(half_width / nerd_glyph.width, 1))
                # グリフの高さ・位置を調整する
                nerd_glyph.transform(psMat.scale(1, 1.21))
                nerd_glyph.transform(psMat.translate(0, -24))
            elif nerd_glyph.width < (EM_ASCENT + EM_DESCENT) * 0.6:
                # 幅が狭いグリフは中央寄せとみなして調整する
                nerd_glyph.transform(
                    psMat.translate((half_width - nerd_glyph.width) / 2, 0)
                )
            # 幅を設定
            nerd_glyph.width = half_width
    # 日本語フォントにマージするため、既に存在する場合は削除する
    for nerd_glyph in nerd_font.glyphs():
        if nerd_glyph.unicode != -1:
            # 既に存在する場合は削除する
            try:
                for glyph in jp_font.selection.select(
                    ("unicode", None), nerd_glyph.unicode
                ).byGlyphs:
                    glyph.clear()
            except Exception:
                pass
            try:
                for glyph in eng_font.selection.select(
                    ("unicode", None), nerd_glyph.unicode
                ).byGlyphs:
                    glyph.clear()
            except Exception:
                pass
    jp_font.mergeFonts(nerd_font)
    jp_font.selection.none()
    eng_font.selection.none()


def delete_glyphs_with_duplicate_glyph_names(font):
    """重複するグリフ名を持つグリフをリネームする"""
    glyph_name_set = set()
    for glyph in font.glyphs():
        if glyph.glyphname in glyph_name_set:
            glyph.glyphname = f"{glyph.glyphname}_{glyph.encoding}"
        else:
            glyph_name_set.add(glyph.glyphname)


def edit_meta_data(font, weight: str, variant: str, cap_height: int, x_height: int):
    """フォント内のメタデータを編集する"""
    font.ascent = EM_ASCENT
    font.descent = EM_DESCENT

    font.os2_typoascent = OS2_ASCENT
    font.os2_typodescent = -OS2_DESCENT
    font.os2_winascent = OS2_ASCENT
    font.os2_windescent = OS2_DESCENT
    font.os2_typolinegap = 0

    font.hhea_ascent = OS2_ASCENT
    font.hhea_descent = -OS2_DESCENT
    font.hhea_linegap = 0

    font.os2_xheight = x_height
    font.os2_capheight = cap_height

    # VSCode のターミナル上のボトム位置の表示で g, j などが見切れる問題への対処
    # 水平ベーステーブルを削除
    font.horizontalBaseline = None

    if weight == "Regular":
        font.os2_weight = 400
    elif weight == "Bold":
        font.os2_weight = 700

    font.sfnt_names = (
        (
            "English (US)",
            "License",
            """This Font Software is licensed under the SIL Open Font License,
Version 1.1. This license is available with a FAQ
at: http://scripts.sil.org/OFL""",
        ),
        ("English (US)", "License URL", "http://scripts.sil.org/OFL"),
        ("English (US)", "Version", VERSION),
    )
    font.familyname = f"{FONT_NAME} {variant}".strip()
    font.fontname = f"{FONT_NAME}{variant}-{weight}".replace(" ", "").strip()
    font.fullname = f"{FONT_NAME} {variant}".strip() + f" {weight}"
    font.os2_vendor = VENDER_NAME
    font.copyright = COPYRIGHT


if __name__ == "__main__":
    main()
