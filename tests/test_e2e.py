from scripts.verify_f01 import (
    check_no_fulltext,
    cli_command,
    compare_databases,
    run_cli,
    snapshot,
)


def test_cli_real_sigint_and_resume(tmp_path, fixture_dir):
    full = tmp_path / "full.sqlite"
    resumed = tmp_path / "resumed.sqlite"
    count = 26
    batch_size = 5
    run_cli(cli_command(full, count, batch_size))
    _, before = run_cli(cli_command(resumed, count, batch_size), interrupt_after=10)
    after = snapshot(resumed)
    assert 0 < before["statuses"]["done"] <= after["statuses"]["done"] < 24
    assert after["statuses"]["pending"] > 0
    run_cli(cli_command(resumed, count, batch_size))
    compare_databases(full, resumed)
    assert snapshot(full) == snapshot(resumed)
    assert snapshot(resumed)["statuses"] == {"done": 24, "skipped": 2}
    assert snapshot(resumed)["max_attempts"] == 1
    assert check_no_fulltext(resumed, fixture_dir)["fulltext_matches"] == 0
