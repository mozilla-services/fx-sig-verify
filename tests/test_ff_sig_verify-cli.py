
import pytest
from fx_sig_verify.cli import main


def test_main():
    with pytest.raises(SystemExit) as e:
        main(['-h', ])
    print(dir(e))
