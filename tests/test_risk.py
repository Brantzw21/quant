"""
Risk control tests
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_risk_logger():
    """Test risk logger"""
    from risk_logger import check_risk_limits
    
    # Normal case
    result = check_risk_limits(1000, 10000, 5, 0.02)
    assert result["passed"] == True
    
    # Over position
    result = check_risk_limits(8000, 10000, 5, 0.02)
    assert result["passed"] == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
