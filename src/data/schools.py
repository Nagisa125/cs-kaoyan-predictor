"""School dataset: 8 universities, 2022-2026 historical data."""

import sys
sys.path.insert(0, "..")
from framework import SchoolProgram


def build_school_data() -> list[SchoolProgram]:
    data = []

    # ═══ 同济大学 ═══
    tj_peers = {"南大": {}, "浙大": {}, "上交": {}}
    for peer, scores in tj_peers.items():
        if peer == "南大":
            scores.update({2022: 356, 2023: 351, 2024: 340, 2025: 350, 2026: 367})
        elif peer == "浙大":
            scores.update({2022: 377, 2023: 375, 2024: 347, 2025: 347, 2026: 377})
        elif peer == "上交":
            scores.update({2022: 335, 2023: 340, 2024: 340, 2025: 341, 2026: 377})

    # 同济计专
    data.append(SchoolProgram(
        school="同济大学", major="计算机技术(085404)", major_type="专硕",
        college="计算机学院", exam_code="11408",
        scores={2022: 340, 2023: 335, 2024: 330, 2025: 305, 2026: 340},
        admitted={2022: 5, 2023: 0, 2024: 148, 2025: 93, 2026: 80},
        avg_scores={2024: 365, 2025: 341, 2026: 368.1},
        min_scores={2024: 314, 2025: 305, 2026: 340},
        max_scores={2024: 414, 2025: 395, 2026: 422},
        ratios={2025: 1.29},
        peers=["南大", "浙大", "上交"], peer_scores=tj_peers,
    ))

    # ═══ 武汉大学 ═══
    whu_peers = {"华科": {}}
    whu_peers["华科"].update({2022: 335, 2023: 345, 2024: 355, 2025: 315, 2026: 330})

    data.append(SchoolProgram(
        school="武汉大学", major="计算机技术(085404)", major_type="专硕",
        college="计算机学院", exam_code="22408",
        scores={2023: 360, 2024: 335, 2025: 320, 2026: 350},
        admitted={2024: 7, 2025: 105, 2026: 24},
        avg_scores={2024: 374, 2025: 360},
        min_scores={2024: 345, 2025: 322},
        ratios={2026: 1.44},
        peers=["华科"], peer_scores=whu_peers,
    ))

    # 武大网安专硕
    data.append(SchoolProgram(
        school="武汉大学", major="电子信息-网安(085400)", major_type="专硕",
        college="网安学院", exam_code="11408",
        scores={2024: 335, 2025: 350, 2026: 370},
        admitted={2024: 151, 2025: 154},
        avg_scores={2024: 362, 2025: 368},
        min_scores={2024: 335, 2025: 350},
        peers=[], peer_scores={},
    ))

    # ═══ 华中科技大学 ═══
    hust_peers = {"武大": {}}
    hust_peers["武大"].update({2023: 360, 2024: 335, 2025: 320, 2026: 350})

    data.append(SchoolProgram(
        school="华中科技大学", major="计算机技术(085404)", major_type="专硕",
        college="计算机学院", exam_code="11408",
        scores={2022: 335, 2023: 345, 2024: 355, 2025: 315, 2026: 330},
        admitted={2022: 146, 2024: 94, 2025: 105, 2026: 110},
        avg_scores={2022: 370, 2024: 380, 2025: 355},
        min_scores={2022: 338, 2024: 356, 2025: 319},
        max_scores={2022: 414, 2024: 436, 2025: 394},
        ratios={2022: 1.60, 2024: 1.70, 2025: 1.42},
        peers=["武大"], peer_scores=hust_peers,
    ))

    # 华科网安专硕
    data.append(SchoolProgram(
        school="华中科技大学", major="网络与信息安全(085412)", major_type="专硕",
        college="网安学院", exam_code="11408",
        scores={2024: 300, 2025: 300, 2026: 360},
        admitted={2024: 33, 2025: 44},
        avg_scores={2024: 344, 2025: 332},
        min_scores={2024: 305, 2025: 301},
        max_scores={2024: 410, 2025: 367},
        ratios={2024: 1.09, 2025: 1.11},
        peers=[], peer_scores={},
        exam_reform_year=2026,
    ))

    # ═══ 南京大学 ═══
    nju_e5_peers = {
        "浙大": {2022: 377, 2023: 375, 2024: 347, 2025: 347, 2026: 377},
        "上交": {2022: 335, 2023: 340, 2024: 340, 2025: 341, 2026: 377},
    }

    data.append(SchoolProgram(
        school="南京大学", major="电子信息-计算机(085404)", major_type="专硕",
        college="计算机系", exam_code="11408",
        scores={2022: 356, 2023: 351, 2024: 340, 2025: 350, 2026: 367},
        admitted={2023: 31, 2025: 87, 2026: 76},
        avg_scores={2023: 385},
        min_scores={2023: 352},
        max_scores={2023: 435},
        ratios={2023: 1.23, 2025: 1.22},
        peers=["浙大", "上交"], peer_scores=nju_e5_peers,
    ))

    data.append(SchoolProgram(
        school="南京大学", major="电子信息-软件(085405)", major_type="专硕",
        college="软件学院", exam_code="11408",
        scores={2023: 358, 2025: 372, 2026: 354},
        admitted={2023: 87, 2026: 117},
        avg_scores={2023: 385},
        min_scores={2023: 358},
        ratios={2023: 1.23, 2026: 1.20},
        peers=["浙大", "上交"], peer_scores=nju_e5_peers,
        exam_reform_year=2026,
    ))

    # ═══ 中山大学 ═══
    data.append(SchoolProgram(
        school="中山大学", major="计算机技术(085404)", major_type="专硕",
        college="计算机学院(广州)", exam_code="22408",
        scores={2024: 338, 2025: 371, 2026: 379},
        admitted={2024: 66, 2025: 74},
        avg_scores={2024: 371, 2025: 388},
        min_scores={2024: 338, 2025: 370},
        peers=[], peer_scores={},
    ))

    # ═══ 上海交通大学 ═══
    sjtu_peers = {
        "浙大": {2022: 377, 2023: 375, 2024: 347, 2025: 347, 2026: 377},
        "南大": {2022: 356, 2023: 351, 2024: 340, 2025: 350, 2026: 367},
    }

    data.append(SchoolProgram(
        school="上海交通大学", major="电子信息-计算机(085400)", major_type="专硕",
        college="计算机学院", exam_code="11408",
        scores={2022: 335, 2023: 340, 2024: 340, 2025: 341, 2026: 377},
        admitted={2024: 58, 2025: 74, 2026: 176},
        avg_scores={2024: 370, 2025: 368},
        min_scores={2024: 340, 2025: 341},
        max_scores={2024: 429, 2025: 414},
        ratios={2024: 2.26, 2025: 1.64},
        peers=["浙大", "南大"], peer_scores=sjtu_peers,
    ))

    # ═══ 浙江大学 ═══
    zju_peers = {
        "上交": {2022: 335, 2023: 340, 2024: 340, 2025: 341, 2026: 377},
        "南大": {2022: 356, 2023: 351, 2024: 340, 2025: 350, 2026: 367},
    }

    data.append(SchoolProgram(
        school="浙江大学", major="电子信息-计算机(085400)", major_type="专硕",
        college="计算机学院", exam_code="11408",
        scores={2022: 377, 2023: 375, 2024: 347, 2025: 347, 2026: 377},
        peers=["上交", "南大"], peer_scores=zju_peers,
    ))

    data.append(SchoolProgram(
        school="浙江大学", major="电子信息-软件(085400)", major_type="专硕",
        college="软件学院", exam_code="11408",
        scores={2022: 370, 2023: 360, 2024: 355, 2025: 349, 2026: 373},
        peers=["上交", "南大"], peer_scores=zju_peers,
    ))

    # ═══ 电子科技大学 ═══
    data.append(SchoolProgram(
        school="电子科技大学", major="计算机技术(085404)", major_type="专硕",
        college="计算机学院", exam_code="11408",
        scores={2022: 315, 2023: 345, 2024: 335, 2025: 320, 2026: 355},
        admitted={2022: 116, 2023: 127, 2024: 136, 2025: 131},
        avg_scores={2022: 350, 2023: 370, 2024: 365, 2025: 355},
        peers=[], peer_scores={},
        exam_reform_year=2026,
    ))

    return data
