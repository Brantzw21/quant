#!/usr/bin/env python3
"""Minimal offline simulator for eth_grid_v7 sync behavior."""

from typing import List, Tuple, Dict

MAX_GRIDS = 8


def order_key(side: str, price: float) -> Tuple[str, float]:
    return (side, round(float(price), 2))


def build_target_orders(grids: List[Tuple[str, float]], inv: float) -> List[Tuple[str, float]]:
    target_orders = []
    for side, g in grids:
        if side == "BUY" and inv > 0.7:
            continue
        if side == "SELL" and inv < -0.7:
            continue
        target_orders.append(order_key(side, g))
    return target_orders[:MAX_GRIDS]


def plan_sync(existing_orders: List[Dict], target_orders: List[Tuple[str, float]]):
    existing_map = {order_key(o['side'], o['price']): o for o in existing_orders}
    existing_set = set(existing_map.keys())
    target_set = set(target_orders)
    to_cancel = [existing_map[k] for k in sorted(existing_set - target_set)]
    to_create = [k for k in target_orders if k not in existing_set]
    return to_cancel, to_create


def assert_case(name: str, existing_orders: List[Dict], target_orders: List[Tuple[str, float]], expect_cancel: int, expect_create: int):
    to_cancel, to_create = plan_sync(existing_orders, target_orders)
    print(f'[{name}] cancel={len(to_cancel)} create={len(to_create)}')
    print('  to_cancel =', [order_key(o['side'], o['price']) for o in to_cancel])
    print('  to_create =', to_create)
    assert len(to_cancel) == expect_cancel, f'{name}: expected cancel {expect_cancel}, got {len(to_cancel)}'
    assert len(to_create) == expect_create, f'{name}: expected create {expect_create}, got {len(to_create)}'


if __name__ == '__main__':
    grids = [
        ('BUY', 2011.66),
        ('BUY', 2032.40),
        ('BUY', 2053.14),
        ('SELL', 2094.62),
        ('SELL', 2115.36),
        ('SELL', 2136.10),
    ]
    inv = 0.06
    target = build_target_orders(grids, inv)

    assert_case('A_match',
                [{'side': s, 'price': p} for s, p in target],
                target,
                expect_cancel=0,
                expect_create=0)

    assert_case('B_only_buy_missing_sell',
                [
                    {'side': 'BUY', 'price': 2011.66},
                    {'side': 'BUY', 'price': 2032.40},
                    {'side': 'BUY', 'price': 2053.14},
                ],
                target,
                expect_cancel=0,
                expect_create=3)

    assert_case('C_has_stale_buy_orders',
                [
                    {'side': 'BUY', 'price': 2001.05},
                    {'side': 'BUY', 'price': 2018.95},
                    {'side': 'BUY', 'price': 2022.28},
                    {'side': 'BUY', 'price': 2022.32},
                    {'side': 'BUY', 'price': 2035.28},
                    {'side': 'BUY', 'price': 2043.34},
                    {'side': 'BUY', 'price': 2044.15},
                    {'side': 'BUY', 'price': 2058.41},
                ],
                target,
                expect_cancel=8,
                expect_create=6)

    assert_case('D_same_price_wrong_side',
                [
                    {'side': 'BUY', 'price': 2094.62},
                ],
                target,
                expect_cancel=1,
                expect_create=6)

    target_a = build_target_orders(grids, inv)
    target_b = build_target_orders(grids, inv)
    print('[E_small_price_move_stable] same_target=', target_a == target_b)
    assert target_a == target_b

    stable_grids_1 = [
        ('BUY', 2014.70), ('BUY', 2035.47), ('BUY', 2056.24),
        ('SELL', 2097.78), ('SELL', 2118.55), ('SELL', 2139.32),
    ]
    stable_grids_2 = [
        ('BUY', 2014.70), ('BUY', 2035.47), ('BUY', 2056.24),
        ('SELL', 2097.78), ('SELL', 2118.55), ('SELL', 2139.32),
    ]
    print('[F_spacing_locked] same_target=', build_target_orders(stable_grids_1, inv) == build_target_orders(stable_grids_2, inv))
    assert build_target_orders(stable_grids_1, inv) == build_target_orders(stable_grids_2, inv)

    reduced_target = build_target_orders(grids[:2], inv)
    print('[G_reduced_levels] target_count=', len(reduced_target))
    assert len(reduced_target) == 2

    session_target = build_target_orders(stable_grids_1, inv)
    later_round_target = session_target[:]
    print('[H_session_targets_locked] same_target=', session_target == later_round_target)
    assert session_target == later_round_target

    existing_live_book = [
        {'side': 'BUY', 'price': 1992.29},
        {'side': 'BUY', 'price': 2013.04},
        {'side': 'BUY', 'price': 2033.79},
        {'side': 'BUY', 'price': 2054.54},
        {'side': 'SELL', 'price': 2096.04},
        {'side': 'SELL', 'price': 2116.79},
        {'side': 'SELL', 'price': 2137.54},
        {'side': 'SELL', 'price': 2158.29},
    ]
    hydrated_target = [order_key(o['side'], o['price']) for o in existing_live_book]
    to_cancel, to_create = plan_sync(existing_live_book, hydrated_target)
    print('[I_hydrate_existing_book] cancel=', len(to_cancel), 'create=', len(to_create))
    assert len(to_cancel) == 0
    assert len(to_create) == 0

    print('all_cases_passed')
