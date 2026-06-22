export const meta = {
  name: 'upgrade-dashboard',
  description: 'Discover, verify, compatibility-check, forecast, and rank PC-hardware upgrade paths for a machine profile. Every spec/price claim is adversarially verified before it reaches the recommendation.',
  whenToUse: 'On-demand refresh of the hardware-upgrade dashboard recommendation. Pass the machine profile + run config via args.',
  phases: [
    { title: 'Discover', detail: 'parallel hardware-scout per category' },
    { title: 'Spec+Verify', detail: 'per-candidate spec-researcher → adversarial source-verifier' },
    { title: 'Compatibility', detail: 'compatibility-checker per surviving candidate' },
    { title: 'Forecast', detail: 'forecast-analyst reads engine output per candidate' },
    { title: 'Synthesize', detail: 'upgrade-strategist emits the ranked recommendation' },
  ],
}

// args: { profile, categories, scale, budgetUSD, forecastDir }
const profile = args.profile
const categories = args.categories || ['gpu', 'ram', 'storage', 'cpu', 'motherboard']
const scale = args.scale || 'standard'
const budgetUSD = args.budgetUSD ?? null
const forecastDir = args.forecastDir || 'apps/hw-dashboard/data/analytics'

const capN = { quick: 3, standard: 6, deep: 12 }[scale]
const votes = { quick: 1, standard: 2, deep: 3 }[scale]
const profileJSON = JSON.stringify(profile)

// ---- structured-output schemas (forced via agent opts.schema) -------------
const CANDIDATE_ARRAY = {
  type: 'object', required: ['candidates'], properties: {
    candidates: { type: 'array', items: {
      type: 'object', required: ['id', 'category', 'make', 'model'],
      properties: {
        id: { type: 'string' }, category: { type: 'string' }, make: { type: 'string' },
        model: { type: 'string' }, est_price_usd: { type: ['number', 'null'] },
        lead_source: { type: 'string' }, why_relevant: { type: 'string' },
      },
    } },
  },
}
const CITATION = {
  type: 'object', required: ['url', 'tier', 'claim'], properties: {
    url: { type: 'string' }, tier: { type: 'integer' }, claim: { type: 'string' },
    excerpt: { type: 'string' }, corroborator_url: { type: 'string' },
  },
}
const SPEC_SHEET = {
  type: 'object', required: ['candidate_id', 'claims'], properties: {
    candidate_id: { type: 'string' }, category: { type: 'string' },
    claims: { type: 'array', items: {
      type: 'object', required: ['field', 'value', 'status'], properties: {
        field: { type: 'string' }, value: {}, unit: { type: 'string' },
        status: { type: 'string', enum: ['verified', 'hypothesis'] }, citation: CITATION,
      },
    } },
  },
}
const VOTES = {
  type: 'object', required: ['votes'], properties: {
    votes: { type: 'array', items: {
      type: 'object', required: ['claim_ref', 'vote'], properties: {
        claim_ref: { type: 'string' }, vote: { type: 'string', enum: ['accept', 'reject', 'flag'] },
        reason: { type: 'string' }, reverified_url: { type: 'string' },
      },
    } },
  },
}
const COMPAT = {
  type: 'object', required: ['candidate_id', 'verdict'], properties: {
    candidate_id: { type: 'string' },
    verdict: { type: 'string', enum: ['compatible', 'conditional', 'incompatible'] },
    checks: { type: 'array', items: { type: 'object' } },
    blocking_reasons: { type: 'array', items: { type: 'string' } },
  },
}
const FORECAST = {
  type: 'object', required: ['candidate_id', 'recommendation'], properties: {
    candidate_id: { type: 'string' },
    recommendation: { type: 'string', enum: ['buy', 'wait', 'hold'] },
    narrative: { type: 'string' }, confidence: { type: 'number' },
    target_window: { type: 'string' }, series_ref: { type: 'string' },
  },
}
const UPGRADE_RECOMMENDATION = {
  type: 'object',
  required: ['profile_id', 'generated_at', 'ranked_options', 'verification_summary'],
  properties: {
    profile_id: { type: 'string' }, generated_at: { type: 'string' },
    run_config: { type: 'object' },
    ranked_options: { type: 'array', items: { type: 'object' } },
    whole_machine_paths: { type: 'array', items: { type: 'object' } },
    excluded: { type: 'array', items: { type: 'object' } },
    verification_summary: { type: 'object' },
  },
}

// ---- prompt builders ------------------------------------------------------
const scoutPrompt = (category) =>
  `Scout upgrade candidates for category="${category}".\nMachine profile:\n${profileJSON}\n` +
  `Budget USD: ${budgetUSD ?? 'unbounded'}. Return at most ${capN} deduplicated candidates ` +
  `that plausibly fit this machine and advance its goals. JSON only per the candidates schema.`

const specPrompt = (cand) =>
  `Research authoritative, citation-backed specs for this candidate:\n${JSON.stringify(cand)}\n` +
  `Machine profile (for relevance):\n${profileJSON}\nEvery spec is a Claim with a citation. ` +
  `Mark unverifiable values status:"hypothesis". JSON only per the spec sheet schema.`

const verifyPrompt = (spec, i) =>
  `Independent verification pass #${i + 1}. Adversarially re-check each claim's citation by ` +
  `re-fetching the source. Default to reject when uncertain.\nClaims:\n${JSON.stringify(spec.claims)}\n` +
  `JSON only per the votes schema.`

const compatPrompt = (spec) =>
  `Decide compatibility of this spec'd part against the machine.\nSpec:\n${JSON.stringify(spec)}\n` +
  `Machine profile:\n${profileJSON}\nJSON only per the compatibility schema.`

const forecastPrompt = (cand) =>
  `Interpret the price analytics for candidate "${cand.candidate_id || cand.id}". ` +
  `Read ${forecastDir}/${cand.candidate_id || cand.id}.json (if present) and produce a buy/wait/hold ` +
  `narrative honoring the engine's confidence. JSON only per the forecast schema.`

const strategistPrompt = (fit, forecasts) =>
  `Synthesize the final ranked UpgradeRecommendation.\nMachine profile:\n${profileJSON}\n` +
  `Budget USD: ${budgetUSD ?? 'unbounded'}. Run config: ${JSON.stringify({ scale, budgetUSD, categories })}.\n` +
  `Compatible, spec-verified candidates:\n${JSON.stringify(fit)}\n` +
  `Forecasts:\n${JSON.stringify(forecasts)}\n` +
  `Carry every citation forward; populate excluded[] and verification_summary. ` +
  `JSON only conforming to recommendation.schema.json.`

// ---- adversarial verification --------------------------------------------
function tally(spec, ballots) {
  const byClaim = new Map(spec.claims.map((c) => [c.field, []]))
  for (const b of ballots) {
    for (const v of (b.votes || [])) {
      if (byClaim.has(v.claim_ref)) byClaim.get(v.claim_ref).push(v.vote)
    }
  }
  let demoted = 0
  const verifiedClaims = spec.claims.map((c) => {
    const vs = byClaim.get(c.field) || []
    const accepts = vs.filter((v) => v === 'accept').length
    const passed = vs.length === 0 ? c.status === 'verified' : accepts * 2 > vs.length
    if (!passed) demoted++
    return { ...c, status: passed ? 'verified' : 'hypothesis' }
  })
  return {
    ...spec, claims: verifiedClaims,
    passed: verifiedClaims.some((c) => c.status === 'verified'),
    claims_total: spec.claims.length, claims_demoted: demoted,
  }
}

async function adversarialVerify(spec, voteCount) {
  if (!spec || !spec.claims || !spec.claims.length) return { ...spec, passed: false, claims_total: 0, claims_demoted: 0 }
  const ballots = (await parallel(
    Array.from({ length: voteCount }, (_, i) => () =>
      agent(verifyPrompt(spec, i), { agentType: 'source-verifier', phase: 'Spec+Verify', model: 'haiku', schema: VOTES })
    )
  )).filter(Boolean)
  return tally(spec, ballots)
}

// ---- orchestration --------------------------------------------------------
phase('Discover')
const candidateSets = await parallel(categories.map((c) => () =>
  agent(scoutPrompt(c), { agentType: 'hardware-scout', phase: 'Discover', model: 'sonnet', schema: CANDIDATE_ARRAY })
))
const candidates = candidateSets.filter(Boolean).flatMap((r) => r.candidates || [])
log(`discovered ${candidates.length} candidates across ${categories.length} categories`)

// per-candidate: spec → adversarial-verify → compatibility (pipeline; candidates run independently)
const evaluated = await pipeline(
  candidates,
  (cand) => agent(specPrompt(cand), { agentType: 'spec-researcher', phase: 'Spec+Verify', model: 'sonnet', schema: SPEC_SHEET }),
  (spec) => adversarialVerify(spec, votes),
  (vspec) => vspec && vspec.passed
    ? agent(compatPrompt(vspec), { agentType: 'compatibility-checker', phase: 'Compatibility', schema: COMPAT })
        .then((verdict) => ({ verdict, spec: vspec }))
    : null
)
const fit = evaluated.filter(Boolean).filter((e) => e.verdict && e.verdict.verdict === 'compatible')
log(`${fit.length} candidates passed verification + compatibility`)

phase('Forecast')
const forecasts = (await parallel(fit.map((e) => () =>
  agent(forecastPrompt(e.spec), { agentType: 'forecast-analyst', phase: 'Forecast', schema: FORECAST })
))).filter(Boolean)

phase('Synthesize')
const recommendation = await agent(
  strategistPrompt(fit, forecasts),
  { agentType: 'upgrade-strategist', phase: 'Synthesize', schema: UPGRADE_RECOMMENDATION }
)

// The session persists this to apps/hw-dashboard/data/recommendation.json (workflows can't write files).
return recommendation
