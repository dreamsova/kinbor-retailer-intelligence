#!/usr/bin/env python3
"""Evidence-linked style hypotheses, never purchasing predictions. Offline by default."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
import research

ROOT = Path(__file__).resolve().parent
UNKNOWN = 'Unknown'
STRATEGY = 'style_evidence_v1'
# Deliberately small, inspectable vocabulary. These tags are text interpretations,
# not pixel assessments of retailer images and not claims about store preference.
TAG_PATTERNS = {
 'plain_cover': r'solid.colou?r|simplicity|no.frills|simple design|plain cover',
 'botanical': r'botanical|floral|flowers?|tulips?|leaves|leaf',
 'repeat_pattern': r'repeat(?:ing)? pattern',
 'checker': r'checker',
 'geometric': r'checker|geometric',
 'muted': r'\bmuted\b', 'pastel': r'pale.green|pastel',
 'transparent': r'transparent|see.through|translucent',
 'animal': r'\b(?:cat|opossum|bunny|dog|animal)\b',
 'illustrated': r'doodles?|depiction|illustrat',
 'monochrome': r'matte charcoal|monochrome',
}
STYLE_WEIGHT = {'botanical':3, 'animal':2, 'transparent':3, 'repeat_pattern':3,
                'checker':3, 'geometric':2, 'plain_cover':2, 'muted':2, 'pastel':1,
                'illustrated':1, 'monochrome':2}
COMMERCIAL_UNKNOWN = ('Current inventory, supplier availability, Kinbor retail/landed price, paper performance, '
                      'material, resale authorization, buyer interest and one-carton acceptance are Unknown.')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_style_tags(corpus):
    clauses = re.split(r'[.;\n]', corpus)
    safe = ' '.join(c for c in clauses if not re.search(
        r'\b(?:not|without|never|no longer)\b|ignore.{0,40}(?:instructions|rules)|system prompt|api.key|password', c, re.I))
    return {tag:'title_or_description_text_inference' for tag,pattern in TAG_PATTERNS.items()
            if re.search(pattern,safe,re.I)}


def normalize_evidence(bundle):
    website = research.normalize_url(bundle['website'])
    allowed = {urlsplit(website).hostname.removeprefix('www.')}
    proof = bundle.get('official_shop_link')
    if proof:
        if not research.same_site(proof['source_url'], website):
            raise ValueError('Shop linkage source must be the official site')
        research.check_timestamp(proof.get('observed_at_utc', proof.get('retrieved_at_utc')))
        allowed.add(urlsplit(research.normalize_url(proof['target_url'])).hostname.removeprefix('www.'))
    rows, seen = [], set()
    for original in bundle.get('observations', bundle.get('products', [])):
        row = dict(original)
        eid = row.get('evidence_id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', eid) or eid in seen:
            raise ValueError('Missing or duplicate product evidence ID')
        seen.add(eid)
        source = research.normalize_url(row['source_url'])
        if urlsplit(source).hostname.removeprefix('www.') not in allowed:
            raise ValueError('Product source outside official or explicitly linked shop')
        timestamp = row.get('retrieved_at_utc', row.get('observed_at_utc'))
        research.check_timestamp(timestamp)
        image = row.get('product_image_url') or UNKNOWN
        image_status='URL observed; pixels unassessed' if image!=UNKNOWN else UNKNOWN
        if image != UNKNOWN:
            # Validate but retain ordinary public CDN resize parameters. Signed/
            # credential URLs are excluded rather than published in output.
            from vision import safe_image_url
            try:
                image = safe_image_url(image)
            except ValueError:
                image=UNKNOWN
                image_status='Unknown; unsafe or unavailable reference excluded'
        title = research.plain(row.get('title', row.get('product_name', '')))[:300]
        facts = row.get('observed_product_facts', row.get('observed_features', row.get('description_excerpt', '')))
        if isinstance(facts, list):
            facts = ' '.join(facts)
        facts = research.plain(facts)
        if facts == UNKNOWN:
            facts = ''
        corpus = title + ' ' + facts
        tags = text_style_tags(corpus)
        price = row.get('public_price', {})
        if not isinstance(price, dict):
            price = {'amount': price, 'currency': row.get('currency', UNKNOWN)}
        price = {'amount': str(price.get('amount', row.get('price_public', UNKNOWN))),
                 'currency': str(price.get('currency', row.get('currency', UNKNOWN)))}
        if price['amount'] != UNKNOWN and not re.fullmatch(r'\d+(?:\.\d{1,4})?', price['amount']):
            raise ValueError('Public price must be observed decimal or Unknown')
        if price['currency'] != UNKNOWN and not re.fullmatch(r'[A-Z]{3}', price['currency']):
            raise ValueError('Currency must be explicit ISO currency or Unknown')
        rows.append({'evidence_id':eid, 'title':title, 'source_url':source,
                     'product_image_url':image, 'screenshot_url':UNKNOWN,
                     'image_reference_status':image_status,
                     'retrieved_at_utc':timestamp, 'confidence':research.plain(row.get('confidence', UNKNOWN)),
                     'observed_product_facts':facts, 'source_excerpt':research.plain(row.get('raw_quote') or row.get('source_excerpt','')),
                     'public_price':price, 'style_tags_inferred':tags,
                     'family_inferred':family(title),
                     'uncertainties': row.get('uncertainties', []) + [COMMERCIAL_UNKNOWN],
                     'acquisition': row.get('acquisition', 'see product_evidence.json receipt'),
                     'epistemic_status':'official_page_observation; tags and family are inferences'})
    return rows


def family(title):
    if re.search(r'refill|insert', title, re.I):
        return 'refill'
    if re.search(r'pouch|case|bag', title, re.I):
        return 'storage'
    if re.search(r'sticker|tape|patch', title, re.I):
        return 'decoration'
    if re.search(r'notebook|\bnb\b|notepad|memo|planner|calendar|journal|task pad', title, re.I):
        return 'writing_paper'
    if re.search(r'\bpen\b|\bpencil\b', title, re.I):
        return 'writing_instrument'
    return 'unassessed'


def paper_format(title):
    if re.search(r'notepad|memo|task pad|taskpad|adhesive|sticky', title, re.I):
        return 'pad'
    if re.search(r'planner|calendar', title, re.I):
        return 'planner'
    if re.search(r'notebook|\bnb\b|journal', title, re.I):
        return 'notebook'
    return 'unassessed'


def product_family(product):
    return {'Notebooks & Journals':'writing_paper','Planners & Calendars':'writing_paper',
            'Sticky Notes & Page Flags':'writing_paper','Refills & Inserts':'refill',
            'Pouches & Cases':'storage','Stickers & Decorative Tape':'decoration',
            'Pens & Writing':'writing_instrument'}.get(product['category'], 'unassessed')


def load_notes(path, products, catalog_root=ROOT):
    notes = json.loads(Path(path).read_text(encoding='utf-8'))
    by_sku = {p['sku']:p for p in products}
    result = {}
    for note in notes['notes']:
        sku = note['sku']
        if sku not in by_sku or sku in result:
            raise ValueError('Visual note has unknown or duplicate SKU')
        if note['image_path'] != by_sku[sku]['image_path'] or note['image_sha256'] != digest(catalog_root / by_sku[sku]['image_path']):
            raise ValueError('Visual note/image identity drift: ' + sku)
        if note['epistemic_status'] != 'analyst_image_inference' or note['human_review_status'] != 'pending':
            raise ValueError('Image notes cannot assert final human approval')
        result[sku] = note
    return result


def style_profile(observations):
    tags = {}
    for e in observations:
        for tag in e['style_tags_inferred']:
            tags.setdefault(tag, []).append(e['evidence_id'])
    prices = {}
    for e in observations:
        p = e['public_price']
        if p['amount'] != UNKNOWN and p['currency'] != UNKNOWN:
            prices.setdefault(p['currency'], []).append(float(p['amount']))
    return {'basis':'Purposive official product sample; not a full assortment or customer-preference survey.',
            'style_hypotheses':[{'tag':tag,'evidence_ids':ids,'epistemic_status':'text_inference; retailer pixels unassessed'} for tag,ids in sorted(tags.items())],
            'observed_public_price_ranges':{c:{'minimum':min(v),'maximum':max(v),'sample_count':len(v)} for c,v in prices.items()},
            'customer_positioning':'Unknown; functional and aesthetic hypotheses only, no demographic inference.',
            'retailer_pixels_assessed':False, 'human_review_status':'pending',
            'counterevidence':'Mixed designs are retained individually; one sampled product does not define an exclusive store aesthetic. No negative preference inferred from absence.'}


def match(products, bundle, notes, *, limit=4):
    if not 0 <= limit <= 5:
        raise ValueError('Preview limit must be 0 to 5; never a quota')
    observations = normalize_evidence(bundle)
    candidates = []
    for p in products:
        note = notes.get(p['sku'])
        pf = product_family(p)
        support = []
        counter = []
        # A refill is not a substitute for a complete notebook; compatibility
        # requires explicit evidence and is never inferred from a plain cover.
        for e in observations:
            if not note or pf in ('unassessed', 'refill') or pf != e['family_inferred']:
                continue
            if pf == 'writing_paper':
                actual_format = {'Notebooks & Journals':'notebook', 'Planners & Calendars':'planner', 'Sticky Notes & Page Flags':'pad'}[p['category']]
                if paper_format(e['title']) != actual_format:
                    continue
            shared = sorted(set(note['style_tags']) & set(e['style_tags_inferred']))
            if not shared:
                continue
            # A generic 'illustrated' match alone is too broad for personalization.
            if set(shared) <= {'illustrated'}:
                continue
            strength=sum(STYLE_WEIGHT[t] for t in shared)
            if strength < 3:
                counter.append('Reference '+e['evidence_id']+' shares only broad design terms ('+', '.join(shared)+'); insufficient specific aesthetic evidence by itself.')
                continue
            support.append({'evidence_id':e['evidence_id'],'source_url':e['source_url'],
                            'title':e['title'], 'shared_style_tags_inferred':shared,
                            'support_score':strength,
                            'observed_retailer_fact':e['observed_product_facts'],
                            'retailer_product_image_url':e['product_image_url']})
            if ('lined' in (e['title']+' '+e['observed_product_facts']).lower() or 'ruled' in e['title'].lower()) and '横线' not in p['name_zh']:
                counter.append('SKU image suggests lined pages; physical ruling and layout equivalence remain unverified.'
                               if re.search(r'lined.page',note['visible_observation'],re.I) else
                               'Retailer reference specifies ruling; Kinbor ruling/layout is not established by this image comparison.')
            if 'checker black' in e['title'].lower() and 'high_color' in note['style_tags']:
                counter.append('Reference is named Checker Black; this SKU uses multicolor checks and a rainbow motif. Shared geometry does not establish palette fit.')
            if 'botanical archway' in e['title'].lower():
                counter.append('Botanical Archway is a named design; its title alone does not establish identical flower drawing, palette or artwork provenance.')
            if ('notebook' in e['title'].lower()) and p['category'] != 'Notebooks & Journals':
                counter.append('Notebook reference and this SKU have different functional formats; layout/use is not interchangeable.')
            if re.search(r'left.hand|letterpress|gold foil|brass wire',e['observed_product_facts'],re.I):
                counter.append('Reference includes handedness, printing or binding details not established for Kinbor; motif overlap does not establish equivalent construction.')
            if 'cat' in e['title'].lower() and '猫' not in p['name_zh']:
                counter.append('Cat reference does not establish affinity for this different animal/character design.')
        support.sort(key=lambda x:(-x['support_score'],x['evidence_id']))
        if pf == 'refill':
            counter.append('Refill dimensions/binding compatibility with retailer notebook systems Unknown; no standalone notebook substitution.')
        if int(p['moq_units']) >= 100:
            counter.append('Minimum is '+p['moq_units']+' units for this individual SKU; buyer carton acceptance Unknown.')
        if p['collection'] != 'Original Design':
            counter.append('Character/IP provenance and US resale authority require verification; no retailer relationship established.')
        if support:
            counter.append('Shared cover traits do not establish identical motif, language, ruling, binding, material or paper performance; compare images and physical samples.')
        if not note:
            counter.append('This SKU image has not been individually annotated; unassessed is not a negative match.')
        if note and observations:
            other = [e for e in observations if e['evidence_id'] not in {s['evidence_id'] for s in support}]
            if other:
                counter.append('Other sampled designs ('+', '.join(e['evidence_id'] for e in other[:3])+') provide different references; absence of overlap is not evidence of dislike.')
        status = 'needs_human_review' if support else 'insufficient_evidence'
        score = support[0]['support_score'] if support else 0
        reason = ('Style hypothesis from local SKU image observation and specific official product text: '
                  + ', '.join(support[0]['shared_style_tags_inferred']) + '; reference '+support[0]['title']+'. '
                  +'Retailer image pixels and buying preference remain unvalidated.' if support else
                  'No sufficient product-specific style + function evidence; no recommendation.')
        row = {k:p[k] for k in ('sku','name_zh','collection','image_path','units_per_carton','moq_cartons','moq_units','carton_qty_basis')}
        row.update(product_source_sheet=p['source_sheet'],product_source_row=p['source_row'],
                   product_category_inferred=p['category'],status=status,selected=False,
                   score=score,score_meaning='Evidence retrieval ordering only; not quality, confidence or purchase probability.',
                   retailer_evidence_ids=[s['evidence_id'] for s in support],
                   retailer_evidence_urls=[s['source_url'] for s in support],support=support,
                   visible_style_features_inferred=note['visible_observation'] if note else UNKNOWN,
                   visual_note_image_sha256=note['image_sha256'] if note else UNKNOWN,
                   reason=reason,counterevidence=list(dict.fromkeys(counter)),
                   confirmed_product_facts='Catalog SKU/image/source-row/carton join only; descriptive name retained verbatim.',
                   inference_status='analyst/rule hypothesis; not multimodal model assessment',
                   human_review_status='pending',commercial_unknown=COMMERCIAL_UNKNOWN)
        candidates.append(row)
    # No category rotation, collection quotas, supplier order or forced shop
    # differentiation. SKU only stabilizes equal evidence strength for display.
    candidates.sort(key=lambda r:(-r['score'],r['sku']))
    selected = [r for r in candidates if r['status']=='needs_human_review'][:limit]
    for r in selected:
        r['selected'] = True
    return {'schema_version':1,'strategy':STRATEGY,'retailer_id':bundle['retailer_id'],
            'website':bundle['website'],'generated_at_utc':research.now(),
            'retailer_style_profile':style_profile(observations),'observations':observations,
            'candidates':candidates,'selected_skus':[r['sku'] for r in selected],
            'recommendation_status':'Unvalidated review hypotheses only' if selected else 'insufficient evidence / needs human review',
            'policy_counterevidence':bundle.get('policy_counterevidence',[]),
            'multimodal':{'status':'MULTIMODAL LIVE NOT VALIDATED','assessments':[],
                          'receipt':{'request_count':0,'service':'OpenAI','billed_cost':UNKNOWN}},
            'limits':['Only annotated image subset can support offline style hypotheses; all 210 remain in audit.',
                      'Retailer image URLs were observed; pixels not analyzed by this offline matcher.',
                      'No confirmed buyer, stock, purchase intent, price-band compatibility or quality claim.',
                      'Same SKU may fit more than one retailer; no artificial differentiation.']}


def baseline(bundle_dir, products):
    source = json.loads((Path(bundle_dir)/'research.json').read_text(encoding='utf-8'))
    evidence = research.extract_evidence(source['pages'],source['acquisition'],source.get('run_id'),typed=True)
    _, recs = research.recommend(products,evidence,source.get('requested_limit',4),strategy=source.get('matching_strategy','legacy_source_order_v1'))
    return recs


def vision_selection(multimodal, expected, limit):
    """Validate saved model structure and recompute ranking, never authenticate it.

    An offline receipt is an audit record, not independent proof of execution.
    Strict comparisons detect accidental/tampered joins without claiming otherwise.
    """
    from vision import ENDPOINT, NOT_VALIDATED, validate_assessments
    rows=multimodal.get('assessments')
    if not isinstance(rows,list):
        raise ValueError('Invalid multimodal assessments')
    receipt=multimodal.get('receipt',{})
    if not rows:
        if multimodal.get('status') != NOT_VALIDATED:
            raise ValueError('No validated model assessment supports live status')
        return expected['selected_skus']
    supported=[r for r in expected['candidates'] if r['status']=='needs_human_review'][:8]
    relevant={s['evidence_id'] for r in supported for s in r['support']}
    eids=[e['evidence_id'] for e in expected['observations']
          if e['evidence_id'] in relevant and e['product_image_url']!=UNKNOWN][:3]
    skus=[r['sku'] for r in supported]
    if (multimodal.get('status')!='multimodal_assessment_received; human review required'
            or receipt.get('service')!='OpenAI' or receipt.get('endpoint')!=ENDPOINT
            or receipt.get('authorization') is not True or receipt.get('store') is not False
            or receipt.get('request_count')!=1 or receipt.get('authenticated_response_received') is not True
            or not receipt.get('model') or receipt.get('sent_skus')!=skus or receipt.get('evidence_ids')!=eids):
        raise ValueError('Multimodal receipt/subset drift')
    checked=validate_assessments(rows,skus,eids)
    assessed={a['sku']:a for a in checked}
    for r in supported:
        a=assessed[r['sku']]
        if a['fit']=='support' and not set(a['evidence_ids']) & set(r['retailer_evidence_ids']):
            raise ValueError('Visual support lacks a sent product-specific reference')
    ranks={'support':0,'uncertain':1,'conflict':2}
    ordered=sorted(supported,key=lambda r:(ranks[assessed[r['sku']]['fit']],-r['score'],r['sku']))
    return [r['sku'] for r in ordered if assessed[r['sku']]['fit']!='conflict'][:limit]


def validate_result(result, products, bundle, notes):
    expected = match(products,bundle,notes,limit=result['requested_limit'])
    # Do not trust model prose to mutate any catalog fact, evidence ID or baseline.
    expected_by = {r['sku']:r for r in expected['candidates']}
    if len(result['candidates']) != 210 or len({r['sku'] for r in result['candidates']}) != 210:
        raise ValueError('Full 210-SKU audit missing or duplicated')
    for row in result['candidates']:
        exp = expected_by.get(row['sku'])
        if exp is None:
            raise ValueError('Unknown SKU')
        for key in exp:
            if key != 'selected' and row.get(key) != exp[key]:
                raise ValueError('Candidate fact/evidence drift: '+row['sku']+' '+key)
    for key in ('observations','retailer_style_profile','policy_counterevidence'):
        if result[key] != expected[key]:
            raise ValueError('Profile or evidence drift: '+key)
    for key in ('strategy','retailer_id','website','recommendation_status','limits'):
        if result[key]!=expected[key]:
            raise ValueError('Matching identity/status drift: '+key)
    allowed = {r['sku'] for r in expected['candidates'] if r['status']=='needs_human_review'}
    if len(set(result['selected_skus'])) != len(result['selected_skus']) or not set(result['selected_skus']) <= allowed or len(result['selected_skus']) > result['requested_limit']:
        raise ValueError('Unsupported or excessive selected SKU')
    if result['selected_skus'] != vision_selection(result['multimodal'],expected,result['requested_limit']):
        raise ValueError('Selection ordering drift')
    if {r['sku'] for r in result['candidates'] if r['selected']} != set(result['selected_skus']):
        raise ValueError('Selected flags drift')
    return {'status':'passed','catalog_skus':210,'selected_review_hypotheses':len(result['selected_skus']),
            'multimodal':result['multimodal']['status']}


def validate_saved(directory, notes_path=ROOT/'phase2/sku_visual_notes.json'):
    directory=Path(directory)
    r=json.loads((directory/'matching.json').read_text(encoding='utf-8'))
    if (r['catalog_sha256']!=digest(ROOT/'products.csv')
            or r['product_evidence_sha256']!=digest(directory/'product_evidence.json')
            or r['visual_notes_sha256']!=digest(notes_path)):
        raise ValueError('Input identity drift')
    products=research.load_catalog()
    recs=baseline(directory,products) if (directory/'research.json').exists() else []
    strategy='saved '+(json.loads((directory/'research.json').read_text()).get('matching_strategy','legacy_source_order_v1') if recs else 'unavailable')
    if (r['baseline_skus']!=[x['sku'] for x in recs]
            or r['baseline_reasons']!={x['sku']:x['match_reason'] for x in recs}
            or r['baseline_strategy']!=strategy):
        raise ValueError('Frozen baseline drift')
    return validate_result(r,products,json.loads((directory/'product_evidence.json').read_text()),load_notes(notes_path,products))


def write_brief(result, directory):
    by_sku = {r['sku']:r for r in result['candidates']}
    model_rows={a['sku']:a for a in result['multimodal']['assessments']}
    pixel_notice=('Retailer pixels assessed only for the IDs in the OpenAI receipt; judgments remain model inference.' if model_rows else 'Retailer pixels were not visually assessed.')
    text = ['# Store-specific SKU review', '',f"Official site: {result['website']}",
            '', '**'+result['multimodal']['status']+'**. All selections need human review. No model quality improvement has been established.',
            '', 'Confirmed product facts are the immutable SKU/image/source/carton joins. Style comparison is inference. '+COMMERCIAL_UNKNOWN,
            '',f"Audited 210 SKUs; {sum(r['status']=='needs_human_review' for r in result['candidates'])} have a specific text/style hypothesis. Preview has {len(result['selected_skus'])} candidates; this is a maximum, not a quota.",
            '', '## Why these candidates']
    if not result['selected_skus']:
        text += ['', '**Insufficient evidence / needs human review. No forced recommendations.**',
                 'This does not reject all 210 products: only the annotated image subset can support a style hypothesis. The sampled products span '+
                 ', '.join(sorted({e['family_inferred'] for e in result['observations']}))+
                 '; mixed product references do not establish one store-wide preference.']
    for sku in result['selected_skus']:
        r=by_sku[sku]
        relative=Path(__import__('os').path.relpath(ROOT/r['image_path'],directory)).as_posix()
        text += ['',f"### {sku} — {r['name_zh']}",f"![{sku}]({relative})",
                 f"**One full carton per SKU: {r['moq_units']} units. Human review: pending.**",
                 '', '**Visible SKU features (analyst inference):** '+r['visible_style_features_inferred'],
                 '', '**Why investigate:** '+r['reason']]
        for s in r['support'][:3]:
            text += ['', f"- [{s['evidence_id']} — {s['title']}]({s['source_url']}): {s['observed_retailer_fact']} Shared design terms (inference): {', '.join(s['shared_style_tags_inferred'])}."]
        text += ['', '**Why it might fail:** '+' '.join(r['counterevidence']),
                 '', '**Verify next:** Compare the linked retailer image with this actual SKU; inspect language/layout, physical sample, paper and authorized resale; ask a human buyer to assess the carton quantity.']
        if sku in model_rows:
            a=model_rows[sku]
            text += ['', '**Optional OpenAI assessment (model inference, pending human review):** '+a['fit']+'; references '+', '.join(a['evidence_ids'])+'. '+a['visible_features'],
                     'Counterevidence: '+a['counterevidence']+' Uncertainty: '+a['uncertainty']]
    text += ['', '## Retailer product evidence', '', 'Images are URL references only; image rights remain with the owner. '+pixel_notice+' Observed listings do not establish current stock.',
             '', '| Evidence | Official product | Public price | Image reference | Observed UTC |', '|---|---|---|---|---|']
    for e in result['observations']:
        p=e['public_price']; price=p['amount']+' '+p['currency']
        img=f"[source image]({e['product_image_url']})" if e['product_image_url']!=UNKNOWN else UNKNOWN
        text.append(f"| {e['evidence_id']} | [{e['title']}]({e['source_url']}) | {price} | {img} | {e['retrieved_at_utc']} |")
    if result['policy_counterevidence']:
        text += ['', '## Submission-policy uncertainty']
        for p in result['policy_counterevidence']:
            text += ['',p['observed_policy']+' [Read full policy]('+p['source_url']+'). '+p['commercial_unknown']]
    text += ['', '## Before/after review', '', 'Saved category baseline: '+', '.join(result.get('baseline_skus',[]))+'.',
             'The old baseline is retained in the adjacent original research/CSV files for comparison. Current style decisions and all 210 candidate reasons are in `matching.json`. No accuracy or improvement percentage is available without independent labels.',
             'Use [the evaluation protocol](../../../docs/MATCHING_EVALUATION.md) and `phase2/reviews.csv`; intentional counterexamples are hypotheses, not gold negatives.']
    (Path(directory)/'style_brief.md').write_text('\n'.join(text)+'\n',encoding='utf-8')


def run(directory, *, notes_path=ROOT/'phase2/sku_visual_notes.json', limit=4, vision_enabled=False, authorized=False, model=None):
    started=time.monotonic(); directory=Path(directory)
    bundle=json.loads((directory/'product_evidence.json').read_text(encoding='utf-8'))
    products=research.load_catalog(); notes=load_notes(notes_path,products)
    result=match(products,bundle,notes,limit=limit)
    result.update(requested_limit=limit,catalog_sha256=digest(ROOT/'products.csv'),
                  product_evidence_sha256=digest(directory/'product_evidence.json'),visual_notes_sha256=digest(notes_path))
    recs=baseline(directory,products) if (directory/'research.json').exists() else []
    result['baseline_skus']=[r['sku'] for r in recs]
    result['baseline_reasons']={r['sku']:r['match_reason'] for r in recs}
    result['baseline_strategy']='saved '+(json.loads((directory/'research.json').read_text()).get('matching_strategy','legacy_source_order_v1') if recs else 'unavailable')
    if vision_enabled:
        from vision import assess
        supported=[r for r in result['candidates'] if r['status']=='needs_human_review'][:8]
        relevant={s['evidence_id'] for r in supported for s in r['support']}
        result['multimodal']=assess(supported,[e for e in result['observations'] if e['evidence_id'] in relevant],enabled=True,authorized=authorized,model=model)
        assessments=result['multimodal']['assessments']
        if assessments:
            expected=match(products,bundle,notes,limit=limit)
            try:
                result['selected_skus']=vision_selection(result['multimodal'],expected,limit)
            except ValueError:
                result['multimodal']['assessments']=[]
                result['multimodal']['status']='MULTIMODAL LIVE NOT VALIDATED'
                result['multimodal']['receipt']['reason']='product_reference_validation_failed'
            for r in result['candidates']:
                r['selected']=r['sku'] in result['selected_skus']
    result['elapsed_seconds']=round(time.monotonic()-started,4)
    validate_result(result,products,bundle,notes)
    (directory/'matching.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_brief(result,directory)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-dir',type=Path,required=True)
    parser.add_argument('--notes',type=Path,default=ROOT/'phase2/sku_visual_notes.json')
    parser.add_argument('--limit',type=int,default=4)
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--vision',action='store_true',help='Send bounded selected catalog images and public retailer image URLs to OpenAI Responses; requires OPENAI_API_KEY and KINBOR_VISION_MODEL')
    parser.add_argument('--authorize-openai-images',action='store_true',help='Confirm permission to send these specific catalog/retailer images to OpenAI for transient assessment; this does not grant publication rights')
    parser.add_argument('--model')
    args=parser.parse_args(argv)
    try:
        if args.validate:
            answer=validate_saved(args.pilot_dir,args.notes)
        else:
            r=run(args.pilot_dir,notes_path=args.notes,limit=args.limit,vision_enabled=args.vision,authorized=args.authorize_openai_images,model=args.model)
            answer={k:r[k] for k in ('retailer_id','selected_skus','recommendation_status','multimodal','elapsed_seconds')}
        print(json.dumps(answer,ensure_ascii=False,indent=2)); return 0
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({'status':'failed','error':research.safe_text(str(exc))})); return 2

if __name__=='__main__':
    raise SystemExit(main())
