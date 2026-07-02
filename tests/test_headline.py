from sampler.viz.headline import BRAND_TEXT, print_version_card


def test_print_version_card_plain(capsys) -> None:
    from rich.console import Console

    console = Console(file=open("/dev/null", "w"), force_terminal=False)
    print_version_card(console, "0.0.0-test", animated=False)
    # smoke: no exception; brand constant is stable
    assert BRAND_TEXT == "SAMPLER"