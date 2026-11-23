from discount import discount_price


def test_ten_percent_discount_on_one_hundred():
    assert discount_price(100, 10) == 90


def test_zero_discount_keeps_original_price():
    assert discount_price(100, 0) == 100
