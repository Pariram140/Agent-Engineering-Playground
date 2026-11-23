from discount import discount_price


def test_ten_percent_discount_on_two_hundred():
    assert discount_price(200, 10) == 180


def test_zero_discount_keeps_original_price():
    assert discount_price(100, 0) == 100
