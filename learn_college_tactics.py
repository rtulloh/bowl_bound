"""Optional private tactical-prior estimation; never publishes reference data."""

from tools.chartgen.cli import learn_tactics_main

if __name__ == "__main__":
    raise SystemExit(learn_tactics_main())
