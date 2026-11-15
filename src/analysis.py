"""Reproducible customer-level intent-to-treat analysis; run from repository root."""
from pathlib import Path
import hashlib, json, sqlite3
import numpy as np
import pandas as pd
from scipy import stats, optimize
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep, proportion_effectsize
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import NormalIndPower
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
ARMS = ['No E-Mail', 'Mens E-Mail', 'Womens E-Mail']
SHA = '0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece'

def binary_effect(x, n, y, m):
    if not (0 <= x <= n and 0 <= y <= m and n > 0 and m > 0):
        raise ValueError('Invalid binomial counts')
    p = 1.0 if x+y in (0,n+m) else float(proportions_ztest([x,y],[n,m])[1])
    ci = confint_proportions_2indep(x,n,y,m,method='newcomb',compare='diff')
    simultaneous = confint_proportions_2indep(x,n,y,m,method='newcomb',compare='diff',alpha=.025)
    return dict(effect=x/n-y/m,relative_lift=(x/n)/(y/m)-1 if y else None,p_value=p,
                ci_low=ci[0],ci_high=ci[1],family_ci_low=simultaneous[0],family_ci_high=simultaneous[1])

def validate(d):
    required={'recency','history_segment','history','mens','womens','zip_code','newbie','channel','segment','visit','conversion','spend'}
    if set(d.columns)!=required or d.isna().any().any(): raise ValueError('Schema or missing-value failure')
    if set(d.segment)!=set(ARMS): raise ValueError('Unexpected experimental arms')
    for c in ['mens','womens','newbie','visit','conversion']:
        if not d[c].isin([0,1]).all(): raise ValueError('Nonbinary '+c)
    for c in ['history','spend','recency']:
        if not np.isfinite(d[c]).all() or (d[c]<0).any(): raise ValueError('Invalid '+c)
    if not d.recency.between(1,12).all(): raise ValueError('Recency outside source definition')
    if (d.conversion>d.visit).any() or ((d.spend>0)!=(d.conversion==1)).any(): raise ValueError('Outcome inconsistency')
    return d.copy()  # identical profiles are not verified duplicate customers

def bootstrap_difference(a,b,seed=20261115,reps=3000):
    rng=np.random.default_rng(seed)
    # Multinomial counts over unique values equal an ordinary within-arm bootstrap.
    av,ac=np.unique(a,return_counts=True); bv,bc=np.unique(b,return_counts=True)
    delta=rng.multinomial(len(a),ac/len(a),size=reps)@av/len(a)-rng.multinomial(len(b),bc/len(b),size=reps)@bv/len(b)
    return np.quantile(delta,[.025,.975])

def main():
    out=ROOT/'reports'; out.mkdir(exist_ok=True)
    raw=ROOT/'data/hillstrom.csv'; sha=hashlib.sha256(raw.read_bytes()).hexdigest()
    if sha!=SHA: raise ValueError('Source checksum changed; investigate before analysis')
    d=validate(pd.read_csv(raw)); duplicate_rows=int(d.duplicated().sum())
    d.zip_code=d.zip_code.replace({'Surburban':'Suburban'})
    counts=d.segment.value_counts().reindex(ARMS)
    audit={'rows':len(d),'columns':len(d.columns),'missing_values':int(d.isna().sum().sum()),'identical_rows_beyond_first_retained':duplicate_rows,'verified_customer_duplicates':'unknown: no customer ID','sha256':sha,'counts':counts.to_dict(),'srm_p_value':float(stats.chisquare(counts)[1]),'srm_expected':'1:1:1, based on original source; independent allocation assumed','rows_removed':0,'cleaning':['Surburban normalized to Suburban']}
    (out/'audit.json').write_text(json.dumps(audit,indent=2))
    d.to_csv(ROOT/'data/cleaned.csv',index=False)
    summary=d.groupby('segment').agg(n=('conversion','size'),conversions=('conversion','sum'),conversion_rate=('conversion','mean'),visit_rate=('visit','mean'),revenue_per_customer=('spend','mean')).reindex(ARMS)
    summary.to_csv(out/'group_summary.csv')
    d.describe(include='all').to_csv(out/'eda_summary.csv')
    control=d[d.segment==ARMS[0]]; results=[]; revenue=[]
    for arm in ARMS[1:]:
        a=d[d.segment==arm]
        results.append(dict(arm=arm,**binary_effect(a.conversion.sum(),len(a),control.conversion.sum(),len(control))))
        test=stats.ttest_ind(a.spend,control.spend,equal_var=False); ci=test.confidence_interval()
        boot=bootstrap_difference(a.spend.to_numpy(),control.spend.to_numpy())
        revenue.append(dict(arm=arm,effect=a.spend.mean()-control.spend.mean(),p_value=test.pvalue,ci_low=ci.low,ci_high=ci.high,bootstrap_low=boot[0],bootstrap_high=boot[1]))
    r=pd.DataFrame(results); r['p_holm']=multipletests(r.p_value,method='holm')[1]; r.to_csv(out/'primary_effects.csv',index=False)
    rev=pd.DataFrame(revenue); rev.to_csv(out/'revenue_exploratory.csv',index=False)
    balance=[]
    features=pd.concat([d[['history','recency','mens','womens','newbie']],pd.get_dummies(d[['channel','zip_code']],dtype=int)],axis=1)
    for arm in ARMS[1:]:
        for c in features:
            x=features.loc[d.segment==arm,c]; y=features.loc[d.segment==ARMS[0],c]
            sd=np.sqrt((x.var()+y.var())/2)
            balance.append(dict(arm=arm,feature=c,smd=(x.mean()-y.mean())/sd if sd else 0))
    bal=pd.DataFrame(balance); bal.to_csv(out/'baseline_balance.csv',index=False)
    power=NormalIndPower(); p0=control.conversion.mean(); n=int(counts.min())
    mde=optimize.brentq(lambda delta:power.power(abs(proportion_effectsize(p0+delta,p0)),n,alpha=.025)-.8,1e-6,.1)
    plans=[]
    for delta in [.001,.002,.003,.005]:
        h=abs(proportion_effectsize(p0+delta,p0))
        plans.append(dict(absolute_effect=delta,relative_effect=delta/p0,baseline=p0,alpha_per_comparison=.025,power_at_current_n=power.power(h,n,alpha=.025),n_per_arm_80pct=int(np.ceil(power.solve_power(h,power=.8,alpha=.025)))))
    pd.DataFrame(plans).to_csv(out/'power_planning.csv',index=False)
    (out/'power_summary.json').write_text(json.dumps({'mde_80pct_absolute':mde,'n_per_arm':n,'baseline_from_observed_control':p0,'interpretation':'Future-planning sensitivity, not observed post-hoc power or a retrospective sample-size justification'},indent=2))
    with sqlite3.connect(':memory:') as con:
        d.to_sql('customers',con,index=False)
        pd.read_sql_query((ROOT/'sql/metrics.sql').read_text(),con).to_csv(out/'sql_metrics.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160,'axes.titleweight':'bold'})
    fig,ax=plt.subplots(figsize=(9,4.5)); xx=r.effect.to_numpy()*100
    ax.errorbar(xx,[1,0],xerr=np.array([r.effect-r.family_ci_low,r.family_ci_high-r.effect])*100,fmt='o',color='#176B87',capsize=5)
    ax.set_yticks([1,0],r.arm); ax.axvline(0,color='#999999',linestyle='--'); ax.set_xlabel('Conversion lift vs no email (percentage points)'); ax.set_title('Email assignment increased two-week conversion',loc='left',pad=18)
    fig.text(.02,.02,'97.5% Newcombe intervals per comparison; Bonferroni family coverage ≥95% (approximate).',fontsize=9);fig.tight_layout(rect=(0,.06,1,1)); fig.savefig(out/'conversion_effects.png');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.5)); axs[0].bar(['No email','Mens','Womens'],summary.conversion_rate*100,color=['#A5B4C0','#176B87','#38A3A5']);axs[0].set_ylabel('Conversion (%)');axs[0].set_title('Conversion by assigned arm')
    axs[1].hist(d.loc[d.spend>0,'spend'],bins=30,color='#176B87');axs[1].set_title('Positive spend distribution');axs[1].set_xlabel('Spend (source dollars)');axs[1].set_ylabel('Purchasing customers')
    fig.suptitle('64,000 customers • two-week observation window',fontweight='bold');fig.tight_layout();fig.savefig(out/'eda.png');plt.close(fig)
    lines=['# Results\n','Generated from the verified Kaggle CSV. See methodology and limitations before interpreting.\n',summary.to_markdown(),'\n## Primary comparisons\n',r.to_markdown(index=False),'\n## Exploratory revenue\n',rev.to_markdown(index=False),f'\nSRM p={audit["srm_p_value"]:.6f}; maximum absolute baseline SMD={bal.smd.abs().max():.4f}.',f'\nPlanning MDE at 80% power: {mde*100:.3f} percentage points.']
    (out/'results.md').write_text('\n'.join(lines))
    print(summary.to_string());print(r.to_string(index=False)); print('SRM',audit['srm_p_value'],'MDE',mde)

if __name__=='__main__': main()
