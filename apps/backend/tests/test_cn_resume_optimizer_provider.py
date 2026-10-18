"""Chinese wording improves while fixed observable facts remain guarded."""
import asyncio
from copy import deepcopy
import json
import pytest
import httpx
from app.core.config import REPO_ROOT,Settings
from app.services.cn_resume_optimizer_provider import CNResumeOptimizerProvider,ResumeProviderError,validate_resume_review,_validate_chinese_edit
from cn_resume_optimizer_test_support import review_payload,RESUME,JD,QUOTE


@pytest.mark.parametrize('quote,replacement',[
    (QUOTE,'使用Python实现数据接口开发'),
    ('负责甲公司后台接口开发','承担甲公司后台接口开发'),
    ('2020年加入甲公司','2020年入职甲公司'),
    ('参与Python数据接口开发','协助Python数据接口开发'),
])
def test_real_chinese_rewording_is_allowed(quote,replacement):
    raw=review_payload(edits=False)
    source=RESUME+'\n'+quote if quote!=QUOTE else RESUME
    raw['edits']=[{'sourceQuote':quote,'replacement':replacement}]
    review,draft=validate_resume_review(raw,resume=source,jd='')
    assert replacement in draft and 'synthetic@example.invalid' in draft
    assert '教育：合成大学 本科。' in draft and review['overallScore']==72


@pytest.mark.parametrize('quote,replacement',[
    ('服务12个团队','服务13个团队'),('于2024年开发接口','于2025年开发接口'),
    ('二〇二四年入职甲公司','二〇二五年入职甲公司'),
    ('服务十个团队','服务二十个团队'),
    ('参与Python开发','主导Python开发'),('协助Python开发','独立负责Python开发'),
    ('支持接口开发','负责接口开发'),('负责接口开发','独立负责接口开发'),
    ('未参与支付项目','参与支付项目'),('没有机器学习经验','具备机器学习经验'),
    ('本科毕业于甲大学','硕士毕业于甲大学'),('在读本科','本科'),
    ('负责甲公司接口开发','负责乙公司接口开发'),('毕业于甲大学','毕业于乙大学'),
    (QUOTE,'使用Python和Kubernetes实现数据接口开发'),
    (QUOTE,'使用Python实现容器编排和数据接口开发'),
    ('实习参与接口开发','参与接口开发'),
    ('联系方式synthetic@example.invalid','联系方式other@example.invalid'),
])
def test_unsupported_facts_are_rejected(quote,replacement):
    raw=review_payload(edits=False)
    raw['edits']=[{'sourceQuote':quote,'replacement':replacement}]
    source=RESUME+'\n'+quote if quote not in RESUME else RESUME
    with pytest.raises(ResumeProviderError):validate_resume_review(raw,resume=source,jd='')


def test_jd_role_match_binds_both_sources_without_filling_candidate_skills():
    raw=review_payload(with_jd=True)
    review,draft=validate_resume_review(raw,resume=RESUME,jd=JD)
    assert review['roleMatchingAssessed'] is True and '容器编排' not in draft
    raw['dimensions'][-1]['evidence']=[{'source':'resume','quote':'Python'}]
    with pytest.raises(ResumeProviderError):validate_resume_review(raw,resume=RESUME,jd=JD)


@pytest.mark.parametrize('score',[True,False,-1,101,99.5,'90'])
def test_scores_are_strict_integers(score):
    raw=review_payload();raw['dimensions'][0]['score']=score
    with pytest.raises(ResumeProviderError):validate_resume_review(raw,resume=RESUME,jd='')


@pytest.mark.parametrize('mutate',[
    lambda r:r['dimensions'].pop(),
    lambda r:r['dimensions'].append(deepcopy(r['dimensions'][0])),
    lambda r:r['suggestions'][0].update(title='English advice only'),
    lambda r:r['dimensions'][0]['evidence'][0].update(quote='不存在的原文依据'),
    lambda r:r.update(missingFacts=['X'*601]),
    lambda r:r.update(draftMarkdown='untrusted full replacement'),
    lambda r:r.update(edits=[{'sourceQuote':'Python','replacement':'Python'},{'sourceQuote':QUOTE,'replacement':QUOTE}]),
])
def test_invalid_review_language_evidence_or_shape_fails(mutate):
    raw=review_payload();mutate(raw)
    with pytest.raises(ResumeProviderError):validate_resume_review(raw,resume=RESUME,jd='')


@pytest.mark.parametrize('failure',['truncated','malformed','http','oversize','timeout'])
def test_provider_is_bounded_no_retry_no_private_errors(failure):
    requests=[]
    async def respond(request):
        requests.append(request)
        if failure=='timeout':raise httpx.ReadTimeout('private synthetic resume content',request=request)
        if failure=='http':return httpx.Response(503,text='private synthetic provider body')
        if failure=='oversize':return httpx.Response(200,content=b'x'*(256*1024+1))
        return httpx.Response(200,json={'choices':[{'finish_reason':'length' if failure=='truncated' else 'stop','message':{'content':'{private malformed body'}}]})
    settings=Settings(_env_file=None).model_copy(update={'product_edition':'cn','chat_qwen_api_key':'synthetic','chat_qwen_base_url':'https://provider.invalid/v1'})
    provider=CNResumeOptimizerProvider(settings,transport=httpx.MockTransport(respond))
    with pytest.raises(ResumeProviderError) as exc:asyncio.run(provider.generate(resume=RESUME,jd='',target_role=''))
    assert str(exc.value) in {'invalid_output','provider_timeout','provider_unavailable'} and len(requests)==1
    sent=json.loads(requests[0].content)
    assert sent['stream'] is False and sent['enable_thinking'] is False
    assert '不可信资料' in sent['messages'][0]['content']
    assert json.loads(sent['messages'][1]['content'])['resume']==RESUME


def test_provider_success_chinese_prompt_and_conservative_output():
    async def respond(request):return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(review_payload(),ensure_ascii=False)}}]})
    settings=Settings(_env_file=None).model_copy(update={'product_edition':'cn','chat_qwen_api_key':'synthetic','chat_qwen_base_url':'https://provider.invalid/v1'})
    review,draft=asyncio.run(CNResumeOptimizerProvider(settings,transport=httpx.MockTransport(respond)).generate(resume=RESUME,jd='',target_role='后端开发'))
    assert review['overallScore']==72 and '使用Python实现数据接口开发' in draft


CASES=[json.loads(line) for line in (REPO_ROOT/'ai/evals/cn-resume-optimizer-v1.jsonl').read_text().splitlines() if line.strip()]
@pytest.mark.parametrize('case',CASES,ids=[c['id'] for c in CASES])
def test_chinese_grounding_offline_evals(case):
    assert case['synthetic'] is True
    if case['expectedAccepted']:
        review,draft=validate_resume_review(case['output'],resume=case['resume'],jd=case['jd'])
        assert 0<=review['overallScore']<=100 and 'synthetic@example.invalid' in draft
    else:
        with pytest.raises(ResumeProviderError):validate_resume_review(case['output'],resume=case['resume'],jd=case['jd'])
