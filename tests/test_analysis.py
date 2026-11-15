"""Tests for the pieces of src/analysis.py that carry the results.

The important ones pin the effect calculation against independent references:
a hand-checkable example, Pearson's chi-square (which must agree with the
two-proportion z-test), and Holm adjustment on known values.
"""
import numpy as np
import pandas as pd
import pytest
from scipy.stats import chi2_contingency
from statsmodels.stats.multitest import multipletests
from src.analysis import binary_effect, validate, bootstrap_difference

def make_frame():
    """Smallest frame that passes validate(): one row per arm."""
    return pd.DataFrame(dict(recency=[1]*3,history_segment=['1) $0 - $100']*3,history=[10]*3,mens=[1]*3,womens=[0]*3,zip_code=['Urban']*3,newbie=[0]*3,channel=['Web']*3,segment=['No E-Mail','Mens E-Mail','Womens E-Mail'],visit=[0]*3,conversion=[0]*3,spend=[0]*3))

def test_known_effect_and_symmetry():
    a=binary_effect(30,1000,10,1000); b=binary_effect(10,1000,30,1000)
    assert a['effect']==pytest.approx(.02)
    assert a['relative_lift']==pytest.approx(2)
    assert a['p_value']==pytest.approx(b['p_value'])
    assert a['ci_low']==pytest.approx(-b['ci_high'])
    assert a['family_ci_low']<a['ci_low']<a['ci_high']<a['family_ci_high']

def test_independent_chisquare_check():
    _,p,_,_=chi2_contingency([[30,970],[10,990]],correction=False)
    assert binary_effect(30,1000,10,1000)['p_value']==pytest.approx(p)

def test_null_and_boundaries():
    assert binary_effect(10,1000,10,1000)['p_value']==1
    assert binary_effect(0,10,0,10)['p_value']==1
    with pytest.raises(ValueError): binary_effect(11,10,1,10)

def test_missing_rejected():
    d=make_frame(); d.loc[0,'history']=np.nan
    with pytest.raises(ValueError): validate(d)

def test_duplicates_retained():
    d=pd.concat([make_frame(),make_frame()],ignore_index=True)
    assert len(validate(d))==6

def test_invalid_outcome_rejected():
    d=make_frame();d.loc[0,'conversion']=1
    with pytest.raises(ValueError): validate(d)

def test_bootstrap_constant_and_deterministic():
    assert np.allclose(bootstrap_difference(np.ones(10),np.zeros(10)),[1,1])
    a=np.arange(10); b=np.arange(8)
    assert np.array_equal(bootstrap_difference(a,b,reps=100),bootstrap_difference(a,b,reps=100))

def test_holm_reference():
    assert np.allclose(multipletests([.01,.04],method='holm')[1],[.02,.04])
