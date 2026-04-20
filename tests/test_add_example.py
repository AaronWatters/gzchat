from gzchat.add_example import add_numbers, main


def test_add_numbers():
    assert add_numbers(2, 3) == 5


def test_main_outputs_sum(capsys):
    exit_code = main(["123", "456"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "579"
